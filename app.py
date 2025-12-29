import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import execute_values
import time
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(
    page_title="Nawaem Enterprise POS", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# --- 2. PROFESSIONAL UI/UX STYLING ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
        
        :root {
            --primary-color: #D48896; /* Dusty Rose */
            --bg-dark: #0E1117;
            --card-bg: #1A1C24;
            --text-light: #F0F2F6;
            --border-color: #2D303E;
        }

        /* Global Font & Direction */
        * { font-family: 'Cairo', sans-serif !important; direction: rtl; }
        
        /* App Background */
        .stApp { background-color: var(--bg-dark); }
        
        /* Custom Cards */
        .css-1r6slb0, .stContainer {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
        }

        /* Sidebar Polish */
        section[data-testid="stSidebar"] {
            background-color: #12141C;
            border-left: 1px solid var(--border-color);
        }

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #262933 !important;
            border: 1px solid #3F4354 !important;
            color: white !important;
            border-radius: 6px !important;
        }
        
        /* Metrics */
        div[data-testid="stMetric"] {
            background-color: #262933;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #3F4354;
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            border-color: var(--primary-color);
            transform: translateY(-2px);
        }
        div[data-testid="stMetricLabel"] { font-size: 14px; color: #888; }
        div[data-testid="stMetricValue"] { color: var(--primary-color) !important; font-weight: 700; }

        /* Dataframes */
        div[data-testid="stDataFrame"] { border: none; }
        
        /* Receipt Style for POS */
        .receipt-container {
            background-color: #fff;
            color: #000;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', Courier, monospace !important;
            border-top: 5px solid var(--primary-color);
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 3. BACKEND: CONNECTION & CACHING ---

@st.cache_resource
def get_db_connection():
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        st.stop()

def run_query(query, params=None, fetch=True, commit=False):
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
        st.toast(f"Error: {e}", icon="⚠️")
        return None

def init_db():
    conn = get_db_connection()
    with conn.cursor() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, 
            cost REAL, price REAL, stock INTEGER
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

# --- 4. OPTIMIZED CACHING LAYER ---

@st.cache_data(ttl=60)
def get_inventory(): return run_query("SELECT * FROM public.variants ORDER BY name")

@st.cache_data(ttl=300)
def get_customers(): return run_query("SELECT * FROM public.customers ORDER BY name")

@st.cache_data(ttl=60)
def get_sales(limit=2000): return run_query(f"SELECT * FROM public.sales ORDER BY date DESC LIMIT {limit}")

def clear_cache():
    get_inventory.clear()
    get_customers.clear()
    get_sales.clear()

def get_time(): return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- 5. LOGIC & CALLBACKS ---

if 'cart' not in st.session_state: st.session_state.cart = []
if 'db_inited' not in st.session_state: init_db(); st.session_state.db_inited = True

def add_to_cart_callback():
    sel = st.session_state.get('pos_selection')
    if not sel: return
    try:
        df = get_inventory()
        # Parse: "Name | Color (Size)"
        p_name = sel.split(" | ")[0]
        p_color = sel.split(" | ")[1].split(" (")[0]
        item = df[(df['name'] == p_name) & (df['color'] == p_color)].iloc[0]
        
        qty = st.session_state.get('pos_qty', 1)
        price = st.session_state.get('pos_price', item['price'])
        
        st.session_state.cart.append({
            "id": int(item['id']), "name": item['name'], "color": item['color'],
            "size": item['size'], "price": price, "qty": qty, "cost": float(item['cost']),
            "total": price * qty
        })
        st.toast(f"Added: {item['name']}", icon="🛍️")
    except: st.error("Error adding item")

def remove_item(idx): st.session_state.cart.pop(idx)

def process_checkout():
    if not st.session_state.cart: return
    
    c_name = st.session_state.get('c_name_input')
    c_select = st.session_state.get('c_selector')
    
    if c_select == "➕ عميل جديد" and not c_name:
        st.toast("⚠️ اسم العميل مطلوب", icon="❗")
        return

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Customer
            if c_select == "➕ عميل جديد":
                cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s, %s, %s, %s) RETURNING id", 
                           (c_name, st.session_state.c_phone, st.session_state.c_addr, c_name))
                cust_id = cur.fetchone()[0]
                cust_display = c_name
            else:
                df_c = get_customers()
                cust_row = df_c[df_c['name'] == c_select].iloc[0]
                cust_id = int(cust_row['id'])
                cust_display = cust_row['name']

            # 2. Sales Batch
            inv_id = get_time().strftime("%Y%m%d%H%M")
            sales_data = []
            for it in st.session_state.cart:
                cur.execute("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (it['qty'], it['id']))
                profit = (it['price'] - it['cost']) * it['qty']
                sales_data.append((cust_id, it['id'], it['name'], it['qty'], it['total'], profit, get_time(), inv_id, st.session_state.c_dur))

            execute_values(cur, """INSERT INTO public.sales 
                (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                VALUES %s""", sales_data)
            
            conn.commit()
            
            # 3. Receipt Generation
            rec = f"""
            Nawaem Boutique | نواعم بوتيك
            --------------------------------
            فاتورة: {inv_id}
            التاريخ: {get_time().strftime('%Y-%m-%d %H:%M')}
            العميل: {cust_display}
            --------------------------------
            """
            for x in st.session_state.cart:
                rec += f"{x['name']} ({x['size']})\n"
                rec += f"   {x['qty']} x {x['price']:,.0f} = {x['total']:,.0f}\n"
            rec += "--------------------------------\n"
            rec += f"المجموع: {sum(x['total'] for x in st.session_state.cart):,.0f} د.ع"
            
            st.session_state.last_receipt = rec
            st.session_state.cart = []
            clear_cache()
            
    except Exception as e:
        conn.rollback()
        st.error(f"System Error: {e}")

# --- 6. NAVIGATION & LAYOUT ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3502/3502685.png", width=60)
    st.markdown("<h3 style='text-align: center; color: #D48896;'>Nawaem OS</h3>", unsafe_allow_html=True)
    
    selected_page = option_menu(
        menu_title=None,
        options=["Dashboard", "Point of Sale", "Inventory", "Customers", "Expenses"],
        icons=["speedometer2", "cart4", "box-seam", "people", "wallet2"],
        menu_icon="cast",
        default_index=1,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#D48896", "font-size": "16px"}, 
            "nav-link": {"font-size": "15px", "text-align": "right", "margin":"5px", "--hover-color": "#262933"},
            "nav-link-selected": {"background-color": "#D48896", "font-weight": "600"},
        }
    )
    st.divider()
    if st.button("🔄 Sync Data", use_container_width=True):
        clear_cache()
        st.rerun()

