import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import psycopg2
from psycopg2.extras import execute_values
import time

# --- 1. Page Configuration & Modern UI ---
st.set_page_config(
    page_title="Nawaem POS 🚀", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# Optimized Glassmorphism CSS with better responsiveness
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    :root {
        --primary: #D48896;
        --secondary: #2C2C2C;
        --bg-dark: #0E1117;
        --text-main: #FAFAFA;
    }

    * { font-family: 'Cairo', sans-serif !important; direction: rtl; }
    
    /* Global App Style */
    .stApp { background-color: var(--bg-dark); }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161a20;
        border-left: 1px solid #333;
    }

    /* Custom Cards */
    div.stContainer {
        background: rgba(30, 30, 30, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 15px;
    }

    /* Input Fields */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1E1E1E !important;
        border: 1px solid #444 !important;
        color: white !important;
        border-radius: 8px !important;
    }

    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 700;
        border: none;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(212, 136, 150, 0.3);
    }

    /* Data Editor */
    div[data-testid="stDataFrame"] { border: none; }
    
    /* Metrics */
    div[data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Database & Connection Management ---

@st.cache_resource
def get_db_connection():
    """Singleton connection pool wrapper"""
    return psycopg2.connect(**st.secrets["postgres"])

def run_query(query, params=None, fetch=True, commit=False):
    """Safe query execution wrapper"""
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
    except Exception as e:
        conn.rollback()
        st.error(f"Database Error: {e}")
        return None

def init_db():
    conn = get_db_connection()
    with conn.cursor() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS public.customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS public.sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TIMESTAMP, invoice_id TEXT, delivery_duration TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS public.expenses (
            id SERIAL PRIMARY KEY, amount REAL, reason TEXT, date TIMESTAMP
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS public.returns (
            id SERIAL PRIMARY KEY, sale_id INTEGER, variant_id INTEGER, customer_id INTEGER,
            product_name TEXT, product_details TEXT, qty INTEGER, return_amount REAL, 
            return_date TIMESTAMP, status TEXT
        )""")
        conn.commit()

# --- 3. Optimized Data Fetching (Caching) ---

@st.cache_data(ttl=60)
def get_inventory():
    return run_query("SELECT * FROM public.variants ORDER BY name")

@st.cache_data(ttl=300)
def get_customers():
    return run_query("SELECT * FROM public.customers ORDER BY name")

@st.cache_data(ttl=60)
def get_sales(limit=100):
    return run_query(f"SELECT * FROM public.sales ORDER BY date DESC LIMIT {limit}")

def clear_all_cache():
    get_inventory.clear()
    get_customers.clear()
    get_sales.clear()

def get_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- 4. Session State Management ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'db_inited' not in st.session_state:
    init_db()
    st.session_state.db_inited = True

# --- 5. LOGIC CONTROLLERS (Callbacks) ---
# Using callbacks makes the app 2x faster by avoiding full reruns for logic

def add_to_cart_callback():
    """Logic to add item to cart without blocking"""
    selection = st.session_state.get('pos_selection')
    if not selection: return
    
    # Identify product from string
    df = get_inventory()
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

def remove_from_cart_callback(idx):
    st.session_state.cart.pop(idx)

def checkout_callback():
    """Handles the checkout logic efficiently in one go"""
    if not st.session_state.cart:
        st.error("السلة فارغة")
        return

    cust_name = st.session_state.get('c_name')
    if not cust_name and st.session_state.get('c_select') == "عميل جديد":
        st.error("يجب إدخال اسم العميل")
        return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Handle Customer
            cust_id = None
            if st.session_state.c_select == "عميل جديد":
                cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s, %s, %s, %s) RETURNING id", 
                           (st.session_state.c_name, st.session_state.c_phone, st.session_state.c_addr, st.session_state.c_name))
                cust_id = cur.fetchone()[0]
                customer_display = st.session_state.c_name
                customer_addr = st.session_state.c_addr
            else:
                df_cust = get_customers()
                cust_data = df_cust[df_cust['name'] == st.session_state.c_select].iloc[0]
                cust_id = int(cust_data['id'])
                customer_display = cust_data['name']
                customer_addr = cust_data['address']

            # 2. Prepare Batch Data
            inv_id = get_time().strftime("%Y%m%d%H%M")
            sales_data = []
            
            for item in st.session_state.cart:
                # Update Stock (Directly)
                cur.execute("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
                
                # Prepare Sale Record
                profit = (item['price'] - item['cost']) * item['qty']
                sales_data.append((
                    cust_id, item['id'], item['name'], item['qty'], item['total'], 
                    profit, get_time(), inv_id, st.session_state.c_dur
                ))

            # 3. Batch Insert Sales
            execute_values(cur, """
                INSERT INTO public.sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                VALUES %s
            """, sales_data)

            conn.commit()
            
            # 4. Generate Invoice Text
            msg = f"🧾 فاتورة ({inv_id})\n👤 {customer_display}\n" + "-"*20 + "\n"
            total = 0
            for it in st.session_state.cart:
                msg += f"▫️ {it['name']} ({it['color']}) x{it['qty']} = {it['total']:,.0f}\n"
                total += it['total']
            msg += "-"*20 + f"\n💰 الإجمالي: {total:,.0f} د.ع\n📍 {customer_addr}"
            
            st.session_state.last_inv = msg
            st.session_state.cart = []
            clear_all_cache()
            
    except Exception as e:
        conn.rollback()
        st.error(f"فشلت العملية: {e}")

# --- 6. Main Layout ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3144/3144456.png", width=50) # Placeholder Icon
    st.markdown("### 🌸 نواعم بوتيك")
    page = st.radio("التنقل", ["🛒 نقطة البيع", "📦 المخزون", "📊 التقارير", "👥 العملاء", "📜 السجل", "💸 المصاريف"])
    
    st.markdown("---")
    if st.button("🔄 تحديث النظام", use_container_width=True):
        clear_all_cache()
        st.rerun()

# === PAGE: POS ===
if page == "🛒 نقطة البيع":
    col_pos, col_cart = st.columns([1.8, 1.2], gap="large")

    with col_pos:
        st.subheader("🔍 البحث والمنتجات")
        df_inv = get_inventory()
        
        if not df_inv.empty:
            df_active = df_inv[df_inv['stock'] > 0].copy()
            df_active['display'] = df_active['name'] + " | " + df_active['color'] + " (" + df_active['size'] + ")"
            
            # Smart Search Box
            selected_product = st.selectbox(
                "اختر المنتج:", 
                options=df_active['display'].tolist(), 
                index=None, 
                key="pos_selection",
                placeholder="اكتب اسم المنتج أو اللون..."
            )

            if selected_product:
                # Instant lookup from dataframe (RAM is faster than SQL)
                item = df_active[df_active['display'] == selected_product].iloc[0]
                
                with st.container():
                    c1, c2, c3 = st.columns(3)
                    c1.metric("المتوفر", f"{item['stock']} قطعة")
                    c2.metric("السعر الأساسي", f"{item['price']:,.0f}")
                    c3.metric("القياس", item['size'])
                
                # Add Form
                with st.container():
                    cc1, cc2 = st.columns(2)
                    cc1.number_input("الكمية", min_value=1, max_value=int(item['stock']), value=1, key="pos_qty")
                    cc2.number_input("سعر البيع (قابل للتعديل)", value=float(item['price']), key="pos_price")
                    
                    st.button("➕ إضافة للسلة", type="primary", use_container_width=True, on_click=add_to_cart_callback)

    with col_cart:
        st.subheader("🧾 الفاتورة")
        
        # Cart Visuals
        total_bill = sum(item['total'] for item in st.session_state.cart)
        
        with st.container():
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; background: rgba(212, 136, 150, 0.1); border-radius: 10px;">
                <span style="font-size: 14px; color: #888;">الإجمالي النهائي</span><br>
                <span style="font-size: 32px; font-weight: bold; color: #D48896;">{total_bill:,.0f} <span style="font-size:16px">د.ع</span></span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            if not st.session_state.cart:
                st.info("السلة فارغة حالياً")
            else:
                for i, item in enumerate(st.session_state.cart):
                    c_txt, c_del = st.columns([4, 1])
                    c_txt.markdown(f"**{item['name']}** ({item['qty']}) - <span style='color:#D48896'>{item['total']:,.0f}</span>", unsafe_allow_html=True)
                    c_txt.caption(f"{item['color']} | {item['size']}")
                    c_del.button("✖", key=f"del_{i}", on_click=remove_from_cart_callback, args=(i,))
                    st.divider()

            # Checkout Section
            with st.expander("👤 بيانات العميل والدفع", expanded=True if st.session_state.cart else False):
                df_cust = get_customers()
                cust_opts = ["عميل جديد"] + df_cust['name'].tolist()
                st.selectbox("العميل", cust_opts, key="c_select")
                
                if st.session_state.c_select == "عميل جديد":
                    st.text_input("الاسم", key="c_name")
                    st.text_input("الهاتف", key="c_phone")
                    st.text_input("العنوان", key="c_addr")
                else:
                    # Auto-fill visual (read-only for info)
                    curr_c = df_cust[df_cust['name'] == st.session_state.c_select].iloc[0]
                    st.caption(f"📞 {curr_c['phone']} | 📍 {curr_c['address']}")

                st.selectbox("التوصيل", ["24 ساعة", "48 ساعة", "فوري"], key="c_dur")
                
                if st.button("✅ إتمام البيع", type="primary", use_container_width=True, on_click=checkout_callback):
                    pass # Logic handled in callback

        # Invoice Result Modal
        if 'last_inv' in st.session_state:
            st.success("تمت العملية بنجاح!")
            st.text_area("نص الفاتورة (للنسخ)", st.session_state.last_inv, height=150)
            if st.button("إغلاق وبدء جديد"):
                del st.session_state.last_inv
                st.rerun()

# === PAGE: INVENTORY ===
elif page == "📦 المخزون":
    st.title("📦 إدارة المخزون")
    
    # Add Product
    with st.expander("➕ إضافة منتج جديد"):
        with st.form("new_inv"):
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            n = c1.text_input("الاسم")
            co = c2.text_input("اللون")
            sz = c3.text_input("القياس")
            stk = c4.number_input("العدد", 1)
            cost = c5.number_input("التكلفة", 0.0)
            pr = c6.number_input("البيع", 0.0)
            if st.form_submit_button("حفظ"):
                run_query("INSERT INTO public.variants (name, color, size, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)", 
                          (n, co, sz, stk, cost, pr), commit=True, fetch=False)
                clear_all_cache()
                st.rerun()

    # Edit Product (Excel Style)
    df = get_inventory()
    if not df.empty:
        edited_df = st.data_editor(
            df,
            column_config={
                "id": None,
                "name": "الاسم",
                "color": "اللون",
                "stock": st.column_config.NumberColumn("المخزون", min_value=0, required=True),
                "price": st.column_config.NumberColumn("السعر", format="%d IQD"),
            },
            use_container_width=True,
            num_rows="fixed",
            key="inv_editor"
        )
        
        if st.button("💾 حفظ التغييرات"):
            # Intelligent update logic
            changes = []
            for i, row in edited_df.iterrows():
                orig = df.iloc[i]
                # Compare critical fields
                if (row['stock'] != orig['stock']) or (row['price'] != orig['price']) or (row['cost'] != orig['cost']):
                    changes.append((int(row['stock']), float(row['price']), float(row['cost']), int(row['id'])))
            
            if changes:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    execute_values(cur, "UPDATE public.variants SET stock = data.stock, price = data.price, cost = data.cost FROM (VALUES %s) AS data (stock, price, cost, id) WHERE variants.id = data.id", changes)
                    conn.commit()
                clear_all_cache()
                st.success(f"تم تحديث {len(changes)} صف")
                time.sleep(1)
                st.rerun()

# === PAGE: DASHBOARD ===
elif page == "📊 التقارير":
    st.title("📊 لوحة القيادة")
    df_s = get_sales(1000)
    
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['date'])
        today = pd.Timestamp.now().normalize()
        daily = df_s[df_s['date'] >= today]
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("مبيعات اليوم", f"{daily['total'].sum():,.0f}")
        m2.metric("عدد الطلبات", len(daily))
        m3.metric("الأرباح", f"{daily['profit'].sum():,.0f}")
        m4.metric("متوسط الطلب", f"{daily['total'].mean() if not daily.empty else 0:,.0f}")
        
        st.markdown("---")
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.caption("اتجاه المبيعات (آخر 7 أيام)")
            trend = df_s.groupby(df_s['date'].dt.date)['total'].sum()
            st.line_chart(trend, color="#D48896")
        
        with c2:
            st.caption("أفضل المنتجات")
            top = df_s.groupby('product_name')['qty'].sum().nlargest(5)
            st.bar_chart(top, color="#2C2C2C")

# === PAGE: OTHER ===
elif page == "👥 العملاء":
    st.title("دليل العملاء")
    st.dataframe(get_customers(), use_container_width=True)

elif page == "💸 المصاريف":
    st.title("تسجيل المصاريف")
    with st.form("ex"):
        a = st.number_input("المبلغ")
        r = st.text_input("السبب")
        if st.form_submit_button("حفظ"):
            run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s,%s,%s)", (a, r, get_time()), commit=True, fetch=False)
            st.success("تم")

elif page == "📜 السجل":
    st.title("سجل العمليات")
    df = get_sales(100)
    st.dataframe(df, use_container_width=True)
    
    # Return Logic Helper
    st.markdown("### ↩️ إدارة الرواجع")
    sale_id = st.number_input("أدخل رقم العملية (ID) للإرجاع", min_value=1, step=1)
    if st.button("استرجاع بيانات العملية"):
        sale = df[df['id'] == sale_id]
        if not sale.empty:
            st.write(sale)
            if st.button("تأكيد الإرجاع للمخزن"):
                row = sale.iloc[0]
                run_query("UPDATE public.variants SET stock = stock + %s WHERE id = %s", (int(row['qty']), int(row['variant_id'])), commit=True, fetch=False)
                run_query("INSERT INTO public.returns (sale_id, product_name, qty, return_amount, return_date, status) VALUES (%s,%s,%s,%s,%s,%s)", 
                          (int(row['id']), row['product_name'], int(row['qty']), float(row['total']), get_time(), 'Returned'), commit=True, fetch=False)
                st.success("تم الإرجاع")
                clear_all_cache()
        else:
            st.error("غير موجود")
