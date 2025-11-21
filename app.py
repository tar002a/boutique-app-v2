import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import pytz
from contextlib import contextmanager

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem System", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

# --- تحسين الاتصال بقاعدة البيانات (Context Manager) ---
DB_NAME = 'boutique_v3.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER, is_active BOOLEAN DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
        )""")
        conn.commit()

# استدعاء التهيئة مرة واحدة عند التشغيل
init_db()

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS (نفس التنسيق السابق) ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .stock-warning {color: red; font-weight: bold; font-size: 0.8em;}
</style>
""", unsafe_allow_html=True)

# --- إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- 4. شاشة الدخول (محسنة) ---
def login_screen():
    st.title("🌸 نواعم بوتيك - تسجيل الدخول")
    
    # كلمة المرور الافتراضية (يمكنك تغييرها أو وضعها في st.secrets)
    CORRECT_PASSWORD = "admin" 
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.form("login_form"):
            password = st.text_input("كلمة المرور", type="password")
            submit = st.form_submit_button("دخول 🔐")
            
            if submit:
                if password == CORRECT_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("كلمة المرور خاطئة!")

# --- دوال مساعدة ---
def add_to_cart(item, qty, price):
    st.session_state.cart.append({
        "id": int(item['id']), "name": item['name'], 
        "color": item['color'], "size": item['size'], 
        "cost": item['cost'], "price": price, 
        "qty": qty, "total": price*qty
    })
    st.toast("تمت الإضافة للسلة", icon="✅")

# --- التطبيق الرئيسي ---
def main_app():
    # زر تسجيل الخروج
    with st.sidebar:
        if st.button("تسجيل خروج 🚪"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["🛒 نقطة البيع", "📋 السجل", "👥 العملاء", "📦 المخزون", "📊 التقارير"])

    # === 1. البيع (تحسين البحث والأداء) ===
    with tabs[0]:
        col_pos, col_cart = st.columns([2, 1])
        
        with col_pos:
            st.subheader("بحث عن منتج")
            search_term = st.text_input("🔍 ابحث باسم المنتج أو اللون...", label_visibility="collapsed")
            
            query = "SELECT * FROM variants WHERE stock > 0 AND is_active = 1"
            params = []
            if search_term:
                query += " AND (name LIKE ? OR color LIKE ?)"
                params = [f'%{search_term}%', f'%{search_term}%']
            
            with get_db_connection() as conn:
                df = pd.read_sql(query, conn, params=params)

            if not df.empty:
                # عرض النتائج كبطاقات بدل القائمة المنسدلة لتحسين التجربة
                for _, row in df.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        with c1:
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['color']} | {row['size']}")
                            if row['stock'] < 3:
                                st.markdown(f"<span class='stock-warning'>⚠️ باقي {row['stock']} فقط</span>", unsafe_allow_html=True)
                        with c2:
                            price_val = st.number_input("السعر", value=float(row['price']), key=f"p_{row['id']}")
                        with c3:
                            qty_val = st.number_input("العدد", 1, int(row['stock']), 1, key=f"q_{row['id']}")
                        with c4:
                            st.write("") # مسافة
                            if st.button("أضف", key=f"add_{row['id']}", type="primary"):
                                add_to_cart(row, qty_val, price_val)

        # سلة المشتريات (على اليسار)
        with col_cart:
            st.subheader("🛒 السلة")
            if st.session_state.cart:
                total_cart = 0
                for idx, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        st.text(f"{item['name']} - {item['color']}")
                        c_a, c_b = st.columns(2)
                        c_a.text(f"{item['qty']} x {item['price']:,.0f}")
                        c_b.text(f"= {item['total']:,.0f}")
                        total_cart += item['total']
                        if st.button("❌", key=f"del_{idx}"):
                            st.session_state.cart.pop(idx)
                            st.rerun()
                
                st.divider()
                st.markdown(f"### المجموع: {total_cart:,.0f} د.ع")
                
                # إتمام البيع
                cust_name = st.text_input("اسم العميل (اختياري)")
                if st.button("✅ إتمام العملية", type="primary", use_container_width=True):
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        # (يمكن إضافة منطق حفظ العميل هنا)
                        cust_id = 0 # افتراضي
                        if cust_name:
                            cur.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (cust_name, "", ""))
                            cust_id = cur.lastrowid
                        
                        baghdad_now = get_baghdad_time()
                        inv_id = baghdad_now.strftime("%Y%m%d%H%M")
                        dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
                        
                        for item in st.session_state.cart:
                            cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (item['qty'], item['id']))
                            profit = (item['price'] - item['cost']) * item['qty']
                            cur.execute("""
                                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) 
                                VALUES (?,?,?,?,?,?,?,?)
                            """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
                        
                        conn.commit()
                    
                    st.session_state.cart = []
                    st.success("تم حفظ العملية بنجاح!")
                    st.balloons()
                    st.rerun()

    # === 5. التقارير الذكية (تحديث الأداء) ===
    with tabs[4]:
        st.header("📊 لوحة المعلومات")
        
        with get_db_connection() as conn:
            # استخدام استعلامات مجمعة بدل تحميل كل البيانات
            today_str = get_baghdad_time().strftime("%Y-%m-%d")
            
            df_today = pd.read_sql("SELECT SUM(total) as sales, SUM(profit) as net FROM sales WHERE date LIKE ?", conn, params=(f'{today_str}%',))
            sales_today = df_today['sales'].iloc[0] or 0
            profit_today = df_today['net'].iloc[0] or 0
            
            col1, col2 = st.columns(2)
            col1.metric("مبيعات اليوم", f"{sales_today:,.0f}", delta="د.ع")
            col2.metric("أرباح اليوم", f"{profit_today:,.0f}", delta_color="normal")
            
            st.divider()
            
            # رسم بياني لأكثر المنتجات مبيعاً
            st.subheader("أكثر الأصناف مبيعاً (العدد)")
            df_chart = pd.read_sql("SELECT product_name, SUM(qty) as total_qty FROM sales GROUP BY product_name ORDER BY total_qty DESC LIMIT 10", conn)
            if not df_chart.empty:
                st.bar_chart(df_chart.set_index('product_name'))

# نقطة الدخول
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
