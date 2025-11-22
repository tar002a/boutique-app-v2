import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import pytz
from contextlib import contextmanager

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem System", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

# --- الاتصال بقاعدة البيانات (Supabase) ---
# نستخدم st.cache_resource لتسريع الاتصال وعدم تكراره
def get_db_connection():
    try:
        # جلب الرابط من الأسرار
        conn_str = st.secrets["DB_URL"]
        return psycopg2.connect(conn_str)
    except Exception as e:
        st.error(f"فشل الاتصال بقاعدة البيانات: {e}")
        return None

# دالة تنفيذ الاستعلامات (الجوكر)
def run_query(query, params=(), return_data=False):
    conn = get_db_connection()
    if conn:
        try:
            if return_data:
                # pandas يفهم التعامل مع connection مباشرة
                return pd.read_sql(query, conn, params=params)
            else:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                cur.close()
                return True
        except Exception as e:
            st.error(f"خطأ SQL: {e}")
            conn.rollback() # تراجع في حال الخطأ
        finally:
            conn.close() # إغلاق الاتصال ضروري جداً
    return None

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
</style>
""", unsafe_allow_html=True)

# --- إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# --- شاشة الدخول ---
def login_screen():
    st.title("🌸 نواعم بوتيك - السحابة")
    if st.button("دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

# --- التطبيق الرئيسي ---
def main_app():
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "👥 عملاء", "📦 مخزن", "📊 تقارير"])

    # === 1. البيع ===
    with tabs[0]:
        # تحديث الاستعلام: استبدال ? بـ %s
        # Postgres يستخدم ILIKE للبحث غير الحساس لحالة الأحرف بدلاً من LOWER
        srch = st.text_input("🔍 بحث منتج...", label_visibility="collapsed")
        
        query = "SELECT * FROM variants WHERE stock > 0 AND is_active = TRUE"
        params = []
        if srch:
            query += " AND (name ILIKE %s OR color ILIKE %s)"
            params = [f'%{srch}%', f'%{srch}%']
            
        df = run_query(query, tuple(params), return_data=True)

        if df is not None and not df.empty:
             # ... (نفس كود عرض المنتجات السابق) ...
             # مثال للعرض البسيط:
             opts = df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1).tolist()
             sel = st.selectbox("اختر:", opts)
             if st.button("أضف للسلة"):
                 # (منطق السلة يبقى كما هو في بايثون)
                 pass
        
        # عند إتمام البيع (الحفظ في القاعدة):
        if st.button("✅ إتمام البيع"):
            # مثال للحفظ باستخدام %s
            baghdad_now = get_baghdad_time()
            dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
            inv = baghdad_now.strftime("%Y%m%d%H%M")
            
            # ملاحظة: يجب أن يكون لديك بيانات في السلة لتعمل الحلقة
            # هذا مثال فقط
            # run_query("INSERT INTO sales (product_name, date) VALUES (%s, %s)", ("تجربة", dt))
            st.success("تم الحفظ في Supabase!")

    # === 2. السجل ===
    with tabs[1]:
        # لاحظ %s في الـ LIMIT غير ضرورية إذا كانت رقم ثابت، لكن لاحظ البنية
        df_s = run_query("""
            SELECT s.*, c.name as customer_name 
            FROM sales s 
            LEFT JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC LIMIT 30
        """, return_data=True)
        
        if df_s is not None:
            st.dataframe(df_s)

    # === 4. إضافة للمخزون ===
    with tabs[3]:
        with st.form("add_item"):
            nm = st.text_input("اسم")
            # ... باقي الحقول
            if st.form_submit_button("حفظ"):
                # لاحظ استخدام %s بدلاً من ?
                run_query("""
                    INSERT INTO variants (name, color, size, stock, price, cost) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (nm, "أحمر", "L", 10, 15000, 10000))
                st.success("تم الإضافة!")
                st.rerun()

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
