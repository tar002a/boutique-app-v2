import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة (Mobile Optimized) ---
st.set_page_config(page_title="Nawaem Mobile", layout="wide", page_icon="📱", initial_sidebar_state="collapsed")

# --- CSS لتخصيص الموبايل ---
st.markdown("""
<style>
    /* ضبط الاتجاه لليمين */
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    
    /* تكبير الأزرار لتناسب اللمس */
    .stButton button {
        width: 100%;
        height: 50px;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 12px;
    }
    
    /* تقليل الهوامش لاستغلال شاشة الموبايل */
    .block-container {
        padding-top: 1rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* تنسيق البطاقات (Cards) */
    .sale-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, username TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
        qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- 3. نافذة التعديل (Dialog) ---
@st.dialog("تعديل العملية")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.write(f"📦 المنتج: **{product_name}**")
    
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("السعر الإجمالي", value=float(current_total))
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 حفظ", type="primary"):
            cur = conn.cursor()
            diff = new_qty - int(current_qty)
            if diff != 0:
                cur.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (diff, variant_id))
            cur.execute("UPDATE sales SET qty = ?, total = ? WHERE id = ?", (new_qty, new_total, sale_id))
            conn.commit()
            st.success("تم!")
            st.rerun()
    with col2:
        if st.button("🗑️ حذف"):
            cur = conn.cursor()
            cur.execute("UPDATE variants SET stock = stock + ? WHERE id = ?", (int(current_qty), variant_id))
            cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            conn.commit()
            st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    st.title("📱 بوتيك نواعم")
    password = st.text_input("كلمة المرور", type="password")
    if st.button("دخول للنظام"):
        if password == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("خطأ")

# --- 5. التطبيق الرئيسي ---
def main_app():
    # قائمة علوية بدلاً من الجانبية للموبايل (Tabs)
    st.markdown("### 🛍️ نظام الإدارة")
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "📦 مخزن", "🏠 تقرير"])

    # === تبويب 1: نقطة البيع ===
    with tabs[0]:
        # قسم اختيار المنتج
        with st.container(border=True):
            st.caption("إضافة للسلة")
            df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
            
            # بحث سريع
            search = st.text_input("🔍 ابحث هنا...", label_visibility="collapsed", placeholder="اسم الموديل او اللون")
            if search:
                mask = df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)
                df = df[mask]
            
            if not df.empty:
                # دمج البيانات في نص واحد لسهولة القراءة على الموبايل
                options = df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1).tolist()
                selected_opt = st.selectbox("اختر:", options, label_visibility="collapsed")
                
                if selected_opt:
                    row = df[df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1) == selected_opt].iloc[0]
                    
                    # عرض تفاصيل المنتج المختار بشكل واضح
                    st.info(f"سعر القطعة: {row['price']:,.0f} د.ع | المتوفر: {row['stock']}")
                    
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("العدد", 1, int(row['stock']), 1)
                    price = c2.number_input("سعر البيع", value=float(row['price']))
                    
                    if st.button("إضافة للسلة ➕", type="primary"):
                        st.session_state.cart.append({
                            "id": int(row['id']), "name": row['name'], "color": row['color'],
                            "size": row['size'], "cost": row['cost'], "price": price,
                            "qty": qty, "total": price * qty
                        })
                        st.toast("تمت الإضافة للسلة!", icon="✅")

        # قسم السلة
        if st.session_state.cart:
            st.divider()
            st.markdown("#### 🛒 السلة الحالية")
            total_cart = 0
            for idx, item in enumerate(st.session_state.cart):
                with st.container(border=True):
                    c_del, c_info = st.columns([1, 4])
                    with c_del:
                        if st.button("❌", key=f"del_{idx}"):
                            st.session_state.cart.pop(idx)
                            st.rerun()
                    with c_info:
                        st.markdown(f"**{item['name']}** ({item['qty']})")
                        st.caption(f"{item['color']} | {item['size']} | الإجمالي: {item['total']:,.0f}")
                    total_cart += item['total']
            
            st.success(f"الإجمالي الكلي: {total_cart:,.0f} د.ع")
            
            # إتمام الطلب
            with st.expander("بيانات العميل والدفع", expanded=True):
                cust_choice = st.radio("العميل", ["سابق", "جديد"], horizontal=True)
                cust_id, cust_name = None, ""
                
                if cust_choice == "سابق":
                    custs = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not custs.empty:
                        c_name = st.selectbox("اختر:", custs['name'].tolist())
                        cust_id = custs[custs['name']==c_name]['id'].iloc[0]
                        cust_name = c_name
                else:
                    cust_name = st.text_input("اسم العميل الجديد")
                    new_phone = st.text_input("رقم الهاتف")
                    new_addr = st.text_input("العنوان")
                
                if st.button("✅ إتمام البيع الآن"):
                    if not cust_name:
                        st.error("اسم العميل مطلوب")
                    else:
                        cursor = conn.cursor()
                        if cust_choice == "جديد":
                            cursor.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (cust_name, new_phone, new_addr))
                            cust_id = cursor.lastrowid
                        
                        inv_id = datetime.now().strftime("%Y%m%d%H%M")
                        date_n = datetime.now().strftime("%Y-%m-%d %H:%M")
                        
                        for item in st.session_state.cart:
                            cursor.execute("UPDATE variants SET stock = stock - ? WHERE id=?", (item['qty'], item['id']))
                            profit = (item['price'] - item['cost']) * item['qty']
                            cursor.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?,?)",
                                           (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, date_n, inv_id))
                        
                        conn.commit()
                        st.session_state.cart = []
                        st.balloons()
                        st.success(f"تم البيع! فاتورة #{inv_id}")

    # === تبويب 2: سجل العمليات (Cards View) ===
    with tabs[1]:
        st.caption("اضغط على 'تعديل' لتصحيح أي عملية")
        # جلب آخر 20 عملية فقط للسرعة
        df_sales = pd.read_sql("""
            SELECT s.id, s.date, c.name as cust, s.product_name, s.qty, s.total, s.variant_id 
            FROM sales s LEFT JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC LIMIT 20
        """, conn)
        
        for index, row in df_sales.iterrows():
            # تصميم البطاقة بدلاً من الجدول
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{row['product_name']}**")
                    st.caption(f"العميل: {row['cust']} | التاريخ: {row['date']}")
                    st.markdown(f"الكمية: **{row['qty']}** | المبلغ: **{row['total']:,.0f}**")
                with col_b:
                    if st.button("⚙️", key=f"edit_{row['id']}"):
                        edit_sale_dialog(row['id'], row['qty'], row['total'], row['variant_id'], row['product_name'])

    # === تبويب 3: المخزون ===
    with tabs[2]:
        with st.expander("➕ إضافة بضاعة جديدة"):
            with st.form("mob_add"):
                name = st.text_input("الاسم")
                col_c, col_s = st.columns(2)
                colors = col_c.text_input("ألوان (،)")
                sizes = col_s.text_input("قياسات (،)")
                
                col_p1, col_p2, col_st = st.columns(3)
                cost = col_p1.number_input("تكلفة", 0.0)
                price = col_p2.number_input("بيع", 0.0)
                stock = col_st.number_input("عدد", 1)
                
                if st.form_submit_button("حفظ"):
                    colors = colors.replace('،', ',')
                    sizes = sizes.replace('،', ',')
                    clist = [c.strip() for c in colors.split(',') if c.strip()]
                    slist = [s.strip() for s in sizes.split(',') if s.strip()]
                    cur = conn.cursor()
                    c_count = 0
                    for c in clist:
                        for s in slist:
                            cur.execute("INSERT INTO variants (name, color, size, cost, price, stock) VALUES (?,?,?,?,?,?)", (name, c, s, cost, price, stock))
                            c_count += 1
                    conn.commit()
                    st.success(f"تم {c_count}")

        st.caption("المخزون المتوفر")
        df_st = pd.read_sql("SELECT name, color, size, stock FROM variants ORDER BY id DESC", conn)
        st.dataframe(df_st, use_container_width=True, height=300)

    # === تبويب 4: التقارير ===
    with tabs[3]:
        today = datetime.now().strftime("%Y-%m-%d")
        res = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{today}%'", conn).iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.metric("مبيعات اليوم", f"{res[0] or 0:,.0f}")
        with c2:
            with st.container(border=True):
                st.metric("أرباح اليوم", f"{res[1] or 0:,.0f}")
        
        if st.button("تسجيل خروج", type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
