import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة وتنسيق CSS ---
st.set_page_config(page_title="Nawaem Boutique Pro", layout="wide", page_icon="👗")

# تحسين المظهر (RTL للعربية)
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center;}
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة (Session State) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. دوال قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_v3.db', check_same_thread=False)
    c = conn.cursor()
    
    # المنتجات
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
    )""")
    
    # العملاء (جدول جديد)
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, address TEXT, username TEXT
    )""")
    
    # المبيعات (تم ربطها بالعميل)
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        variant_id INTEGER,
        product_name TEXT,
        qty INTEGER,
        total REAL,
        profit REAL,
        date TEXT,
        invoice_id TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- 3. شاشة تسجيل الدخول ---
def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 نظام نواعم بوتيك")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            if password == "1234":  # <--- غير كلمة المرور هنا
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("كلمة المرور خاطئة")

# --- 4. التطبيق الرئيسي ---
def main_app():
    # الشريط الجانبي
    with st.sidebar:
        st.title("👗 نواعم بوتيك")
        st.write(f"مرحباً، المدير")
        menu = st.radio("القائمة", ["🏠 الرئيسية", "🛒 نقطة البيع (سلة)", "📦 المخزون", "👥 العملاء", "📊 التقارير"])
        if st.button("تسجيل خروج"):
            st.session_state.logged_in = False
            st.rerun()

    # === الصفحة الرئيسية (Dashboard) ===
    if menu == "🏠 الرئيسية":
        st.title("لوحة المعلومات")
        
        # إحصائيات سريعة
        date_today = datetime.now().strftime("%Y-%m-%d")
        sales_today = pd.read_sql(f"SELECT SUM(total) as tot, SUM(profit) as prof FROM sales WHERE date LIKE '{date_today}%'", conn)
        low_stock = pd.read_sql("SELECT COUNT(*) FROM variants WHERE stock < 2", conn).iloc[0,0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("مبيعات اليوم", f"{sales_today.iloc[0,0] or 0:,.0f} د.ع")
        c2.metric("أرباح اليوم", f"{sales_today.iloc[0,1] or 0:,.0f} د.ع")
        c3.metric("تنبيهات المخزون", f"{low_stock} أصناف", delta_color="inverse")

    # === نقطة البيع (مع السلة) ===
    elif menu == "🛒 نقطة البيع (سلة)":
        st.header("نقطة البيع الذكية")
        
        col_products, col_cart = st.columns([2, 1])
        
        with col_products:
            st.subheader("1. اختر المنتجات")
            df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
            
            search = st.text_input("🔍 بحث سريع...", placeholder="فستان، أحمر...")
            if search:
                mask = df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)
                df = df[mask]
            
            # عرض المنتجات للإضافة للسلة
            if not df.empty:
                product_list = df.apply(lambda x: f"{x['name']} | {x['color']} | {x['size']} ({x['price']:,.0f} د.ع)", axis=1).tolist()
                selected_prod_str = st.selectbox("اختر قطعة:", options=product_list)
                
                if selected_prod_str:
                    selected_row = df[df.apply(lambda x: f"{x['name']} | {x['color']} | {x['size']} ({x['price']:,.0f} د.ع)", axis=1) == selected_prod_str].iloc[0]
                    
                    c1, c2, c3 = st.columns(3)
                    qty = c1.number_input("الكمية", 1, int(selected_row['stock']), 1)
                    price = c2.number_input("سعر البيع", value=float(selected_row['price']), step=1000.0)
                    
                    if c3.button("إضافة للسلة ➕"):
                        item = {
                            "id": int(selected_row['id']),
                            "name": selected_row['name'],
                            "color": selected_row['color'],
                            "size": selected_row['size'],
                            "cost": selected_row['cost'],
                            "price": price,
                            "qty": qty,
                            "total": price * qty
                        }
                        st.session_state.cart.append(item)
                        st.success("تمت الإضافة للسلة")
                        st.rerun()

        with col_cart:
            st.subheader("🛍️ سلة المشتريات")
            if st.session_state.cart:
                total_cart = 0
                for i, item in enumerate(st.session_state.cart):
                    st.info(f"{item['qty']}x {item['name']} ({item['color']}) - {item['total']:,.0f}")
                    total_cart += item['total']
                
                st.markdown("---")
                st.metric("الإجمالي الكلي", f"{total_cart:,.0f} د.ع")
                
                if st.button("❌ تفريغ السلة"):
                    st.session_state.cart = []
                    st.rerun()
                
                st.markdown("### بيانات العميل والدفع")
                
                # اختيار عميل موجود أو جديد
                cust_choice = st.radio("نوع العميل", ["عميل جديد", "عميل سابق"], horizontal=True)
                cust_id = None
                cust_name = ""
                
                if cust_choice == "عميل سابق":
                    customers = pd.read_sql("SELECT id, name, phone FROM customers", conn)
                    if not customers.empty:
                        cust_options = customers.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist()
                        selected_cust = st.selectbox("ابحث عن العميل", cust_options)
                        cust_name = selected_cust.split(" - ")[0]
                        cust_id = customers[customers['name'] == cust_name]['id'].iloc[0]
                    else:
                        st.warning("لا يوجد عملاء مسجلين")
                
                else: # عميل جديد
                    with st.form("new_cust"):
                        new_name = st.text_input("الاسم")
                        new_phone = st.text_input("الهاتف")
                        new_addr = st.text_input("العنوان")
                        if st.form_submit_button("حفظ بيانات العميل مؤقتاً"):
                            cust_name = new_name
                
                # زر إتمام الطلب النهائي
                if st.button("✅ إتمام الطلب وطباعة"):
                    # معالجة العميل الجديد إذا لزم الأمر
                    cursor = conn.cursor()
                    if cust_choice == "عميل جديد" and new_name:
                        cursor.execute("INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)", 
                                      (new_name, new_phone, new_addr))
                        cust_id = cursor.lastrowid
                        cust_name = new_name
                    
                    if cust_id or cust_name:
                        invoice_id = datetime.now().strftime("%Y%m%d%H%M%S")
                        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        for item in st.session_state.cart:
                            # خصم المخزون
                            cursor.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (item['qty'], item['id']))
                            # تسجيل البيع
                            profit = (item['price'] - item['cost']) * item['qty']
                            cursor.execute("""INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) 
                                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                           (cust_id, item['id'], item['product_name'], item['qty'], item['total'], profit, date_now, invoice_id))
                        
                        conn.commit()
                        st.session_state.cart = [] # تفريغ السلة
                        st.balloons()
                        st.success(f"تم البيع بنجاح! رقم الفاتورة: {invoice_id}")
                        # هنا يمكن إضافة كود لتوليد PDF إذا أردت لاحقاً
                    else:
                        st.error("يجب تحديد بيانات العميل")

            else:
                st.write("السلة فارغة")

    # === المخزون (Matrix) ===
    elif menu == "📦 المخزون":
        st.header("إدارة المخزون")
        with st.expander("إضافة منتج جديد (Matrix)", expanded=True):
            with st.form("add_matrix"):
                c1, c2 = st.columns(2)
                name = c1.text_input("اسم الموديل")
                colors = c1.text_input("الألوان (مفصولة بفاصلة)")
                sizes = c2.text_input("القياسات (مفصولة بفاصلة)")
                stock = c2.number_input("العدد لكل صنف", 1)
                cost = c1.number_input("التكلفة", 0.0)
                price = c2.number_input("سعر البيع", 0.0)
                
                if st.form_submit_button("توليد الأصناف"):
                    clist = [c.strip() for c in colors.split(',') if c.strip()]
                    slist = [s.strip() for s in sizes.split(',') if s.strip()]
                    count = 0
                    cur = conn.cursor()
                    for c in clist:
                        for s in slist:
                            cur.execute("INSERT INTO variants (name, color, size, cost, price, stock) VALUES (?,?,?,?,?,?)",
                                        (name, c, s, cost, price, stock))
                            count += 1
                    conn.commit()
                    st.success(f"تمت إضافة {count} صنف")
        
        st.subheader("المخزون الحالي")
        df_stock = pd.read_sql("SELECT id, name, color, size, price, stock FROM variants", conn)
        st.dataframe(df_stock, use_container_width=True)

    # === العملاء ===
    elif menu == "👥 العملاء":
        st.header("سجل العملاء")
        df_cust = pd.read_sql("SELECT * FROM customers", conn)
        st.dataframe(df_cust, use_container_width=True)

    # === التقارير ===
    elif menu == "📊 التقارير":
        st.header("تقارير المبيعات")
        df_sales = pd.read_sql("""
            SELECT s.invoice_id, s.date, c.name as customer, s.product_name, s.total, s.profit 
            FROM sales s LEFT JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC
        """, conn)
        st.dataframe(df_sales, use_container_width=True)

# --- تشغيل التطبيق ---
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
