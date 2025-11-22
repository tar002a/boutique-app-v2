import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
import itertools
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(
    page_title="نواعم بوتيك", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="collapsed"
)

# --- 2. تصميم UI/UX احترافي (لوحة ألوان متناسقة) ---
st.markdown("""
<style>
    /* استيراد الخط */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    /* === 1. إعدادات الألوان والخطوط العامة === */
    :root {
        --primary-color: #D81B60;    /* وردي غامق أنيق */
        --bg-color: #F3F4F6;         /* رمادي فاتح جداً للخلفية */
        --card-bg: #FFFFFF;          /* أبيض للكروت */
        --text-main: #1F2937;        /* رمادي غامق للنصوص */
        --text-sub: #6B7280;         /* رمادي متوسط للتفاصيل */
    }

    * {
        font-family: 'Cairo', sans-serif !important;
        box-sizing: border-box;
    }

    /* إجبار التطبيق على الخلفية الفاتحة لمنع تضارب الوضع الليلي */
    .stApp {
        direction: rtl;
        background-color: var(--bg-color);
        color: var(--text-main);
    }
    
    /* === 2. إصلاح ألوان النصوص (تضارب الألوان) === */
    h1, h2, h3, h4, h5, h6, p, li, span, div {
        color: var(--text-main);
    }
    
    /* تسميات الحقول (Input Labels) */
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stMultiSelect label {
        color: var(--text-main) !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }
    
    /* النصوص داخل الحقول */
    .stTextInput input, .stNumberInput input {
        color: #000000 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB;
    }

    /* === 3. تحسين شريط التنقل العلوي === */
    div[role="radiogroup"] {
        background-color: var(--card-bg);
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        display: flex;
        justify-content: space-between;
        border: 1px solid #E5E7EB;
    }
    
    div[role="radiogroup"] label {
        background: transparent !important;
        border: none !important;
        color: var(--text-sub) !important;
        font-weight: 600 !important;
        cursor: pointer;
        transition: 0.3s;
    }
    
    /* الزر المختار في القائمة */
    div[role="radiogroup"] label[aria-checked="true"] {
        color: var(--primary-color) !important;
        background-color: #FCE4EC !important; /* خلفية وردية فاتحة جداً */
        border-radius: 8px !important;
    }

    /* === 4. تصميم البطاقات (Containers) === */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--card-bg);
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
        padding: 20px;
        margin-bottom: 15px;
    }

    /* === 5. الأزرار === */
    .stButton button {
        width: 100%;
        border-radius: 10px;
        height: 45px;
        font-weight: 700;
        border: none;
        transition: all 0.2s;
    }
    
    /* زر أساسي (وردي) */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: var(--primary-color);
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #AD1457;
    }

    /* زر ثانوي (أبيض) */
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #F3F4F6;
        color: var(--text-main) !important;
        border: 1px solid #D1D5DB;
    }

    /* إخفاء العناصر غير المرغوبة */
    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;} 
    header {visibility: hidden;}

</style>
""", unsafe_allow_html=True)

# --- 3. دوال قاعدة البيانات ---
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception:
        return None

def run_query(query, params=(), fetch_data=False, commit=True):
    conn = init_connection()
    if conn:
        try:
            if conn.closed: conn = init_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            if fetch_data:
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                cur.close()
                return pd.DataFrame(data, columns=columns)
            else:
                if commit: conn.commit()
                cur.close()
                return True
        except Exception:
            conn.rollback()
            return None
    return None

# --- 4. إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'auth' not in st.session_state: st.session_state.auth = False

# --- 5. الشاشات والمنطق ---