# =========================================================
# 📊 DASHBOARD (Business Intelligence)
# =========================================================
if selected_page == "Dashboard":
    st.title("📊 Business Overview")
    
    df_s = get_sales(2000)
    df_inv = get_inventory()
    
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['date'])
        
        # --- TOP LEVEL METRICS ---
        today = pd.Timestamp.now().normalize()
        sales_today = df_s[df_s['date'] >= today]
        sales_month = df_s[df_s['date'] >= today.replace(day=1)]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Today's Revenue", f"{sales_today['total'].sum():,.0f} IQD", f"{len(sales_today)} Orders")
        col2.metric("Monthly Revenue", f"{sales_month['total'].sum():,.0f} IQD")
        col3.metric("Total Net Profit", f"{sales_month['profit'].sum():,.0f} IQD")
        col4.metric("Inventory Value", f"{(df_inv['stock'] * df_inv['cost']).sum():,.0f} IQD")
        
        # --- CHARTS (Plotly) ---
        col_c1, col_c2 = st.columns([2, 1])
        
        with col_c1:
            st.subheader("📈 Revenue Trend (30 Days)")
            daily_sales = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
            fig = px.area(daily_sales, x='date', y='total', color_discrete_sequence=['#D48896'])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_c2:
            st.subheader("🏆 Top Products")
            top_prod = df_s.groupby('product_name')['qty'].sum().nlargest(5).reset_index()
            fig2 = px.pie(top_prod, values='qty', names='product_name', hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
            fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# 🛒 POINT OF SALE (Professional Interface)
# =========================================================
elif selected_page == "Point of Sale":
    c_left, c_right = st.columns([2, 1.2], gap="medium")
    
    # --- PRODUCT GRID ---
    with c_left:
        st.subheader("🛍️ Product Selection")
        df = get_inventory()
        if not df.empty:
            df_active = df[df['stock'] > 0].copy()
            df_active['display'] = df_active['name'] + " | " + df_active['color'] + " (" + df_active['size'] + ")"
            
            # Styled Selectbox
            sel = st.selectbox("Search Product...", df_active['display'].tolist(), index=None, key="pos_selection", placeholder="Type name or color code...")
            
            if sel:
                item = df_active[df_active['display'] == sel].iloc[0]
                with st.container():
                    i1, i2, i3 = st.columns(3)
                    i1.metric("Stock", item['stock'])
                    i2.metric("Price", f"{item['price']:,.0f}")
                    i3.metric("Size", item['size'])
                    
                    st.divider()
                    
                    f1, f2, f3 = st.columns([1, 1, 2])
                    f1.number_input("Qty", 1, int(item['stock']), 1, key="pos_qty")
                    f2.number_input("Unit Price", value=float(item['price']), key="pos_price")
                    f3.markdown("<br>", unsafe_allow_html=True)
                    f3.button("🛒 Add Item", type="primary", use_container_width=True, on_click=add_to_cart_callback)

    # --- DIGITAL RECEIPT ---
    with c_right:
        st.subheader("🧾 Current Order")
        
        # Receipt Visual Container
        st.markdown('<div class="receipt-container">', unsafe_allow_html=True)
        if not st.session_state.cart:
            st.markdown("<p style='text-align:center; color:#888; padding:20px;'>Empty Cart</p>", unsafe_allow_html=True)
        else:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"<div style='color:black; font-family:monospace; font-weight:bold'>{item['name']}</div><div style='color:#555; font-size:12px'>{item['qty']} x {item['price']:,.0f} = {item['total']:,.0f}</div>", unsafe_allow_html=True)
                c2.button("🗑️", key=f"rm_{i}", on_click=remove_item, args=(i,))
                total += item['total']
                st.markdown("<hr style='margin:5px 0; border-top:1px dashed #ccc;'>", unsafe_allow_html=True)
            
            st.markdown(f"<h3 style='color:black; text-align:center; margin-top:10px;'>Total: {total:,.0f} IQD</h3>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Checkout Form
        with st.container():
            st.markdown("##### 👤 Customer Details")
            df_c = get_customers()
            st.selectbox("Select Customer", ["➕ عميل جديد"] + df_c['name'].tolist(), key="c_selector")
            
            if st.session_state.c_selector == "➕ عميل جديد":
                c1, c2 = st.columns(2)
                c1.text_input("Full Name", key="c_name_input")
                c2.text_input("Phone", key="c_phone")
                st.text_input("Address", key="c_addr")
            
            st.select_slider("Delivery Speed", options=["Immediate", "24 Hours", "48 Hours"], key="c_dur")
            
            if st.button("✅ COMPLETE ORDER", type="primary", use_container_width=True, on_click=process_checkout):
                pass

        # Print Modal
        if 'last_receipt' in st.session_state:
            st.success("Transaction Complete!")
            st.code(st.session_state.last_receipt, language="text")
            if st.button("New Order"):
                del st.session_state.last_receipt
                st.rerun()

# =========================================================
# 📦 INVENTORY (Ag-Grid Style)
# =========================================================
elif selected_page == "Inventory":
    st.title("📦 Inventory Management")
    
    # KPIs Row
    df = get_inventory()
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Items", int(df['stock'].sum()), border=True)
        c2.metric("Total Cost (Capital)", f"{(df['stock']*df['cost']).sum():,.0f}", border=True)
        c3.metric("Potential Sales", f"{(df['stock']*df['price']).sum():,.0f}", border=True)

        st.markdown("### 📝 Master Data Editor")
        
        # Professional Search
        search = st.text_input("🔍 Filter Inventory", placeholder="Search by model name, color or size...")
        if search:
            df = df[df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)]

        # Advanced Data Editor
        edited_df = st.data_editor(
            df,
            key="pro_inv_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "id": None,
                "name": st.column_config.TextColumn("Model Name", width="medium", required=True),
                "color": st.column_config.TextColumn("Color", width="small"),
                "size": st.column_config.SelectboxColumn("Size", options=["S","M","L","XL","XXL","Free"], width="small"),
                "stock": st.column_config.ProgressColumn("Stock Level", format="%d", min_value=0, max_value=int(df['stock'].max())),
                "cost": st.column_config.NumberColumn("Cost Price", format="%.0f IQD"),
                "price": st.column_config.NumberColumn("Sale Price", format="%.0f IQD"),
            }
        )
        
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("💾 Save Changes", type="primary"):
            # Update Logic (Batched)
            conn = get_db_connection()
            changes = []
            new_items = []
            
            # Simple diff logic (optimized for simplicity here)
            # In production, check row state. Here we upsert everything for safety.
            with conn.cursor() as cur:
                # 1. Update existing
                for i, row in edited_df.iterrows():
                    if pd.notna(row['id']):
                        cur.execute("""UPDATE public.variants 
                            SET name=%s, color=%s, size=%s, stock=%s, cost=%s, price=%s 
                            WHERE id=%s""", 
                            (row['name'], row['color'], row['size'], row['stock'], row['cost'], row['price'], row['id']))
                    else:
                        # 2. Insert new rows added via the editor
                        if row['name']:
                            cur.execute("""INSERT INTO public.variants 
                                (name, color, size, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)""",
                                (row['name'], row['color'], row['size'], row['stock'], row['cost'], row['price']))
                conn.commit()
            
            clear_cache()
            st.toast("Inventory Synced Successfully", icon="✅")
            time.sleep(1)
            st.rerun()

# =========================================================
# 👥 CUSTOMERS & EXPENSES
# =========================================================
elif selected_page == "Customers":
    st.title("👥 Customer Database")
    st.dataframe(get_customers(), use_container_width=True, hide_index=True)

elif selected_page == "Expenses":
    st.title("💸 Expense Tracker")
    with st.form("new_exp"):
        c1, c2 = st.columns(2)
        amt = c1.number_input("Amount (IQD)", step=1000.0)
        rsn = c2.text_input("Reason / Category")
        if st.form_submit_button("Record Expense"):
            run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s, %s, %s)", 
                      (amt, rsn, get_time()), commit=True, fetch=False)
            st.success("Recorded!")
