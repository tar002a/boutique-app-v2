import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import psycopg2
from psycopg2.extras import execute_values
import time
import plotly.express as px

# --- 1. إعدادات النظام ---
st.set_page_config(
    page_title="نظام نواعم الاحترافي", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# --- 2. التصميم الاحترافي (CSS + RTL) ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
        
        :root {
            --primary-color: #D48896; /* لون وردي غامق */
            --bg-dark: #0E1117;
            --card-bg: #1A1C24;
            --text-light: #F0F2F6;
            --border-color: #2D303E;
        }

        /* تعميم الخط والاتجاه */
        * { font-family: 'Cairo', sans-serif !important; direction: rtl; }
        
        /* خلفية التطبيق */
        .stApp { background-color: var(--bg-dark); }
        
        /* الكروت والحاويات */
        div.stContainer {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* القائمة الجانبية */
        section[data-testid="stSidebar"] {
            background-color: #12141C;
            border-left: 1px solid var(--border-color);
        }

        /* حقول الإدخال */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #262933 !important;
            border: 1px solid #3F4354 !important;
            color: white !important;
            border-radius: 8px !important;
        }
        
        /* البطاقات الإحصائية (Metrics) */
        div[data-testid="stMetric"] {
            background-color: #262933;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #3F4354;
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            border-color: var(--primary-color);
            transform: translateY(-5px);
        }
        div[data-testid="stMetricLabel"] { font-size: 14px; color: #aaa; }
        div[data-testid="stMetricValue"] { color: var(--primary-color) !important; font-weight: 800; }

        /* جداول البيانات */
        div[data-testid="stDataFrame"] { border: none; }
        
        /* تصميم الفاتورة الرقمية */
        .receipt-container {
            background-color: #fff;
            color: #000;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', Courier, monospace !important;
            border-top: 6px solid var(--primary-color);
            direction: rtl;
            text-align: right;
        }
        .receipt-header { text-align: center; margin-bottom: 10px; border-bottom: 2px dashed #000; padding-bottom: 10px; }
        .receipt-item { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; }
        .receipt-total { border-top: 2px dashed #000; margin-top: 10px; padding-top: 5px; font-weight: bold; font-size: 18px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- 3. الاتصال بقاعدة البيانات ---

@st.cache_resource
def get_db_connection():
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال: {e}")
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
        st.toast(f"حدث خطأ: {e}", icon="⚠️")
        return None

def init_db():
    conn = get_db_connection()
    with conn.cursor() as c:
        # إنشاء الجداول الأساسية
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

# --- 4. وظائف جلب البيانات (Caching) ---

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

# --- 5. المنطق البرمجي (Callbacks) ---

if 'cart' not in st.session_state: st.session_state.cart = []
if 'db_inited' not in st.session_state: init_db(); st.session_state.db_inited = True

def add_to_cart_callback():
    sel = st.session_state.get('pos_selection')
    if not sel: return
    try:
        df = get_inventory()
        # تحليل النص: "الاسم | اللون (القياس)"
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
        st.toast(f"تمت الإضافة: {item['name']}", icon="🛍️")
    except: st.error("خطأ في إضافة المنتج")

def remove_item(idx): st.session_state.cart.pop(idx)

def process_checkout():
    if not st.session_state.cart: return
    
    c_name = st.session_state.get('c_name_input')
    c_select = st.session_state.get('c_selector')
    
    if c_select == "➕ عميل جديد" and not c_name:
        st.toast("⚠️ يرجى إدخال اسم العميل", icon="❗")
        return

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. معالجة العميل
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

            # 2. إدخال المبيعات وتحديث المخزون
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
            
            # 3. إنشاء نص الفاتورة للطباعة
            total_val = sum(x['total'] for x in st.session_state.cart)
            rec = f"""
            بوتيك نواعم للأزياء
            --------------------------------
            رقم الفاتورة: {inv_id}
            التاريخ: {get_time().strftime('%Y-%m-%d %H:%M')}
            العميل: {cust_display}
            --------------------------------
            """
            for x in st.session_state.cart:
                rec += f"- {x['name']} ({x['size']})\n"
                rec += f"  {x['qty']} x {x['price']:,.0f} = {x['total']:,.0f}\n"
            rec += "--------------------------------\n"
            rec += f"الإجمالي النهائي: {total_val:,.0f} د.ع"
            
            st.session_state.last_receipt = rec
            st.session_state.cart = []
            clear_cache()
            
    except Exception as e:
        conn.rollback()
        st.error(f"خطأ في النظام: {e}")

# --- 6. القائمة الجانبية والصفحات ---

with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #D48896;'>نواعم سيستم</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # قائمة عربية مدمجة
    selected_page = st.radio(
        "القائمة الرئيسية",
        ["لوحة القيادة", "نقطة البيع (POS)", "إدارة المخزون", "قاعدة العملاء", "المصاريف"],
        index=1
    )
    
    st.markdown("---")
    if st.button("🔄 مزامنة البيانات", use_container_width=True):
        clear_cache()
        st.rerun()

# =========================================================
# 📊 لوحة القيادة (Dashboard)
# =========================================================
if selected_page == "لوحة القيادة":
    st.title("📊 نظرة عامة على النشاط")
    
    df_s = get_sales(2000)
    df_inv = get_inventory()
    
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['date'])
        
        # المقاييس العلوية
        today = pd.Timestamp.now().normalize()
        sales_today = df_s[df_s['date'] >= today]
        sales_month = df_s[df_s['date'] >= today.replace(day=1)]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("مبيعات اليوم", f"{sales_today['total'].sum():,.0f} د.ع", f"{len(sales_today)} طلب")
        col2.metric("إيراد الشهر الحالي", f"{sales_month['total'].sum():,.0f} د.ع")
        col3.metric("صافي الأرباح (الشهري)", f"{sales_month['profit'].sum():,.0f} د.ع")
        col4.metric("قيمة بضاعة المخزن", f"{(df_inv['stock'] * df_inv['cost']).sum():,.0f} د.ع")
        
        # الرسوم البيانية
        col_c1, col_c2 = st.columns([2, 1])
        
        with col_c1:
            st.subheader("📈 منحنى المبيعات (30 يوم)")
            daily_sales = df_s.groupby(df_s['date'].dt.date)['total'].sum().reset_index()
            # استخدام Plotly للرسم
            fig = px.area(daily_sales, x='date', y='total', labels={'date':'التاريخ', 'total':'المبيعات'}, color_discrete_sequence=['#D48896'])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)
            
        with col_c2:
            st.subheader("🏆 المنتجات الأكثر طلباً")
            top_prod = df_s.groupby('product_name')['qty'].sum().nlargest(5).reset_index()
            fig2 = px.pie(top_prod, values='qty', names='product_name', hole=0.6, color_discrete_sequence=px.colors.sequential.RdBu)
            fig2.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

# =========================================================
# 🛒 نقطة البيع (POS)
# =========================================================
elif selected_page == "نقطة البيع (POS)":
    c_left, c_right = st.columns([2, 1.2], gap="medium")
    
    # --- قسم اختيار المنتجات ---
    with c_left:
        st.subheader("🛍️ قائمة المنتجات")
        df = get_inventory()
        if not df.empty:
            df_active = df[df['stock'] > 0].copy()
            df_active['display'] = df_active['name'] + " | " + df_active['color'] + " (" + df_active['size'] + ")"
            
            # بحث وتحديد
            sel = st.selectbox("بحث عن منتج...", df_active['display'].tolist(), index=None, key="pos_selection", placeholder="اكتب الاسم أو اللون...")
            
            if sel:
                item = df_active[df_active['display'] == sel].iloc[0]
                with st.container():
                    # بطاقة تفاصيل المنتج
                    i1, i2, i3 = st.columns(3)
                    i1.metric("المتوفر", item['stock'])
                    i2.metric("السعر", f"{item['price']:,.0f}")
                    i3.metric("القياس", item['size'])
                    
                    st.divider()
                    
                    # نموذج الإضافة للسلة
                    f1, f2, f3 = st.columns([1, 1, 2])
                    f1.number_input("العدد", 1, int(item['stock']), 1, key="pos_qty")
                    f2.number_input("سعر البيع للقطعة", value=float(item['price']), key="pos_price")
                    f3.markdown("<br>", unsafe_allow_html=True)
                    f3.button("🛒 إضافة للسلة", type="primary", use_container_width=True, on_click=add_to_cart_callback)

    # --- الفاتورة الحالية والدفع ---
    with c_right:
        st.subheader("🧾 الطلب الحالي")
        
        # تصميم الفاتورة الحرارية
        st.markdown('<div class="receipt-container">', unsafe_allow_html=True)
        st.markdown('<div class="receipt-header">بوتيك نواعم<br>فاتورة مبدئية</div>', unsafe_allow_html=True)
        
        if not st.session_state.cart:
            st.markdown("<p style='text-align:center; color:#888;'>السلة فارغة</p>", unsafe_allow_html=True)
        else:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                # عرض كل عنصر في الفاتورة
                col_row1, col_row2 = st.columns([4, 1])
                with col_row1:
                    st.markdown(f"""
                    <div class="receipt-item">
                        <span>{item['name']} ({item['size']})</span>
                    </div>
                    <div style="font-size:12px; color:#555;">
                        {item['qty']} x {item['price']:,.0f} = {item['total']:,.0f}
                    </div>
                    """, unsafe_allow_html=True)
                with col_row2:
                    st.button("✖", key=f"rm_{i}", on_click=remove_item, args=(i,), help="حذف")
                
                total += item['total']
            
            st.markdown(f'<div class="receipt-total">الإجمالي: {total:,.0f} د.ع</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # نموذج إتمام البيع
        with st.container():
            st.markdown("##### 👤 بيانات العميل")
            df_c = get_customers()
            st.selectbox("اختر العميل", ["➕ عميل جديد"] + df_c['name'].tolist(), key="c_selector")
            
            if st.session_state.c_selector == "➕ عميل جديد":
                c1, c2 = st.columns(2)
                c1.text_input("الاسم الكامل", key="c_name_input")
                c2.text_input("رقم الهاتف", key="c_phone")
                st.text_input("العنوان", key="c_addr")
            
            st.select_slider("موعد التوصيل", options=["فوري (استلام محل)", "خلال 24 ساعة", "خلال 48 ساعة"], key="c_dur")
            
            if st.button("✅ تأكيد البيع وطباعة", type="primary", use_container_width=True, on_click=process_checkout):
                pass

        # نافذة الطباعة بعد البيع
        if 'last_receipt' in st.session_state:
            st.success("تمت العملية بنجاح!")
            st.text_area("نص الفاتورة للنسخ", st.session_state.last_receipt, height=200)
            if st.button("بدء فاتورة جديدة"):
                del st.session_state.last_receipt
                st.rerun()

# =========================================================
# 📦 إدارة المخزون (Excel Grid)
# =========================================================
elif selected_page == "إدارة المخزون":
    st.title("📦 إدارة المخزون الشاملة")
    
    df = get_inventory()
    if not df.empty:
        # ملخص سريع
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي القطع", int(df['stock'].sum()), border=True)
        c2.metric("التكلفة الكلية (رأس المال)", f"{(df['stock']*df['cost']).sum():,.0f}", border=True)
        c3.metric("المبيعات المتوقعة", f"{(df['stock']*df['price']).sum():,.0f}", border=True)

        st.markdown("### 📝 تعديل بيانات المنتجات")
        
        # فلتر البحث
        search = st.text_input("🔍 تصفية الجدول", placeholder="ابحث باسم الموديل، اللون، أو القياس...")
        if search:
            df = df[df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)]

        # المحرر الذكي
        edited_df = st.data_editor(
            df,
            key="pro_inv_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "id": None, # إخفاء المعرف
                "name": st.column_config.TextColumn("اسم الموديل", width="medium", required=True),
                "color": st.column_config.TextColumn("اللون", width="small"),
                "size": st.column_config.SelectboxColumn("القياس", options=["S","M","L","XL","XXL","Free"], width="small"),
                "stock": st.column_config.ProgressColumn("مستوى المخزون", format="%d", min_value=0, max_value=int(df['stock'].max())),
                "cost": st.column_config.NumberColumn("سعر التكلفة", format="%.0f د.ع"),
                "price": st.column_config.NumberColumn("سعر البيع", format="%.0f د.ع"),
                # إخفاء الأعمدة المحسوبة إن وجدت
                "total_cost_value": None,
                "total_sale_potential": None
            }
        )
        
        # زر الحفظ
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("💾 حفظ التغييرات", type="primary"):
            conn = get_db_connection()
            with conn.cursor() as cur:
                for i, row in edited_df.iterrows():
                    # تحديث الصفوف الموجودة (التي لها ID)
                    if pd.notna(row['id']):
                        cur.execute("""UPDATE public.variants 
                            SET name=%s, color=%s, size=%s, stock=%s, cost=%s, price=%s 
                            WHERE id=%s""", 
                            (row['name'], row['color'], row['size'], row['stock'], row['cost'], row['price'], row['id']))
                    # إضافة الصفوف الجديدة (بدون ID)
                    else:
                        if row['name']: # شرط وجود اسم
                            cur.execute("""INSERT INTO public.variants 
                                (name, color, size, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)""",
                                (row['name'], row['color'], row['size'], row['stock'], row['cost'], row['price']))
                conn.commit()
            
            clear_cache()
            st.toast("تم تحديث المخزون بنجاح", icon="✅")
            time.sleep(1)
            st.rerun()

# =========================================================
# 👥 العملاء والمصاريف
# =========================================================
elif selected_page == "قاعدة العملاء":
    st.title("👥 قاعدة بيانات العملاء")
    st.dataframe(get_customers(), use_container_width=True, hide_index=True)

elif selected_page == "المصاريف":
    st.title("💸 سجل المصاريف اليومية")
    with st.form("new_exp"):
        c1, c2 = st.columns(2)
        amt = c1.number_input("المبلغ (د.ع)", step=1000.0)
        rsn = c2.text_input("سبب الصرف / التفاصيل")
        if st.form_submit_button("تسجيل المصروف"):
            run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s, %s, %s)", 
                      (amt, rsn, get_time()), commit=True, fetch=False)
            st.success("تم التسجيل!")
