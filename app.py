import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(page_title="بوتيك كلاود", layout="wide", page_icon="👗")

# --- دوال قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_web.db', check_same_thread=False)
    c = conn.cursor()
    # جدول المنتجات
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        color TEXT,
        size TEXT,
        cost REAL,
        price REAL,
        stock INTEGER
    )""")
    # جدول المبيعات
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id INTEGER,
        name TEXT,
        qty INTEGER,
        total REAL,
        profit REAL,
        date TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- الواجهة الجانبية (القائمة) ---
st.sidebar.title("نظام إدارة البوتيك")
menu = st.sidebar.radio("القائمة الرئيسية", ["نقطة البيع (POS)", "إدخال بضاعة (Matrix)", "التقارير والمخزون"])

# ==========================
# صفحة 1: إدخال بضاعة (Matrix)
# ==========================
if menu == "إدخال بضاعة (Matrix)":
    st.header("📦 إدخال منتج جديد (نظام المصفوفة)")
    
    with st.form("add_product_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("اسم الموديل (مثال: فستان صيفي)")
            colors = st.text_input("الألوان (افصل بفاصلة ،) مثال: أحمر, أسود")
        with col2:
            sizes = st.text_input("القياسات (افصل بفاصلة ،) مثال: S, M, L")
            stock_per_item = st.number_input("العدد لكل قطعة", min_value=1, value=1)
        
        col3, col4 = st.columns(2)
        with col3:
            cost = st.number_input("سعر التكلفة (للقطعة)", min_value=0.0, step=1000.0)
        with col4:
            price = st.number_input("سعر البيع (للقطعة)", min_value=0.0, step=1000.0)
            
        submitted = st.form_submit_button("توليد الأصناف وحفظها")
        
        if submitted:
            if name and colors and sizes:
                color_list = [c.strip() for c in colors.split(',')]
                size_list = [s.strip() for s in sizes.split(',')]
                
                count = 0
                c = conn.cursor()
                for color in color_list:
                    for size in size_list:
                        if color and size:
                            c.execute("""INSERT INTO variants (name, color, size, cost, price, stock) 
                                         VALUES (?, ?, ?, ?, ?, ?)""", 
                                      (name, color, size, cost, price, stock_per_item))
                            count += 1
                conn.commit()
                st.success(f"تم توليد وإضافة {count} صنف للمخزون بنجاح!")
            else:
                st.error("يرجى ملء جميع الحقول!")

# ==========================
# صفحة 2: نقطة البيع (POS)
# ==========================
elif menu == "نقطة البيع (POS)":
    st.header("🛒 نقطة البيع")

    # تحميل البيانات
    df = pd.read_sql("SELECT * FROM variants", conn)
    
    if not df.empty:
        # الفلترة والبحث
        search_term = st.text_input("🔍 بحث (بالاسم أو اللون):", placeholder="اكتب اسم الموديل...")
        
        if search_term:
            mask = df['name'].str.contains(search_term, case=False) | df['color'].str.contains(search_term, case=False)
            filtered_df = df[mask]
        else:
            filtered_df = df

        # عرض النتائج بطريقة مناسبة للموبايل
        st.subheader("اختر القطعة للبيع:")
        
        # نقوم بإنشاء قائمة منسدلة ذكية تحتوي التفاصيل
        filtered_df['display'] = filtered_df.apply(lambda x: f"{x['name']} | {x['color']} | {x['size']} (متبقي: {x['stock']}) - {x['price']} د.ع", axis=1)
        
        selected_item_str = st.selectbox("القائمة المتاحة:", options=filtered_df['display'].tolist())
        
        if selected_item_str:
            # استخراج بيانات العنصر المختار
            selected_row = filtered_df[filtered_df['display'] == selected_item_str].iloc[0]
            
            st.info(f"القطعة المختارة: **{selected_row['name']}** - اللون: {selected_row['color']} - القياس: {selected_row['size']}")
            st.metric("السعر", f"{selected_row['price']:,.0f}")
            
            if st.button("تأكيد البيع (قطعة واحدة)", type="primary"):
                if selected_row['stock'] > 0:
                    c = conn.cursor()
                    # 1. خصم المخزون
                    c.execute("UPDATE variants SET stock = stock - 1 WHERE id = ?", (int(selected_row['id']),))
                    
                    # 2. تسجيل البيع
                    profit = selected_row['price'] - selected_row['cost']
                    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""INSERT INTO sales (variant_id, name, qty, total, profit, date) 
                                 VALUES (?, ?, ?, ?, ?, ?)""",
                              (int(selected_row['id']), selected_row['name'], 1, selected_row['price'], profit, date_now))
                    conn.commit()
                    st.success("✅ تمت عملية البيع بنجاح!")
                    st.rerun() # تحديث الصفحة
                else:
                    st.error("⚠️ نعتذر، الكمية نفذت!")
    else:
        st.warning("المخزون فارغ، يرجى إضافة بضاعة أولاً.")

# ==========================
# صفحة 3: التقارير والمخزون
# ==========================
elif menu == "التقارير والمخزون":
    st.header("📊 حالة البوتيك")
    
    tab1, tab2 = st.tabs(["جرد المخزون", "سجل المبيعات والأرباح"])
    
    with tab1:
        st.subheader("المخزون الحالي")
        stock_df = pd.read_sql("SELECT name, color, size, price, stock FROM variants", conn)
        st.dataframe(stock_df, use_container_width=True)
        
        total_stock_value = pd.read_sql("SELECT SUM(cost * stock) FROM variants", conn).iloc[0,0]
        st.metric("قيمة البضاعة بالمخزون (بسعر التكلفة)", f"{total_stock_value:,.0f} د.ع" if total_stock_value else "0")

    with tab2:
        st.subheader("حركة المبيعات")
        sales_df = pd.read_sql("SELECT name, total, profit, date FROM sales ORDER BY id DESC", conn)
        st.dataframe(sales_df, use_container_width=True)
        
        if not sales_df.empty:
            total_sales = sales_df['total'].sum()
            total_profit = sales_df['profit'].sum()
            
            col_a, col_b = st.columns(2)
            col_a.metric("إجمالي المبيعات", f"{total_sales:,.0f}")
            col_b.metric("صافي الأرباح", f"{total_profit:,.0f}")
        else:
            st.info("لا توجد مبيعات مسجلة بعد.")
