import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import psycopg2
import time

# --- 1. إعداد الصفحة (يجب أن يكون أول سطر) ---
# initial_sidebar_state="expanded" مهم جداً لظهور القائمة
st.set_page_config(page_title="Nawaem POS 🚀", layout="wide", page_icon="🛍️", initial_sidebar_state="expanded")

# --- 2. CSS وتصميم UI وإصلاح RTL للقائمة ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    /* تطبيق الخط على كل العناصر */
    * { font-family: 'Cairo', sans-serif !important; }

    /* خلفية التطبيق */
    .stApp { background-color: #121212; }

    /* --- إصلاح اتجاه العربي والقائمة الجانبية --- */
    /* نجعل المحتوى فقط يمين-يسار وليس هيكل الصفحة كاملة */
    [data-testid="stSidebar"], .stMain {
        direction: rtl;
        text-align: right;
    }
    
    /* إصلاح المحاذاة للنصوص */
    p, h1, h2, h3, h4, h5, h6, span, div, label, .stButton, .stTextInput, .stNumberInput, .stSelectbox {
        text-align: right !important;
    }

    /* إصلاح حقول الإدخال */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        direction: rtl;
        text-align: right;
        background-color: #2C2C2E !important;
        color: white !important;
        border-radius: 10px !important;
    }

    /* --- تصميم بطاقات المنتجات --- */
    .product-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 16px;
        padding: 15px;
        text-align: center;
        transition: transform 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .product-card:hover {
        border-color: #B76E79;
        transform: translateY(-5px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .price-tag {
        font-size: 1.2rem;
        font-weight: 800;
        color: #B76E79;
        margin: 8px 0;
    }
    .stock-tag {
        font-size: 0.8rem;
        color: #A0A0A0;
        background: #2c2c2e;
        padding: 2px 8px;
        border-radius: 8px;
    }

    /* --- تنسيق الأزرار --- */
    .stButton button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        height: 45px;
        width: 100%;
    }
    
    /* إخفاء القوائم الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. إدارة الحالة (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'page' not in st.session_state: st.session_state.page = 0

# --- 4. دوال قاعدة البيانات (Backend Logic) ---
@st.cache_resource
def init_connection():
    # تأكد من وجود secrets.toml محلياً أو في إعدادات Streamlit Cloud
    return psycopg2.connect(**st.secrets["postgres"])

def run_query(query, params=None, fetch_df=False):
    """دالة مركزية لتنفيذ الاستعلامات بأمان"""
    conn = None
    try:
        conn = init_connection()
        if fetch_df:
            return pd.read_sql(query, conn, params=params)
        else:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if query.strip().upper().startswith("INSERT") or query.strip().upper().startswith("UPDATE"):
                    conn.commit()
                    return True
                else:
                    return cur.fetchall()
    except Exception as e:
        if conn: conn.rollback()
        st.toast(f"حدث خطأ: {e}", icon="❌")
        return None

# دالة البحث السريع (Server-Side)
def search_products_sql(search_term, limit=30):
    if not search_term:
        q = "SELECT id, name, color, size, price, stock FROM public.variants WHERE stock > 0 ORDER BY id DESC LIMIT %s"
        return run_query(q, (limit,), fetch_df=True)
    else:
        search_pattern = f"%{search_term}%"
        q = """
            SELECT id, name, color, size, price, stock 
            FROM public.variants 
            WHERE stock > 0 AND (name ILIKE %s OR color ILIKE %s OR size ILIKE %s)
            LIMIT %s
        """
        return run_query(q, (search_pattern, search_pattern, search_pattern, limit), fetch_df=True)

# --- 5. واجهة المستخدم (UI Functions) ---

def render_pos_tab():
    """نقطة البيع"""
    col_products, col_cart = st.columns([3, 1.2])

    # === قسم المنتجات ===
    with col_products:
        c1, c2 = st.columns([4, 1])
        search_txt = c1.text_input("🔍 بحث سريع...", key="pos_search", placeholder="اسم، لون، أو قياس")
        c2.markdown(f"<div style='text-align:center; padding-top:25px; color:#666; font-size:0.8em'>Server Search Active</div>", unsafe_allow_html=True)
        
        df = search_products_sql(search_txt, limit=21) # جلب 21 منتج
        
        if not df.empty:
            cols = st.columns(3) # شبكة من 3 أعمدة
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div class="product-card">
                        <div style="font-weight:700; font-size:1.1em; color:white;">{row['name']}</div>
                        <div style="font-size:0.9em; color:#ccc;">{row['color']} | {row['size']}</div>
                        <div class="price-tag">{row['price']:,.0f} د.ع</div>
                        <div class="stock-tag">متبقي: {row['stock']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("🛒 أضف", key=f"add_{row['id']}", type="secondary"):
                        add_to_cart(row)
                    st.markdown("<div style='margin-bottom:15px'></div>", unsafe_allow_html=True)
        else:
            st.warning("لا توجد نتائج مطابقة")

    # === قسم السلة ===
    with col_cart:
        with st.container(border=True):
            st.markdown("### 🧾 الفاتورة")
            if not st.session_state.cart:
                st.info("السلة فارغة")
            else:
                total_cart = 0
                for pid, item in list(st.session_state.cart.items()):
                    total_item = item['price'] * item['qty']
                    total_cart += total_item
                    
                    c_det, c_act = st.columns([3, 1])
                    with c_det:
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"{item['color']} | {item['size']}")
                        # تحديث الكمية
                        new_qty = st.number_input(f"qty_{pid}", 1, int(item['max_stock']), int(item['qty']), key=f"q_{pid}", label_visibility="collapsed")
                        if new_qty != item['qty']:
                            st.session_state.cart[pid]['qty'] = new_qty
                            st.rerun()
                        st.markdown(f"<span style='color:#B76E79'>{total_item:,.0f}</span>", unsafe_allow_html=True)
                    
                    with c_act:
                        if st.button("🗑️", key=f"del_{pid}"):
                            del st.session_state.cart[pid]
                            st.rerun()
                    st.divider()

                # المجموع والدفع
                st.markdown(f"<h2 style='text-align:center; color:#B76E79;'>{total_cart:,.0f} د.ع</h2>", unsafe_allow_html=True)
                
                with st.form("checkout"):
                    cust_name = st.text_input("العميل", placeholder="الاسم أو الحساب")
                    cust_phone = st.text_input("الهاتف")
                    cust_addr = st.text_input("العنوان")
                    del_time = st.selectbox("التوصيل", ["24 ساعة", "48 ساعة", "أسبوع"])
                    
                    if st.form_submit_button("✅ تثبيت الطلب", type="primary"):
                        process_sale(cust_name, cust_phone, cust_addr, del_time)

def add_to_cart(row):
    pid = row['id']
    if pid in st.session_state.cart:
        if st.session_state.cart[pid]['qty'] < row['stock']:
            st.session_state.cart[pid]['qty'] += 1
            st.toast("تمت زيادة الكمية", icon="➕")
        else:
            st.toast("نفدت الكمية المتوفرة", icon="⚠️")
    else:
        st.session_state.cart[pid] = {
            'id': row['id'], 'name': row['name'], 'color': row['color'], 
            'size': row['size'], 'price': float(row['price']), 
            'max_stock': row['stock'], 'qty': 1
        }
        st.toast("تمت الإضافة", icon="🛒")

def process_sale(name, phone, addr, duration):
    if not name or not st.session_state.cart:
        st.error("البيانات ناقصة!")
        return
        
    try:
        conn = init_connection()
        with conn.cursor() as cur:
            # 1. العميل
            cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s, %s, %s, %s) RETURNING id", 
                        (name, phone, addr, name))
            cust_id = cur.fetchone()[0]
            
            # 2. الفاتورة
            tz = pytz.timezone('Asia/Baghdad')
            now = datetime.now(tz)
            inv_id = now.strftime("%Y%m%d%H%M")
            
            for pid, item in st.session_state.cart.items():
                cur.execute("SELECT cost FROM public.variants WHERE id=%s", (pid,))
                cost = cur.fetchone()[0]
                profit = (item['price'] - cost) * item['qty']
                
                cur.execute("UPDATE public.variants SET stock=stock-%s WHERE id=%s", (item['qty'], pid))
                cur.execute("""INSERT INTO public.sales 
                    (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", 
                    (cust_id, pid, item['name'], item['qty'], item['price']*item['qty'], profit, now, inv_id, duration))
            conn.commit()
            
            st.session_state.cart = {}
            st.success("تم الطلب بنجاح! 🎉")
            st.balloons()
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"خطأ: {e}")

def render_inventory_tab():
    st.markdown("### 📦 إدارة المخزون (سريع)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        q = st.text_input("بحث في المخزون...", key="inv_q")
    with col2:
        if st.button("➕ صنف جديد", type="primary", use_container_width=True):
            add_product_dialog()

    # Pagination Logic
    PAGE_SIZE = 15
    offset = st.session_state.page * PAGE_SIZE
    
    if q:
        query = f"SELECT * FROM public.variants WHERE name ILIKE %s ORDER BY id DESC LIMIT {PAGE_SIZE} OFFSET {offset}"
        df = run_query(query, (f"%{q}%",), fetch_df=True)
    else:
        query = f"SELECT * FROM public.variants ORDER BY id DESC LIMIT {PAGE_SIZE} OFFSET {offset}"
        df = run_query(query, fetch_df=True)
        
    if not df.empty:
        # عرض البيانات بشكل جدول قابل للتعديل (Read-Only حالياً للأمان والأداء)
        st.dataframe(
            df, 
            column_config={
                "id": "ID", "name": "الاسم", "color": "اللون", 
                "size": "القياس", "stock": "العدد", "price": "البيع", "cost": "الكلفة"
            },
            use_container_width=True, hide_index=True
        )
    
    # أزرار التنقل بين الصفحات
    c_prev, c_curr, c_next = st.columns([1, 2, 1])
    if c_prev.button("السابق ⬅️") and st.session_state.page > 0:
        st.session_state.page -= 1
        st.rerun()
    c_curr.markdown(f"<div style='text-align:center'>صفحة {st.session_state.page + 1}</div>", unsafe_allow_html=True)
    if c_next.button("التالي ➡️") and len(df) == PAGE_SIZE:
        st.session_state.page += 1
        st.rerun()

@st.dialog("إضافة منتج")
def add_product_dialog():
    with st.form("add_p"):
        name = st.text_input("الاسم")
        c1, c2 = st.columns(2)
        col = c1.text_input("اللون")
        siz = c2.text_input("القياس")
        c3, c4, c5 = st.columns(3)
        stk = c3.number_input("العدد", 1)
        prc = c4.number_input("البيع", 0.0)
        cst = c5.number_input("الكلفة", 0.0)
        if st.form_submit_button("حفظ"):
            run_query("INSERT INTO public.variants (name, color, size, stock, price, cost) VALUES (%s,%s,%s,%s,%s,%s)", 
                      (name, col, siz, stk, prc, cst))
            st.rerun()

@st.cache_data(ttl=300)
def get_metrics():
    conn = init_connection()
    q = """SELECT 
           (SELECT COALESCE(SUM(total),0) FROM public.sales WHERE date >= CURRENT_DATE) as s,
           (SELECT COALESCE(SUM(profit),0) FROM public.sales WHERE date >= CURRENT_DATE) as p,
           (SELECT COALESCE(SUM(amount),0) FROM public.expenses WHERE date >= CURRENT_DATE) as e"""
    return pd.read_sql(q, conn).iloc[0]

def render_dashboard():
    st.markdown("### 📊 ملخص اليوم (تحديث كل 5 دقائق)")
    m = get_metrics()
    c1, c2, c3 = st.columns(3)
    c1.metric("مبيعات", f"{m['s']:,.0f}")
    c2.metric("صافي", f"{m['p'] - m['e']:,.0f}")
    c3.metric("مصاريف", f"{m['e']:,.0f}")

# --- 6. التشغيل الرئيسي ---
def main():
    with st.sidebar:
        st.title("نواعم بوتيك")
        page = st.radio("القائمة", ["🛒 بيع", "📦 مخزن", "📊 تقارير"])
        st.divider()
        if st.button("تحديث 🔄"): st.cache_data.clear(); st.rerun()
    
    if page == "🛒 بيع": render_pos_tab()
    elif page == "📦 مخزن": render_inventory_tab()
    elif page == "📊 تقارير": render_dashboard()

if __name__ == "__main__":
    main()
