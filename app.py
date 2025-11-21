import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة وتنسيق CSS ---
st.set_page_config(page_title="Nawaem Boutique Pro", layout="wide", page_icon="👗")

st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .stButton button {width: 100%;}
    .sale-row {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. دوال قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_v3.db', check_same_thread=False)
    c = conn.cursor()
    
    # الجداول (نفس الهيكل السابق)
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, address TEXT, username TEXT
    )""")
    
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

# --- 3. وظيفة النافذة المنبثقة للتعديل (Dialog) ---
@st.dialog("تعديل عملية البيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"تعديل العملية رقم: {sale_id} - المنتج: {product_name}")
    
    # خيارات التعديل
    new_qty = st.number_input("تعديل الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("تعديل السعر الإجمالي", value=float(current_total))
    
    col_save, col_del = st.columns(2)
    
    # زر الحفظ
    with col_save:
        if st.button("💾 حفظ التعديلات", type="primary"):
            cur = conn.cursor()
            # حساب فرق المخزون
            diff = new_qty - int(current_qty)
            if diff != 0:
                # إذا زادت الكمية، نخصم من المخزون، والعكس
                cur.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (diff, variant_id))
            
            # تحديث البيعة
            cur.execute("UPDATE sales SET qty = ?, total = ? WHERE id = ?", (new_qty, new_total, sale_id))
            conn.commit()
            st.success("تم التعديل بنجاح!")
            st.rerun()
            
    # زر الحذف
    with col_del:
        if st.button("🗑️ حذف نهائي"):
            cur = conn.cursor()
            # استرجاع البضاعة للمخزون
            cur.execute("UPDATE variants SET stock = stock + ? WHERE id = ?", (int(current_qty), variant_id))
            # حذف السجل
            cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            conn.commit()
            st.error("تم حذف العملية واسترجاع المخزون!")
            st.rerun()

# --- 4. شاشة تسجيل الدخول ---
def login_screen():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("🔒 نظام نواعم بوتيك")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            if password == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("كلمة المرور خاطئة")

# --- 5. التطبيق الرئيسي ---
def main_app():
    with st.sidebar:
        st.title("👗 نواعم بوتيك")
        menu = st.radio("القائمة", ["🏠 الرئيسية", "🛒 نقطة البيع", "📦 المخزون", "👥 العملاء", "📊 سجل العمليات"])
        if st.button("تسجيل خروج"):
            st.session_state.logged_in = False
            st.rerun()

    # === الرئيسية ===
    if menu == "🏠 الرئيسية":
        st.title("لوحة المعلومات")
        date_today = datetime.now().strftime("%Y-%m-%d")
        sales_today = pd.read_sql(f"SELECT SUM(total) as tot, SUM(profit) as prof FROM sales WHERE date LIKE '{date_today}%'", conn)
        low_stock = pd.read_sql("SELECT COUNT(*) FROM variants WHERE stock < 2", conn).iloc[0,0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("مبيعات اليوم", f"{sales_today.iloc[0,0] or 0:,.0f} د.ع")
        c2.metric("أرباح اليوم", f"{sales_today.iloc[0,1] or 0:,.0f} د.ع")
        c3.metric("تنبيهات المخزون", f"{low_stock} أصناف", delta_color="inverse")

    # === نقطة البيع ===
    elif menu == "🛒 نقطة البيع":
        st.header("نقطة البيع الذكية")
        col_products, col_cart = st.columns([2, 1])
        
        with col_products:
            st.subheader("1. اختر المنتجات")
            df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
            search = st.text_input("🔍 بحث سريع...", placeholder="اسم، لون...")
            if search:
                mask = df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)
                df = df[mask]
            
            if not df.empty:
                # قائمة منسدلة ذكية
                options = df.apply(lambda x: f"{x['id']} - {x['name']} | {x['color']} | {x['size']} ({x['price']:,.0f})", axis=1).tolist()
                selected_opt = st.selectbox("اختر قطعة:", options=options)
                
                if selected_opt:
                    sel_id = int(selected_opt.split(' - ')[0])
                    selected_row = df[df['id'] == sel_id].iloc[0]
                    
                    c1, c2, c3 = st.columns(3)
                    qty = c1.number_input("الكمية", 1, int(selected_row['stock']), 1)
                    price = c2.number_input("سعر البيع", value=float(selected_row['price']), step=1000.0)
                    if c3.button("إضافة للسلة ➕"):
                        item = {
                            "id": int(selected_row['id']), "name": selected_row['name'],
                            "color": selected_row['color'], "size": selected_row['size'],
                            "cost": selected_row['cost'], "price": price,
                            "qty": qty, "total": price * qty
                        }
                        st.session_state.cart.append(item)
                        st.success("تمت الإضافة")
                        st.rerun()

        with col_cart:
            st.subheader("🛍️ سلة المشتريات")
            if st.session_state.cart:
                for item in st.session_state.cart:
                    st.info(f"{item['qty']}x {item['name']} - {item['total']:,.0f}")
                
                total_cart = sum(item['total'] for item in st.session_state.cart)
                st.metric("الإجمالي", f"{total_cart:,.0f} د.ع")
                
                if st.button("❌ تفريغ السلة"):
                    st.session_state.cart = []; st.rerun()
                
                st.markdown("---")
                cust_choice = st.radio("العميل", ["سابق", "جديد"], horizontal=True)
                cust_id, cust_name = None, ""
                
                if cust_choice == "سابق":
                    customers = pd.read_sql("SELECT id, name, phone FROM customers", conn)
                    if not customers.empty:
                        sel_cust = st.selectbox("العميل", customers.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist())
                        cust_name = sel_cust.split(" - ")[0]
                        cust_id = customers[customers['name'] == cust_name]['id'].iloc[0]
                else:
                    new_name = st.text_input("الاسم")
                    new_phone = st.text_input("الهاتف")
                    new_addr = st.text_input("العنوان")
                    cust_name = new_name
                
                if st.button("✅ إتمام الطلب"):
                    cursor = conn.cursor()
                    if cust_choice == "جديد" and new_name:
                        cursor.execute("INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)", (new_name, new_phone, new_addr))
                        cust_id = cursor.lastrowid
                    elif cust_choice == "جديد" and not new_name:
                        st.error("اسم العميل مطلوب"); st.stop()
                    
                    invoice_id = datetime.now().strftime("%Y%m%d%H%M%S")
                    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    for item in st.session_state.cart:
                        cursor.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (item['qty'], item['id']))
                        profit = (item['price'] - item['cost']) * item['qty']
                        cursor.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?,?)",
                                       (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, date_now, invoice_id))
                    conn.commit()
                    st.session_state.cart = []
                    st.balloons()
                    st.success(f"فاتورة: {invoice_id}")

    # === المخزون ===
    elif menu == "📦 المخزون":
        st.header("إدارة المخزون")
        with st.expander("إضافة منتج جديد", expanded=True):
            with st.form("add_matrix"):
                c1, c2 = st.columns(2)
                name = c1.text_input("اسم الموديل")
                colors = c1.text_input("الألوان (،)")
                sizes = c2.text_input("القياسات (،)")
                stock = c2.number_input("العدد", 1)
                cost = c1.number_input("التكلفة", 0.0)
                price = c2.number_input("البيع", 0.0)
                if st.form_submit_button("توليد"):
                    colors = colors.replace('،', ',')
                    sizes = sizes.replace('،', ',')
                    clist = [c.strip() for c in colors.split(',') if c.strip()]
                    slist = [s.strip() for s in sizes.split(',') if s.strip()]
                    cur = conn.cursor(); count=0
                    for c in clist:
                        for s in slist:
                            cur.execute("INSERT INTO variants (name, color, size, cost, price, stock) VALUES (?,?,?,?,?,?)", (name, c, s, cost, price, stock))
                            count+=1
                    conn.commit()
                    st.success(f"تمت إضافة {count} صنف")
        st.dataframe(pd.read_sql("SELECT * FROM variants", conn), use_container_width=True)

    # === العملاء ===
    elif menu == "👥 العملاء":
        st.dataframe(pd.read_sql("SELECT * FROM customers", conn), use_container_width=True)

    # === سجل العمليات (المعدل) ===
    elif menu == "📊 سجل العمليات":
        st.header("أرشيف المبيعات وتعديلها")
        
        # جلب آخر 50 عملية فقط للأداء
        df_sales = pd.read_sql("""
            SELECT s.id, s.date, c.name as customer, s.product_name, s.qty, s.total, s.variant_id 
            FROM sales s LEFT JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC LIMIT 50
        """, conn)
        
        # عرض الرؤوس
        cols = st.columns([1, 2, 2, 2, 1, 2, 1.5])
        headers = ["ID", "التاريخ", "العميل", "المنتج", "الكمية", "الإجمالي", "إجراء"]
        for col, h in zip(cols, headers):
            col.markdown(f"**{h}**")
        
        st.markdown("---")
        
        # عرض الصفوف مع زر التعديل
        for index, row in df_sales.iterrows():
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1, 2, 2, 2, 1, 2, 1.5])
            c1.write(str(row['id']))
            c2.write(row['date'].split()[0]) # عرض التاريخ بدون الوقت
            c3.write(row['customer'])
            c4.write(row['product_name'])
            c5.write(str(row['qty']))
            c6.write(f"{row['total']:,.0f}")
            
            # زر التعديل الذي يفتح النافذة المنبثقة
            if c7.button("⚙️ تعديل", key=f"btn_{row['id']}"):
                edit_sale_dialog(row['id'], row['qty'], row['total'], row['variant_id'], row['product_name'])

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
