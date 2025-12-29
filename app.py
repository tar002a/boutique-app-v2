import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import execute_values
import time

# --- 1. إعداد الصفحة والتصميم (Configuration & CSS) ---
st.set_page_config(
    page_title="Nawaem POS 🚀", 
    layout="wide", 
    page_icon="🌸", 
    initial_sidebar_state="expanded"
)

# تصميم عصري محسّن (Enhanced Glassmorphism & Dark Mode)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    :root {
        --primary: #D48896;
        --primary-dark: #B86B7A;
        --primary-light: #E8A5B0;
        --bg-dark: #0E1117;
        --bg-card: #1A1D24;
        --bg-elevated: #22262F;
        --text-primary: #FFFFFF;
        --text-secondary: #9CA3AF;
        --text-muted: #6B7280;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --border-color: rgba(255, 255, 255, 0.08);
    }

    * { 
        font-family: 'Cairo', sans-serif !important; 
        direction: rtl; 
    }
    
    .stApp { 
        background: linear-gradient(135deg, var(--bg-dark) 0%, #151820 100%);
    }
    
    /* === القائمة الجانبية المحسّنة === */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161A22 0%, #1A1E28 100%);
        border-left: 1px solid var(--border-color);
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 0 !important;
    }

    /* === الكروت والحاويات === */
    div.stContainer, div[data-testid="stExpander"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 16px;
        backdrop-filter: blur(10px);
    }
    
    /* === حقول الإدخال المحسّنة === */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: var(--bg-elevated) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(212, 136, 150, 0.15) !important;
    }

    /* === الأزرار المحسّنة === */
    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        border: none;
        padding: 0.65rem 1.3rem;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        text-shadow: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(212, 136, 150, 0.25);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* زر أساسي */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    }
    
    /* === مقاييس الأداء === */
    div[data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
    }
    
    div[data-testid="stMetricDelta"] > div {
        font-weight: 600 !important;
    }

    /* === كروت المقاييس === */
    div[data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 18px !important;
    }
    
    /* === جداول البيانات === */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* === الفواصل === */
    hr {
        border-color: var(--border-color) !important;
        margin: 1.5rem 0 !important;
    }
    
    /* === شارات الحالة === */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-success { background: rgba(16, 185, 129, 0.15); color: var(--success); }
    .status-warning { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
    .status-danger { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
    
    /* === عناصر السلة === */
    .cart-item {
        background: var(--bg-elevated);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        border: 1px solid var(--border-color);
        transition: all 0.2s ease;
    }
    .cart-item:hover {
        border-color: var(--primary);
        transform: translateX(-4px);
    }
    
    /* === مجموع الفاتورة === */
    .total-card {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, rgba(212, 136, 150, 0.12) 0%, rgba(212, 136, 150, 0.05) 100%);
        border-radius: 16px;
        border: 1px solid rgba(212, 136, 150, 0.2);
        margin-bottom: 16px;
    }
    .total-label { 
        font-size: 13px; 
        color: var(--text-secondary);
        margin-bottom: 4px;
    }
    .total-value { 
        font-size: 36px; 
        font-weight: 800; 
        color: var(--primary);
        line-height: 1.2;
    }
    .total-currency {
        font-size: 16px;
        color: var(--primary-light);
    }
    
    /* === حالة السلة الفارغة === */
    .empty-cart {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-muted);
    }
    .empty-cart-icon {
        font-size: 48px;
        margin-bottom: 12px;
        opacity: 0.5;
    }
    
    /* === رأس العلامة التجارية === */
    .brand-header {
        text-align: center;
        padding: 24px 12px;
        margin-bottom: 8px;
    }
    .brand-icon {
        font-size: 52px;
        display: block;
        margin-bottom: 8px;
    }
    .brand-name {
        font-size: 22px;
        font-weight: 800;
        color: var(--primary);
        margin: 0;
    }
    .brand-tagline {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 4px;
    }
    
    /* === بطاقة المنتج المختار === */
    .product-preview {
        background: var(--bg-elevated);
        border-radius: 14px;
        padding: 16px;
        border: 1px solid var(--border-color);
        margin: 12px 0;
    }
    
    /* === تحسين الـ Expander === */
    div[data-testid="stExpander"] > details > summary {
        background: var(--bg-elevated);
        border-radius: 10px;
        padding: 12px 16px !important;
    }
    
    /* === الرسائل === */
    .stAlert {
        border-radius: 12px !important;
    }
    
    /* === شريط التقدم للمخزون === */
    .stock-bar {
        height: 6px;
        border-radius: 3px;
        background: var(--bg-elevated);
        overflow: hidden;
    }
    .stock-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    /* === تخصيص شريط التمرير === */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--bg-elevated);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #3A3F4B;
    }
    
    /* === عرض مخزون الملابس === */
    .model-card {
        background: linear-gradient(135deg, #22262F 0%, #1E2128 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        transition: all 0.2s ease;
    }
    .model-card:hover {
        border-color: #D48896;
        transform: translateY(-2px);
    }
    .model-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .model-name {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
    }
    .model-total {
        background: rgba(212, 136, 150, 0.15);
        color: #D48896;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .colors-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .color-block {
        background: #2A2E38;
        border-radius: 10px;
        padding: 12px;
        min-width: 140px;
        flex: 1;
    }
    .color-name {
        font-size: 14px;
        font-weight: 600;
        color: #E8A5B0;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .sizes-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .size-chip {
        padding: 6px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
        min-width: 45px;
    }
    .size-chip.stock-good {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .size-chip.stock-low {
        background: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .size-chip.stock-out {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
        text-decoration: line-through;
        opacity: 0.6;
    }
    .price-tag {
        font-size: 11px;
        color: #9CA3AF;
        margin-top: 6px;
    }
    .legend {
        display: flex;
        gap: 16px;
        justify-content: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #9CA3AF;
    }
    .legend-dot {
        width: 12px;
        height: 12px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. الاتصال بقاعدة البيانات (Database Layer) ---

@st.cache_resource
def get_db_connection():
    """إنشاء اتصال دائم (Singleton)"""
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except psycopg2.Error as e:
        st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        st.stop()
    except KeyError:
        st.error("❌ لم يتم العثور على إعدادات قاعدة البيانات في secrets.toml")
        st.info("تأكد من إنشاء ملف `.streamlit/secrets.toml` بإعدادات PostgreSQL")
        st.stop()

def run_query(query, params=None, fetch=True, commit=False):
    """دالة مساعدة لتنفيذ الاستعلامات بأمان"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
                return True
            if fetch:
                col_names = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                return pd.DataFrame(data, columns=col_names)
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"❌ خطأ في قاعدة البيانات: {e}")
        return None

def init_db():
    """تهيئة الجداول عند أول تشغيل"""
    conn = get_db_connection()
    with conn.cursor() as c:
        # جدول المنتجات
        c.execute("""CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, 
            cost REAL, price REAL, stock INTEGER
        )""")
        # جدول العملاء
        c.execute("""CREATE TABLE IF NOT EXISTS public.customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        # جدول المبيعات
        c.execute("""CREATE TABLE IF NOT EXISTS public.sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TIMESTAMP, invoice_id TEXT, delivery_duration TEXT
        )""")
        # جدول المصاريف
        c.execute("""CREATE TABLE IF NOT EXISTS public.expenses (
            id SERIAL PRIMARY KEY, amount REAL, reason TEXT, category TEXT, date TIMESTAMP
        )""")
        # جدول الرواجع
        c.execute("""CREATE TABLE IF NOT EXISTS public.returns (
            id SERIAL PRIMARY KEY, sale_id INTEGER, variant_id INTEGER, customer_id INTEGER,
            product_name TEXT, product_details TEXT, qty INTEGER, return_amount REAL, 
            return_date TIMESTAMP, status TEXT
        )""")
        conn.commit()

# --- 3. جلب البيانات (Caching & Optimization) ---

@st.cache_data(ttl=60)
def get_inventory():
    return run_query("SELECT * FROM public.variants ORDER BY name")

@st.cache_data(ttl=300)
def get_customers():
    return run_query("SELECT * FROM public.customers ORDER BY name")

@st.cache_data(ttl=60)
def get_sales(limit=100):
    return run_query(f"SELECT * FROM public.sales ORDER BY date DESC LIMIT {limit}")

@st.cache_data(ttl=300)
def get_expenses():
    return run_query("SELECT * FROM public.expenses ORDER BY date DESC")

def clear_all_cache():
    """تفريغ الكاش لتحديث البيانات"""
    get_inventory.clear()
    get_customers.clear()
    get_sales.clear()
    get_expenses.clear()

def get_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- 4. دوال مساعدة للواجهة ---

def get_stock_status(stock):
    """الحصول على حالة المخزون بشكل مرئي"""
    if stock <= 0:
        return ("🔴 نفذ", "danger")
    elif stock < 3:
        return ("🟡 قليل", "warning")
    else:
        return ("🟢 متوفر", "success")

def render_stock_bar(stock, max_stock=20):
    """رسم شريط تقدم المخزون"""
    percentage = min(100, (stock / max_stock) * 100)
    color = "#EF4444" if stock < 3 else "#F59E0B" if stock < 6 else "#10B981"
    return f"""
    <div class="stock-bar">
        <div class="stock-bar-fill" style="width: {percentage}%; background: {color};"></div>
    </div>
    """

# --- 5. منطق التطبيق (Callbacks Logic) ---

if 'cart' not in st.session_state: 
    st.session_state.cart = []
if 'db_inited' not in st.session_state:
    init_db()
    st.session_state.db_inited = True

def add_to_cart_callback():
    selection = st.session_state.get('pos_selection')
    if not selection: 
        return
    
    df = get_inventory()
    try:
        prod_name = selection.split(" | ")[0]
        prod_color = selection.split(" | ")[1].split(" (")[0]
        item_row = df[(df['name'] == prod_name) & (df['color'] == prod_color)].iloc[0]
        
        qty = st.session_state.get('pos_qty', 1)
        price = st.session_state.get('pos_price', item_row['price'])
        
        cart_item = {
            "id": int(item_row['id']), 
            "name": item_row['name'],
            "color": item_row['color'], 
            "size": item_row['size'],
            "price": price, 
            "qty": qty, 
            "cost": float(item_row['cost']),
            "total": price * qty
        }
        st.session_state.cart.append(cart_item)
        st.toast(f"🛒 أضيف: {item_row['name']}", icon="✅")
    except IndexError:
        st.error("❌ لم يتم العثور على المنتج")
    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء إضافة المنتج: {e}")

def remove_from_cart_callback(idx):
    if 0 <= idx < len(st.session_state.cart):
        removed = st.session_state.cart.pop(idx)
        st.toast(f"🗑️ أُزيل: {removed['name']}", icon="✅")

def checkout_callback():
    if not st.session_state.cart:
        st.error("❌ السلة فارغة")
        return

    c_select = st.session_state.get('c_select')
    c_name = st.session_state.get('c_name')
    if c_select == "➕ عميل جديد" and not c_name:
        st.error("❌ الاسم مطلوب")
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # معالجة العميل
            cust_id = None
            if c_select == "➕ عميل جديد":
                cur.execute(
                    "INSERT INTO public.customers (name, phone, address, username) VALUES (%s, %s, %s, %s) RETURNING id", 
                    (c_name, st.session_state.get('c_phone', ''), st.session_state.get('c_addr', ''), c_name)
                )
                cust_id = cur.fetchone()[0]
                customer_display = c_name
                customer_addr = st.session_state.get('c_addr', '')
            else:
                df_cust = get_customers()
                cust_data = df_cust[df_cust['name'] == c_select].iloc[0]
                cust_id = int(cust_data['id'])
                customer_display = cust_data['name']
                customer_addr = cust_data['address']

            # تحضير البيانات للإدخال الدفعي
            inv_id = get_time().strftime("%Y%m%d%H%M")
            sales_data = []
            
            for item in st.session_state.cart:
                cur.execute("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
                profit = (item['price'] - item['cost']) * item['qty']
                sales_data.append((
                    cust_id, item['id'], item['name'], item['qty'], item['total'], 
                    profit, get_time(), inv_id, st.session_state.get('c_dur', '24 ساعة')
                ))

            execute_values(cur, """
                INSERT INTO public.sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                VALUES %s
            """, sales_data)

            conn.commit()
            
            # إنشاء نص الفاتورة
            msg = f"🧾 فاتورة ({inv_id})\n👤 {customer_display}\n" + "─"*25 + "\n"
            total = 0
            for it in st.session_state.cart:
                msg += f"▫️ {it['name']} ({it['color']}) x{it['qty']} = {it['total']:,.0f}\n"
                total += it['total']
            msg += "─"*25 + f"\n💰 الإجمالي: {total:,.0f} د.ع\n📍 {customer_addr}"
            
            st.session_state.last_inv = msg
            st.session_state.cart = []
            clear_all_cache()
            
    except Exception as e:
        conn.rollback()
        st.error(f"❌ فشلت العملية: {e}")

# --- 6. واجهة المستخدم (Layout) ---

with st.sidebar:
    # العلامة التجارية
    st.markdown("""
    <div class="brand-header">
        <span class="brand-icon">🌸</span>
        <h2 class="brand-name">نواعم بوتيك</h2>
        <p class="brand-tagline">نظام إدارة نقاط البيع</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # التنقل
    page = st.radio(
        "التنقل", 
        ["🛒 نقطة البيع", "📦 المخزون", "📊 التقارير", "👥 العملاء", "📜 السجل", "💸 المصاريف"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # أزرار سريعة
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 تحديث", use_container_width=True, help="تحديث جميع البيانات"):
            clear_all_cache()
            st.rerun()
    with col2:
        if st.button("🧹 تفريغ", use_container_width=True, help="تفريغ السلة"):
            st.session_state.cart = []
            st.rerun()
    
    # ملخص سريع
    st.divider()
    df_inv = get_inventory()
    if df_inv is not None and not df_inv.empty:
        total_items = df_inv['stock'].sum()
        low_stock = len(df_inv[df_inv['stock'] < 3])
        st.caption(f"📦 المخزون: {total_items} قطعة")
        if low_stock > 0:
            st.caption(f"⚠️ نواقص: {low_stock} موديل")

# ==========================================
# صفحة 1: نقطة البيع (POS)
# ==========================================
if page == "🛒 نقطة البيع":
    col_pos, col_cart = st.columns([2, 1.2], gap="large")

    # >> القسم الأيمن: المنتجات والبحث
    with col_pos:
        st.markdown("### 🔍 البحث والمنتجات")
        df_inv = get_inventory()
        
        if df_inv is not None and not df_inv.empty:
            df_active = df_inv[df_inv['stock'] > 0].copy()
            df_active['display'] = df_active['name'] + " | " + df_active['color'] + " (" + df_active['size'] + ")"
            
            st.selectbox(
                "بحث عن منتج:", 
                options=df_active['display'].tolist(), 
                index=None, 
                key="pos_selection",
                placeholder="🔎 اكتب اسم المنتج أو اللون للبحث..."
            )

            # عرض تفاصيل المنتج المختار
            if st.session_state.get('pos_selection'):
                sel = st.session_state.pos_selection
                item = df_active[df_active['display'] == sel].iloc[0]
                
                # بطاقة المنتج
                st.markdown(f"""
                <div class="product-preview">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="margin: 0; color: var(--text-primary);">{item['name']}</h4>
                        <span class="status-badge status-{'success' if item['stock'] >= 3 else 'warning' if item['stock'] > 0 else 'danger'}">
                            {item['stock']} متوفر
                        </span>
                    </div>
                    <div style="color: var(--text-secondary); font-size: 14px;">
                        <span style="margin-left: 16px;">🎨 {item['color']}</span>
                        <span style="margin-left: 16px;">📐 {item['size']}</span>
                        <span style="margin-left: 16px;">💵 {item['price']:,.0f} د.ع</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # نموذج الإضافة
                c_qty, c_price, c_btn = st.columns([1, 1, 2])
                with c_qty:
                    st.number_input("العدد", 1, int(item['stock']), 1, key="pos_qty")
                with c_price:
                    custom_price = st.number_input("سعر البيع", value=float(item['price']), key="pos_price")
                    # إظهار هامش الربح
                    margin = custom_price - float(item['cost'])
                    margin_pct = (margin / custom_price * 100) if custom_price > 0 else 0
                    color = "#10B981" if margin > 0 else "#EF4444"
                    st.caption(f"<span style='color:{color}'>هامش الربح: {margin:,.0f} ({margin_pct:.0f}%)</span>", unsafe_allow_html=True)
                with c_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.button(
                        "➕ إضافة للسلة", 
                        type="primary", 
                        use_container_width=True, 
                        on_click=add_to_cart_callback
                    )
        else:
            st.info("📭 لا توجد منتجات متوفرة في المخزون")

    # >> القسم الأيسر: السلة والدفع
    with col_cart:
        st.markdown("### 🧾 الفاتورة")
        
        total_bill = sum(item['total'] for item in st.session_state.cart)
        total_profit = sum((item['price'] - item['cost']) * item['qty'] for item in st.session_state.cart)
        
        # عرض الإجمالي
        st.markdown(f"""
        <div class="total-card">
            <div class="total-label">الإجمالي النهائي</div>
            <div class="total-value">{total_bill:,.0f} <span class="total-currency">د.ع</span></div>
            <div style="font-size: 12px; color: var(--success); margin-top: 4px;">
                ربح متوقع: {total_profit:,.0f} د.ع
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # عناصر السلة
        if not st.session_state.cart:
            st.markdown("""
            <div class="empty-cart">
                <div class="empty-cart-icon">🛒</div>
                <p>السلة فارغة</p>
                <p style="font-size: 12px;">اختر منتجاً للبدء</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for i, item in enumerate(st.session_state.cart):
                col_item, col_del = st.columns([5, 1])
                with col_item:
                    st.markdown(f"""
                    <div class="cart-item">
                        <div style="display: flex; justify-content: space-between;">
                            <strong>{item['name']}</strong>
                            <span style="color: var(--primary);">{item['total']:,.0f}</span>
                        </div>
                        <div style="color: var(--text-muted); font-size: 12px; margin-top: 4px;">
                            {item['color']} • {item['size']} • {item['qty']} × {item['price']:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    st.button("🗑️", key=f"del_{i}", on_click=remove_from_cart_callback, args=(i,), help="إزالة")

            st.divider()
            
            # معلومات العميل
            with st.expander("👤 معلومات العميل", expanded=True):
                df_cust = get_customers()
                customer_options = ["➕ عميل جديد"]
                if df_cust is not None and not df_cust.empty:
                    customer_options += df_cust['name'].tolist()
                
                st.selectbox("العميل", customer_options, key="c_select")
                
                if st.session_state.get('c_select') == "➕ عميل جديد":
                    st.text_input("الاسم *", key="c_name", placeholder="اسم العميل")
                    col_p, col_a = st.columns(2)
                    col_p.text_input("📞 الهاتف", key="c_phone", placeholder="07XX")
                    col_a.text_input("📍 العنوان", key="c_addr", placeholder="المنطقة/الحي")
                else:
                    if df_cust is not None and not df_cust.empty and st.session_state.get('c_select'):
                        curr = df_cust[df_cust['name'] == st.session_state.c_select]
                        if not curr.empty:
                            curr = curr.iloc[0]
                            st.markdown(f"""
                            <div style="background: var(--bg-elevated); padding: 12px; border-radius: 10px; font-size: 13px;">
                                <span>📞 {curr['phone'] or 'لا يوجد'}</span> &nbsp;|&nbsp; 
                                <span>📍 {curr['address'] or 'لا يوجد'}</span>
                            </div>
                            """, unsafe_allow_html=True)

                st.selectbox("⏱️ مدة التوصيل", ["24 ساعة", "48 ساعة", "فوري"], key="c_dur")
            
            # زر الدفع
            st.button(
                "✅ إتمام البيع وطباعة الفاتورة", 
                type="primary", 
                use_container_width=True, 
                on_click=checkout_callback
            )

        # نافذة الفاتورة بعد الدفع
        if 'last_inv' in st.session_state:
            st.success("✅ تم البيع بنجاح!")
            st.text_area("📋 نص الفاتورة (للنسخ)", st.session_state.last_inv, height=180)
            if st.button("🆕 بدء طلب جديد", use_container_width=True):
                del st.session_state.last_inv
                st.rerun()

# ==========================================
# صفحة 2: المخزون (عرض احترافي لمتجر ملابس)
# ==========================================
elif page == "📦 المخزون":
    st.markdown("## � مخزون المتجر")

    df = get_inventory()
    if df is not None and not df.empty:
        # مؤشرات الأداء السريعة
        df['total_cost_value'] = df['stock'] * df['cost']
        df['total_sale_potential'] = df['stock'] * df['price']

        c1, c2, c3, c4 = st.columns(4)
        total_items = df['stock'].sum()
        total_cost = df['total_cost_value'].sum()
        total_sales = df['total_sale_potential'].sum()
        low_stock = len(df[df['stock'] < 3])

        c1.metric("📦 إجمالي القطع", f"{total_items:,}")
        c2.metric("💰 رأس المال", f"{total_cost:,.0f}")
        c3.metric("📈 القيمة البيعية", f"{total_sales:,.0f}", delta=f"+{(total_sales-total_cost):,.0f} ربح")
        c4.metric("⚠️ نواقص", f"{low_stock} موديل", delta_color="inverse")

        st.divider()

        # خيارات العرض
        view_type = st.radio(
            "طريقة العرض:", 
            ["� عرض المتجر (موديل × لون × مقاس)", "�📊 ملخص سريع", "📝 تفاصيل للتعديل"], 
            horizontal=True
        )

        # ========================================
        # العرض الجديد: مصفوفة الملابس الاحترافية
        # ========================================
        if "عرض المتجر" in view_type:
            # دليل الألوان
            st.markdown("""
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-dot" style="background: rgba(16, 185, 129, 0.3);"></div>
                    <span>متوفر (3+)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background: rgba(245, 158, 11, 0.3);"></div>
                    <span>قليل (1-2)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background: rgba(239, 68, 68, 0.2);"></div>
                    <span>نفذ (0)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # فلتر البحث
            col_search, col_stock_filter = st.columns([2, 1])
            with col_search:
                search_model = st.text_input("� بحث عن موديل:", placeholder="اكتب اسم الموديل...", key="matrix_search")
            with col_stock_filter:
                show_filter = st.selectbox("عرض:", ["الكل", "متوفر فقط", "فيه نواقص"], key="matrix_filter")
            
            # تجميع البيانات حسب الموديل
            models = df['name'].unique()
            
            for model_name in sorted(models):
                # تطبيق فلتر البحث
                if search_model and search_model.lower() not in model_name.lower():
                    continue
                
                model_data = df[df['name'] == model_name]
                model_total = model_data['stock'].sum()
                model_has_low = (model_data['stock'] < 3).any()
                
                # تطبيق فلتر المخزون
                if show_filter == "متوفر فقط" and model_total == 0:
                    continue
                if show_filter == "فيه نواقص" and not model_has_low:
                    continue
                
                # بناء HTML للموديل
                colors_html = ""
                for color in model_data['color'].unique():
                    color_data = model_data[model_data['color'] == color]
                    
                    sizes_html = ""
                    for _, row in color_data.iterrows():
                        stock = int(row['stock'])
                        size = row['size']
                        
                        if stock >= 3:
                            status_class = "stock-good"
                        elif stock > 0:
                            status_class = "stock-low"
                        else:
                            status_class = "stock-out"
                        
                        sizes_html += f'<div class="size-chip {status_class}">{size}: {stock}</div>'
                    
                    # السعر لهذا اللون
                    price = color_data.iloc[0]['price']
                    
                    colors_html += f"""
                    <div class="color-block">
                        <div class="color-name">🎨 {color}</div>
                        <div class="sizes-row">{sizes_html}</div>
                        <div class="price-tag">💵 {price:,.0f} د.ع</div>
                    </div>
                    """
                
                # حالة المخزون الكلية للموديل
                if model_total == 0:
                    total_style = "background: rgba(239, 68, 68, 0.2); color: #EF4444;"
                    total_text = "نفذ ❌"
                elif model_has_low:
                    total_style = "background: rgba(245, 158, 11, 0.2); color: #F59E0B;"
                    total_text = f"{model_total} قطعة ⚠️"
                else:
                    total_style = "background: rgba(16, 185, 129, 0.15); color: #10B981;"
                    total_text = f"{model_total} قطعة ✓"
                
                st.markdown(f"""
                <div class="model-card">
                    <div class="model-header">
                        <span class="model-name">👗 {model_name}</span>
                        <span class="model-total" style="{total_style}">{total_text}</span>
                    </div>
                    <div class="colors-container">
                        {colors_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # زر التصدير
            st.divider()
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 تصدير المخزون كاملاً (CSV)",
                csv,
                "inventory_full.csv",
                "text/csv",
                use_container_width=False
            )

        # ========================================
        # العرض الملخص السريع
        # ========================================
        elif "ملخص" in view_type:
            grouped = df.groupby('name').agg({
                'stock': 'sum',
                'color': 'count',
                'total_sale_potential': 'sum'
            }).reset_index()
            
            grouped.columns = ['الموديل', 'الكمية', 'الألوان', 'القيمة']
            
            st.dataframe(
                grouped,
                use_container_width=True,
                column_config={
                    "الكمية": st.column_config.ProgressColumn(
                        "الكمية",
                        format="%d",
                        min_value=0,
                        max_value=int(grouped['الكمية'].max()) if not grouped.empty else 10
                    ),
                    "القيمة": st.column_config.NumberColumn("القيمة", format="%d د.ع")
                },
                hide_index=True
            )
        
        # ========================================
        # العرض التفصيلي للتعديل
        # ========================================
        else:
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search = st.text_input("🔍 بحث:", placeholder="اكتب للفلترة...")
            with col_filter:
                stock_filter = st.selectbox("📦 فلترة المخزون", ["الكل", "نواقص فقط", "متوفر فقط"])
            
            df_display = df.copy()
            if search:
                df_display = df_display[
                    df_display['name'].str.contains(search, case=False, na=False) | 
                    df_display['color'].str.contains(search, case=False, na=False)
                ]
            if stock_filter == "نواقص فقط":
                df_display = df_display[df_display['stock'] < 3]
            elif stock_filter == "متوفر فقط":
                df_display = df_display[df_display['stock'] >= 3]
            
            edited_df = st.data_editor(
                df_display,
                key="editor_inv",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": None, 
                    "total_cost_value": None, 
                    "total_sale_potential": None,
                    "name": st.column_config.TextColumn("الاسم"),
                    "color": st.column_config.TextColumn("اللون"),
                    "size": st.column_config.SelectboxColumn("القياس", options=["S", "M", "L", "XL", "XXL", "Free"]),
                    "stock": st.column_config.NumberColumn("العدد", min_value=0, format="%d 📦"),
                    "price": st.column_config.NumberColumn("البيع", format="%d د.ع"),
                    "cost": st.column_config.NumberColumn("التكلفة", format="%d د.ع"),
                }
            )
            
            col_save, col_export = st.columns([1, 1])
            with col_save:
                if st.button("💾 حفظ التعديلات", type="primary", use_container_width=True):
                    with st.spinner("جاري الحفظ..."):
                        changes = []
                        for _, row in edited_df.iterrows():
                            changes.append((
                                int(row['stock']), float(row['price']), float(row['cost']), 
                                row['size'], row['name'], row['color'], int(row['id'])
                            ))
                        
                        if changes:
                            conn = get_db_connection()
                            with conn.cursor() as cur:
                                cur.executemany(
                                    "UPDATE public.variants SET stock=%s, price=%s, cost=%s, size=%s, name=%s, color=%s WHERE id=%s", 
                                    changes
                                )
                                conn.commit()
                            clear_all_cache()
                            st.toast("✅ تم الحفظ بنجاح!", icon="✅")
                            time.sleep(0.5)
                            st.rerun()
            
            with col_export:
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📥 تصدير CSV",
                    csv,
                    "inventory.csv",
                    "text/csv",
                    use_container_width=True
                )

    else:
        st.info("📭 المخزون فارغ. أضف منتجات للبدء.")

    # إضافة صنف جديد
    with st.expander("➕ إضافة منتج جديد"):
        with st.form("new_item"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("الاسم *")
            co = c2.text_input("اللون *")
            sz = c3.selectbox("القياس", ["S", "M", "L", "XL", "XXL", "Free"])
            
            c4, c5, c6 = st.columns(3)
            s = c4.number_input("العدد", min_value=1, value=1)
            cs = c5.number_input("التكلفة", min_value=0.0, value=0.0)
            p = c6.number_input("سعر البيع", min_value=0.0, value=0.0)
            
            if st.form_submit_button("💾 حفظ المنتج", type="primary"):
                if n and co:
                    run_query(
                        "INSERT INTO public.variants (name, color, size, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)", 
                        (n, co, sz, s, cs, p), commit=True, fetch=False
                    )
                    clear_all_cache()
                    st.toast("✅ تمت الإضافة!", icon="✅")
                    st.rerun()
                else:
                    st.error("❌ الاسم واللون مطلوبان")

# ==========================================
# صفحة 3: التقارير (Dashboard)
# ==========================================
elif page == "📊 التقارير":
    st.markdown("## 📊 لوحة المعلومات")
    
    # فلتر الفترة
    col_filter, _ = st.columns([1, 3])
    with col_filter:
        period = st.selectbox("📅 الفترة", ["اليوم", "هذا الأسبوع", "هذا الشهر", "كل الوقت"])
    
    df_s = get_sales(1000)
    
    if df_s is not None and not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['date'])
        
        # تطبيق الفلتر
        today = pd.Timestamp.now().normalize()
        if period == "اليوم":
            df_filtered = df_s[df_s['date'] >= today]
        elif period == "هذا الأسبوع":
            week_start = today - timedelta(days=today.dayofweek)
            df_filtered = df_s[df_s['date'] >= week_start]
        elif period == "هذا الشهر":
            month_start = today.replace(day=1)
            df_filtered = df_s[df_s['date'] >= month_start]
        else:
            df_filtered = df_s
        
        # المقاييس
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💵 المبيعات", f"{df_filtered['total'].sum():,.0f}")
        m2.metric("📦 الطلبات", f"{len(df_filtered['invoice_id'].unique())}")
        m3.metric("📈 الأرباح", f"{df_filtered['profit'].sum():,.0f}")
        avg_basket = df_filtered.groupby('invoice_id')['total'].sum().mean() if not df_filtered.empty else 0
        m4.metric("🛒 متوسط السلة", f"{avg_basket:,.0f}")
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📈 النمو اليومي")
            if not df_filtered.empty:
                daily_trend = df_filtered.groupby(df_filtered['date'].dt.date)['total'].sum()
                st.line_chart(daily_trend, color="#D48896", height=300)
            else:
                st.info("لا توجد بيانات لهذه الفترة")
        
        with c2:
            st.markdown("#### 🏆 الأكثر مبيعاً")
            if not df_filtered.empty:
                top = df_filtered.groupby('product_name')['qty'].sum().nlargest(5)
                st.bar_chart(top, color="#D48896", height=300)
            else:
                st.info("لا توجد بيانات لهذه الفترة")
        
        # ملخص إضافي
        st.divider()
        st.markdown("#### 📋 آخر المبيعات")
        recent = df_filtered.head(10)[['date', 'product_name', 'qty', 'total', 'profit']]
        recent.columns = ['التاريخ', 'المنتج', 'الكمية', 'المبلغ', 'الربح']
        st.dataframe(recent, use_container_width=True, hide_index=True)
        
    else:
        st.info("📭 لا توجد مبيعات بعد")

# ==========================================
# صفحة 4: العملاء
# ==========================================
elif page == "👥 العملاء":
    st.markdown("## 👥 دليل العملاء")
    
    df_cust = get_customers()
    
    if df_cust is not None and not df_cust.empty:
        # بحث
        search = st.text_input("🔍 بحث عن عميل:", placeholder="اكتب الاسم أو الهاتف...")
        
        df_display = df_cust
        if search:
            df_display = df_cust[
                df_cust['name'].str.contains(search, case=False, na=False) |
                df_cust['phone'].str.contains(search, case=False, na=False)
            ]
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "username": None,
                "name": st.column_config.TextColumn("الاسم"),
                "phone": st.column_config.TextColumn("📞 الهاتف"),
                "address": st.column_config.TextColumn("📍 العنوان"),
            }
        )
        
        st.caption(f"إجمالي العملاء: {len(df_cust)}")
    else:
        st.info("📭 لا يوجد عملاء مسجلين بعد")

# ==========================================
# صفحة 5: المصاريف
# ==========================================
elif page == "💸 المصاريف":
    st.markdown("## 💸 إدارة المصاريف")
    
    col_form, col_summary = st.columns([1, 1])
    
    with col_form:
        st.markdown("#### ➕ تسجيل مصروف جديد")
        with st.form("exp_form"):
            amt = st.number_input("💵 المبلغ", min_value=0.0)
            category = st.selectbox("📁 التصنيف", ["عام", "رواتب", "إيجار", "فواتير", "مشتريات", "نقل", "أخرى"])
            rsn = st.text_input("📝 السبب/الوصف")
            
            if st.form_submit_button("✅ تسجيل", type="primary", use_container_width=True):
                if amt > 0:
                    run_query(
                        "INSERT INTO public.expenses (amount, reason, category, date) VALUES (%s, %s, %s, %s)", 
                        (amt, rsn, category, get_time()), commit=True, fetch=False
                    )
                    st.toast("✅ تم تسجيل المصروف", icon="✅")
                    st.rerun()
                else:
                    st.error("❌ أدخل مبلغاً صحيحاً")
    
    with col_summary:
        st.markdown("#### 📊 ملخص المصاريف")
        df_exp = get_expenses()
        
        if df_exp is not None and not df_exp.empty:
            df_exp['date'] = pd.to_datetime(df_exp['date'])
            today = pd.Timestamp.now().normalize()
            month_start = today.replace(day=1)
            
            monthly = df_exp[df_exp['date'] >= month_start]['amount'].sum()
            total = df_exp['amount'].sum()
            
            st.metric("هذا الشهر", f"{monthly:,.0f} د.ع")
            st.metric("الإجمالي الكلي", f"{total:,.0f} د.ع")
        else:
            st.info("لا توجد مصاريف مسجلة")
    
    # سجل المصاريف
    st.divider()
    st.markdown("#### 📜 سجل المصاريف")
    df_exp = get_expenses()
    if df_exp is not None and not df_exp.empty:
        st.dataframe(
            df_exp.head(20),
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "amount": st.column_config.NumberColumn("المبلغ", format="%d د.ع"),
                "reason": st.column_config.TextColumn("السبب"),
                "category": st.column_config.TextColumn("التصنيف"),
                "date": st.column_config.DatetimeColumn("التاريخ", format="D MMM YYYY - h:mm a"),
            }
        )
    else:
        st.info("📭 لا توجد مصاريف مسجلة")

# ==========================================
# صفحة 6: السجل والرواجع
# ==========================================
elif page == "📜 السجل":
    st.markdown("## 📜 سجل العمليات")
    
    df_sales_log = get_sales(100)
    
    if df_sales_log is not None and not df_sales_log.empty:
        st.dataframe(
            df_sales_log,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("رقم"),
                "product_name": st.column_config.TextColumn("المنتج"),
                "qty": st.column_config.NumberColumn("الكمية"),
                "total": st.column_config.NumberColumn("المبلغ", format="%d د.ع"),
                "profit": st.column_config.NumberColumn("الربح", format="%d د.ع"),
                "date": st.column_config.DatetimeColumn("التاريخ", format="D MMM - h:mm a"),
                "invoice_id": st.column_config.TextColumn("الفاتورة"),
                "delivery_duration": st.column_config.TextColumn("التوصيل"),
                "customer_id": None,
                "variant_id": None,
            }
        )
    else:
        st.info("📭 لا توجد عمليات مسجلة")
    
    st.divider()
    st.markdown("### ↩️ إرجاع منتج")
    
    with st.form("return_form"):
        ret_id = st.number_input("أدخل رقم العملية (ID) للإرجاع:", min_value=1, step=1)
        submitted = st.form_submit_button("🔍 بحث عن العملية")
        
        if submitted and df_sales_log is not None:
            sale_rec = df_sales_log[df_sales_log['id'] == ret_id]
            if not sale_rec.empty:
                r = sale_rec.iloc[0]
                st.session_state.return_sale = r.to_dict()
                st.session_state.show_return_confirm = True
            else:
                st.error("❌ رقم العملية غير صحيح")
    
    # تأكيد الإرجاع (خارج الفورم لتجنب مشكلة الأزرار المتداخلة)
    if st.session_state.get('show_return_confirm') and st.session_state.get('return_sale'):
        r = st.session_state.return_sale
        st.warning(f"⚠️ هل أنت متأكد من إرجاع: **{r['product_name']}** (العدد: {r['qty']})؟")
        
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ تأكيد الإرجاع", type="primary", use_container_width=True):
                with st.spinner("جاري المعالجة..."):
                    # إرجاع للمخزن
                    run_query(
                        "UPDATE public.variants SET stock = stock + %s WHERE id = %s", 
                        (int(r['qty']), int(r['variant_id'])), commit=True, fetch=False
                    )
                    # تسجيل المرتجع
                    run_query(
                        "INSERT INTO public.returns (sale_id, product_name, qty, return_amount, return_date, status) VALUES (%s,%s,%s,%s,%s,%s)",
                        (int(r['id']), r['product_name'], int(r['qty']), float(r['total']), get_time(), 'Returned'), 
                        commit=True, fetch=False
                    )
                    # تسجيل كمصروف
                    run_query(
                        "INSERT INTO public.expenses (amount, reason, category, date) VALUES (%s, %s, %s, %s)", 
                        (float(r['total']), f"مرتجع فاتورة #{r['id']}", "مرتجعات", get_time()), 
                        commit=True, fetch=False
                    )
                    
                    clear_all_cache()
                    del st.session_state.show_return_confirm
                    del st.session_state.return_sale
                    st.success("✅ تمت عملية الإرجاع بنجاح")
                    time.sleep(1)
                    st.rerun()
        
        with col_no:
            if st.button("❌ إلغاء", use_container_width=True):
                del st.session_state.show_return_confirm
                del st.session_state.return_sale
                st.rerun()
