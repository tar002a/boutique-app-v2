import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import pytz

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem Boutique", layout="wide", page_icon="🛍️", initial_sidebar_state="collapsed")

# --- CSS لتحسين المظهر ودعم العربية ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    h1, h2, h3, h4, h5, h6 {text-align: right; font-family: 'Tajawal', sans-serif;}
    .stButton button {width: 100%; border-radius: 10px; font-weight: bold;}
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)

# --- إدارة الاتصال بقاعدة البيانات (Supabase) ---
def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات باستخدام الرابط من الأسرار"""
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
        st.error(f"فشل الاتصال بقاعدة البيانات: {e}")
        return None

def run_query(query, params=(), return_data=False):
    """دالة موحدة لتنفيذ أوامر SQL"""
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            
            if return_data:
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                df = pd.DataFrame(data, columns=columns)
                cur.close()
                conn.close()
                return df
            else:
                conn.commit()
                cur.close()
                conn.close()
                return True
        except Exception as e:
            st.error(f"خطأ SQL: {e}")
            conn.rollback()
            conn.close()
    return None

def init_db():
    """إنشاء الجداول تلقائياً إذا لم تكن موجودة"""
    # جدول المنتجات
    run_query("""
        CREATE TABLE IF NOT EXISTS variants (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT,
            size TEXT,
            cost FLOAT DEFAULT 0,
            price FLOAT DEFAULT 0,
            stock INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    # جدول العملاء
    run_query("""
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # جدول المبيعات
    run_query("""
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER,
            variant_id INTEGER,
            product_name TEXT,
            qty INTEGER,
            total FLOAT,
            profit FLOAT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            invoice_id TEXT
        );
    """)

# تشغيل تهيئة الجداول مرة واحدة
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# --- دوال مساعدة ---
def get_baghdad_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- إدارة الجلسة (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- شاشة تسجيل الدخول ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 تسجيل الدخول - نواعم")
        with st.form("login_form"):
            password = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول"):
                # كلمة المرور هنا هي admin (يمكنك تغييرها)
                if password == "admin":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة")

# --- التطبيق الرئيسي ---
def main_app():
    # القائمة الجانبية
    with st.sidebar:
        st.title("🌸 نواعم بوتيك")
        st.write(f"التاريخ: {get_baghdad_time().strftime('%Y-%m-%d')}")
        if st.button("تسجيل خروج"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["🛒 نقطة بيع", "📦 المخزون", "📋 سجل المبيعات", "👥 العملاء", "📊 التقارير"])

    # === 1. نقطة البيع ===
    with tabs[0]:
        c_pos, c_cart = st.columns([2, 1])
        
        with c_pos:
            st.subheader("🔍 بحث عن منتج")
            search = st.text_input("اسم المنتج أو اللون", label_visibility="collapsed")
            
            # جلب المنتجات النشطة والتي بها مخزون
            query = "SELECT * FROM variants WHERE stock > 0 AND is_active = TRUE"
            params = []
            if search:
                query += " AND (name ILIKE %s OR color ILIKE %s)"
                params = [f'%{search}%', f'%{search}%']
            
            df_items = run_query(query, tuple(params), return_data=True)
            
            if df_items is not None and not df_items.empty:
                for _, row in df_items.iterrows():
                    with st.container(border=True):
                        cc1, cc2, cc3 = st.columns([3, 2, 2])
                        with cc1:
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['color']} | {row['size']} | باقي: {row['stock']}")
                        with cc2:
                            price = st.number_input("السعر", value=float(row['price']), key=f"p_{row['id']}")
                        with cc3:
                            if st.button("أضف للسلة ➕", key=f"add_{row['id']}"):
                                st.session_state.cart.append({
                                    "id": row['id'], "name": row['name'], "color": row['color'],
                                    "size": row['size'], "qty": 1, "price": price, 
                                    "cost": row['cost'], "total": price
                                })
                                st.toast("تمت الإضافة للسلة!", icon="✅")
                                st.rerun()
            else:
                st.info("لا توجد منتجات مطابقة أو المخزون نفذ.")

        with c_cart:
            st.subheader("🛒 سلة المشتريات")
            if st.session_state.cart:
                total_cart = 0
                for i, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"{item['name']} - {item['color']}")
                        c1.caption(f"{item['price']:,.0f} د.ع")
                        total_cart += item['total']
                        if c2.button("❌", key=f"del_{i}"):
                            st.session_state.cart.pop(i)
                            st.rerun()
                
                st.divider()
                st.markdown(f"### المجموع: {total_cart:,.0f} د.ع")
                
                cust_name = st.text_input("اسم العميل (للحفظ)")
                
                if st.button("✅ إتمام البيع", type="primary"):
                    if not cust_name:
                        st.error("الرجاء كتابة اسم العميل")
                    else:
                        # 1. حفظ العميل
                        run_query("INSERT INTO customers (name) VALUES (%s)", (cust_name,))
                        # نحتاج معرف العميل (يمكن جلبه باستعلام آخر ولكن للتبسيط سنعتمد الاسم حالياً أو نطور الكود لاحقاً)
                        # هنا سنجلب آخر عميل تمت إضافته بهذا الاسم
                        cust_data = run_query("SELECT id FROM customers WHERE name = %s ORDER BY id DESC LIMIT 1", (cust_name,), return_data=True)
                        cust_id = int(cust_data.iloc[0]['id']) if not cust_data.empty else None

                        # 2. حفظ المبيعات وتحديث المخزون
                        inv_id = get_baghdad_time().strftime("%Y%m%d%H%M")
                        dt = get_baghdad_time()
                        
                        for item in st.session_state.cart:
                            # خصم المخزون
                            run_query("UPDATE variants SET stock = stock - 1 WHERE id = %s", (item['id'],))
                            # تسجيل البيع
                            profit = item['price'] - item['cost']
                            run_query("""
                                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (cust_id, item['id'], item['name'], 1, item['total'], profit, dt, inv_id))
                        
                        st.session_state.cart = []
                        st.success("تم حفظ الفاتورة بنجاح!")
                        st.balloons()
                        st.rerun()

    # === 2. المخزون ===
    with tabs[1]:
        st.subheader("إضافة منتج جديد")
        with st.form("add_item"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("اسم المنتج")
            color = c2.text_input("اللون")
            size = c3.text_input("القياس")
            c4, c5, c6 = st.columns(3)
            stock = c4.number_input("العدد", min_value=1, value=10)
            cost = c5.number_input("سعر التكلفة", value=0.0)
            price = c6.number_input("سعر البيع", value=0.0)
            
            if st.form_submit_button("💾 حفظ المنتج"):
                run_query("""
                    INSERT INTO variants (name, color, size, stock, cost, price)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, color, size, stock, cost, price))
                st.success("تمت الإضافة!")
        
        st.divider()
        st.subheader("المخزون الحالي")
        df_stock = run_query("SELECT * FROM variants WHERE is_active = TRUE ORDER BY id DESC", return_data=True)
        if df_stock is not None:
            st.dataframe(df_stock, use_container_width=True)

    # === 3. سجل المبيعات ===
    with tabs[2]:
        st.subheader("آخر عمليات البيع")
        df_sales = run_query("""
            SELECT s.id, s.product_name, s.total, s.date, c.name as customer
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.id
            ORDER BY s.id DESC LIMIT 50
        """, return_data=True)
        
        if df_sales is not None:
            st.dataframe(df_sales, use_container_width=True)

    # === 4. العملاء ===
    with tabs[3]:
        df_cust = run_query("SELECT * FROM customers ORDER BY id DESC", return_data=True)
        if df_cust is not None:
            st.dataframe(df_cust, use_container_width=True)

    # === 5. التقارير ===
    with tabs[4]:
        st.header("📊 ملخص الأداء")
        # إحصائيات اليوم
        today_start = get_baghdad_time().strftime('%Y-%m-%d 00:00:00')
        stats = run_query("""
            SELECT SUM(total) as sales, SUM(profit) as profit 
            FROM sales 
            WHERE date >= %s
        """, (today_start,), return_data=True)
        
        col1, col2 = st.columns(2)
        sales_today = stats.iloc[0]['sales'] if stats is not None and stats.iloc[0]['sales'] else 0
        profit_today = stats.iloc[0]['profit'] if stats is not None and stats.iloc[0]['profit'] else 0
        
        col1.metric("مبيعات اليوم", f"{sales_today:,.0f} د.ع")
        col2.metric("أرباح اليوم", f"{profit_today:,.0f} د.ع")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