def login_ui():
    c1, c2, c3 = st.columns([1, 5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #D81B60;'>🌸 بوتيك نواعم</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6B7280;'>نظام الإدارة المتكامل</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            pwd = st.text_input("كلمة المرور", type="password")
            if st.button("تسجيل الدخول", type="primary"):
                if pwd == st.secrets.get("ADMIN_PASS", "admin"):
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.toast("خطأ في كلمة المرور", icon="❌")

def process_sale(customer_name):
    conn = init_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        dt = datetime.now(pytz.timezone('Asia/Baghdad'))
        inv_id = dt.strftime("%Y%m%d%H%M")
        
        cur.execute("SELECT id FROM customers WHERE name = %s", (customer_name,))
        res = cur.fetchone()
        cust_id = res[0] if res else None
        
        if not cust_id:
            cur.execute("INSERT INTO customers (name) VALUES (%s) RETURNING id", (customer_name,))
            cust_id = cur.fetchone()[0]
        
        for item in st.session_state.cart:
            cur.execute("SELECT stock FROM variants WHERE id = %s FOR UPDATE", (item['id'],))
            if cur.fetchone()[0] < item['qty']: raise Exception(f"الكمية نفذت: {item['name']}")
            
            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
            profit = (item['price'] - item['cost']) * item['qty']
            cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
            
        conn.commit(); cur.close(); return True
    except Exception as e:
        conn.rollback(); st.toast(f"خطأ: {e}", icon="⚠️"); return False

def main_app():
    # الشريط العلوي
    col_head, col_out = st.columns([6, 1])
    col_head.markdown("<h3 style='color: #D81B60; margin:0;'>🌸 نواعم بوتيك</h3>", unsafe_allow_html=True)
    if col_out.button("خروج", key="logout"):
        st.session_state.auth = False; st.rerun()

    # شريط التنقل (محسن)
    st.write("") # مسافة
    selected = st.radio("nav", ["نقطة البيع 🛒", "المخزون 📦", "التقارير 📊", "الفواتير 🧾"], horizontal=True, label_visibility="collapsed")
    st.write("") 

    # ==========================
    # 1. نقطة البيع
    # ==========================
    if "نقطة البيع" in selected:
        tab1, tab2 = st.tabs(["🛍️ عرض المنتجات", f"🛒 سلة المشتريات ({len(st.session_state.cart)})"])
        
        with tab1:
            search = st.text_input("بحث عن منتج", placeholder="اكتب الاسم أو اللون...", label_visibility="collapsed")
            
            q = "SELECT * FROM variants WHERE is_active = TRUE AND stock > 0"
            p = []
            if search:
                q += " AND (name ILIKE %s OR color ILIKE %s)"
                p = [f"%{search}%", f"%{search}%"]
            q += " ORDER BY name ASC, id DESC LIMIT 20"
            
            items = run_query(q, tuple(p), fetch_data=True)
            
            if items is not None and not items.empty:
                cols = st.columns(2)
                for i, row in items.iterrows():
                    with cols[i % 2]:
                        with st.container(border=True):
                            st.markdown(f"<div style='font-weight:bold; font-size:16px;'>{row['name']}</div>", unsafe_allow_html=True)
                            st.caption(f"🎨 {row['color']} | 📏 {row['size']}")
                            
                            c_price, c_stock = st.columns(2)
                            c_price.markdown(f"<span style='color:#D81B60; font-weight:bold'>{int(row['price']):,} د.ع</span>", unsafe_allow_html=True)
                            c_stock.markdown(f"<span style='color:#6B7280; font-size:12px'>باقي: {row['stock']}</span>", unsafe_allow_html=True)
                            
                            # أدوات الإضافة
                            cc1, cc2 = st.columns([1, 2])
                            qty = cc1.number_input("العدد", 1, max_value=row['stock'], key=f"q_{row['id']}", label_visibility="collapsed")
                            if cc2.button("إضافة ➕", key=f"add_{row['id']}", type="secondary"):
                                # منطق الإضافة
                                found = False
                                for x in st.session_state.cart:
                                    if x['id'] == row['id']:
                                        x['qty'] += qty; x['total'] += qty*row['price']; found=True; break
                                if not found: st.session_state.cart.append({"id":row['id'], "name":row['name'], "price":row['price'], "qty":qty, "total":qty*row['price'], "cost":row['cost']})
                                st.toast("تمت الإضافة", icon="✅"); st.rerun()
            else:
                st.info("لا توجد منتجات مطابقة")

        with tab2:
            if st.session_state.cart:
                total_sum = sum(x['total'] for x in st.session_state.cart)
                
                # قائمة العناصر
                for i, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        c_name, c_del = st.columns([5, 1])
                        c_name.markdown(f"**{item['name']}** <span style='font-size:0.9em; color:gray'>x{item['qty']}</span>", unsafe_allow_html=True)
                        c_name.markdown(f"<span style='color:#D81B60; font-weight:bold'>{item['total']:,.0f} د.ع</span>", unsafe_allow_html=True)
                        if c_del.button("🗑️", key=f"del_{i}"): st.session_state.cart.pop(i); st.rerun()
                
                st.divider()
                st.markdown(f"<h3 style='text-align:center; color:#D81B60'>الإجمالي: {total_sum:,.0f} د.ع</h3>", unsafe_allow_html=True)
                
                cust_name = st.text_input("اسم العميل", placeholder="الاسم مطلوب للإيصال")
                if st.button("✅ إتمام عملية البيع", type="primary"):
                    if cust_name:
                        if process_sale(cust_name):
                            st.session_state.cart = []; st.balloons(); st.success("تم حفظ الفاتورة!"); time.sleep(1); st.rerun()
                    else:
                        st.error("الرجاء كتابة اسم العميل")
            else:
                st.info("السلة فارغة حالياً")

    # ==========================
    # 2. المخزون (محسن)
    # ==========================
    elif "المخزون" in selected:
        
        # المولد السريع
        with st.expander("➕ إضافة سريعة (منتجات متعددة)", expanded=False):
            st.markdown("##### 1. تفاصيل المنتج")
            name = st.text_input("اسم المنتج (مثال: فستان صيفي)")
            
            c_col, c_siz = st.columns(2)
            colors = c_col.multiselect("الألوان", ["أحمر", "أسود", "أبيض", "بيج", "وردي", "أزرق", "أخضر", "ذهبي", "فضي"])
            sizes = c_siz.multiselect("المقاسات", ["S", "M", "L", "XL", "XXL", "Free Size", "36", "38", "40", "42", "44"])
            
            st.markdown("##### 2. التسعير والكمية")
            cc1, cc2, cc3 = st.columns(3)
            cost = cc1.number_input("التكلفة", 0.0, step=500.0)
            price = cc2.number_input("سعر البيع", 0.0, step=500.0)
            qty = cc3.number_input("العدد لكل نوع", 1)
            
            if st.button("إنشاء وإضافة للمخزون 🚀", type="primary"):
                if name and colors and sizes:
                    combs = list(itertools.product(colors, sizes))
                    conn = init_connection(); cur = conn.cursor()
                    try:
                        for co, si in combs:
                            cur.execute("INSERT INTO variants (name, color, size, stock, cost, price, is_active) VALUES (%s,%s,%s,%s,%s,%s,TRUE)", 
                                       (name, co, si, qty, cost, price))
                        conn.commit(); st.toast(f"تم إضافة {len(combs)} منتج!", icon="🎉"); st.rerun()
                    except Exception as e: conn.rollback(); st.error(f"خطأ: {e}")
                else:
                    st.warning("املأ جميع الحقول")

        st.markdown("### 📦 جرد المخزون")
        # بحث
        search_q = st.text_input("🔍 تصفية الجدول", placeholder="ابحث عن أي شيء...")
        
        # استعلام
        q_main = "SELECT id, name, color, size, stock, price, cost, is_active FROM variants"
        p_main = []
        if search_q:
            q_main += " WHERE name ILIKE %s OR color ILIKE %s"
            p_main = [f"%{search_q}%", f"%{search_q}%"]
        q_main += " ORDER BY (stock > 0) DESC, name ASC"
        
        df_inv = run_query(q_main, tuple(p_main), fetch_data=True)
        
        if df_inv is not None:
            edited = st.data_editor(
                df_inv,
                column_config={
                    "id": None,
                    "name": "الاسم",
                    "color": "اللون",
                    "size": st.column_config.TextColumn("المقاس", width="small"),
                    "stock": st.column_config.NumberColumn("العدد", min_value=0, format="%d"),
                    "price": st.column_config.NumberColumn("بيع", format="%d"),
                    "cost": st.column_config.NumberColumn("تكلفة", format="%d"),
                    "is_active": "نشط"
                },
                use_container_width=True,
                num_rows="dynamic",
                key="inv_editor",
                height=450
            )
            
            if st.button("💾 حفظ التعديلات", type="primary"):
                conn = init_connection(); cur = conn.cursor()
                try:
                    for i, row in edited.iterrows():
                        if row['id'] and not pd.isna(row['id']):
                            cur.execute("UPDATE variants SET name=%s, color=%s, size=%s, stock=%s, price=%s, cost=%s, is_active=%s WHERE id=%s", 
                                       (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], row['is_active'], row['id']))
                        else:
                            cur.execute("INSERT INTO variants (name, color, size, stock, price, cost, is_active) VALUES (%s,%s,%s,%s,%s,%s,%s)", 
                                       (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], True))
                    conn.commit(); st.toast("تم الحفظ!", icon="💾"); st.rerun()
                except Exception as e: conn.rollback(); st.error(e)

    # ==========================
    # 3. التقارير
    # ==========================
    elif "التقارير" in selected:
        days = st.selectbox("الفترة الزمنية", [1, 7, 30], format_func=lambda x: "اليوم" if x==1 else f"{x} يوم")
        d_start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        df = run_query(f"SELECT SUM(total) as s, SUM(profit) as p FROM sales WHERE date >= '{d_start}'", fetch_data=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.container(border=True).metric("إجمالي المبيعات", f"{df.iloc[0]['s'] or 0:,.0f}", "د.ع")
        with c2:
            st.container(border=True).metric("صافي الربح", f"{df.iloc[0]['p'] or 0:,.0f}", "د.ع")

    # ==========================
    # 4. الفواتير
    # ==========================
    elif "الفواتير" in selected:
        st.dataframe(
            run_query("SELECT s.invoice_id as فاتورة, c.name as عميل, s.total as مبلغ, s.date as تاريخ FROM sales s JOIN customers c ON s.customer_id=c.id ORDER BY s.id DESC LIMIT 50", fetch_data=True),
            use_container_width=True
        )

if __name__ == "__main__":
    if st.session_state.auth: main_app()
    else: login_ui()
