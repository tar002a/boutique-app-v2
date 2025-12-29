import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(
    page_title="Nawaem System Pro", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# --- 2. CSS الإصلاح الجذري (RTL Fixed) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    /* 1. إجبار هيكل التطبيق أن يكون LTR لمنع اختفاء البار */
    .stApp {
        direction: ltr !important;
        font-family: 'Cairo', sans-serif !important;
    }

    /* 2. قلب النصوص والمحتوى فقط لليمين */
    [data-testid="stSidebarUserContent"], 
    .stMain .block-container {
        direction: rtl !important;
        text-align: right !important;
    }

    /* 3. محاذاة العناصر */
    p, h1, h2, h3, h4, h5, h6, span, div, label, .stMarkdown, .stButton {
        text-align: right !important;
    }

    /* 4. حقول الإدخال */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], textarea {
        direction: rtl !important;
        text-align: right !important;
        background-color: #2C2C2E !important;
        color: white !important;
        border-radius: 10px !important;
        border: 1px solid #444 !important;
    }

    /* 5. الجداول */
    div[data-testid="stDataFrame"] {
        direction: rtl !important;
    }

    /* 6. البطاقات */
    .product-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 16px;
        padding: 15px;
        text-align: right;
        direction: rtl;
        transition: transform 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .product-card:hover {
        border-color: #B76E79;
        transform: translateY(-5px);
    }
    
    .metric-card {
        background-color: #252526;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        text-align: center;
    }

    /* إخفاء القوائم */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. إدارة الحالة ---
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'page_inv' not in st.session_state: st.session_state.page_inv = 0
if 'page_cust' not in st.session_state: st.session_state.page_cust = 0

# --- 4. دوال قاعدة البيانات ---
@st.cache_resource
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

def run_query(query, params=None, fetch_df=False, commit=False):
    conn = None
    try:
        conn = init_connection()
        if fetch_df:
            return pd.read_sql(query, conn, params=params)
        else:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if commit:
                    conn.commit()
                    return True
                return cur.fetchall()
    except Exception as e:
        if conn: conn.rollback()
        st.toast(f"خطأ قاعدة بيانات: {e}", icon="❌")
        return None

def get_baghdad_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- 5. واجهات المستخدم (Tabs) ---

# === 1. نقطة البيع ===
def tab_pos():
    col_prod, col_cart = st.columns([3, 1.2])
    
    with col_prod:
        c1, c2 = st.columns([4, 1])
        search = c1.text_input("🔍 بحث سريع (اسم، لون، قياس)...", key="pos_s")
        c2.caption("Server Search Active 🟢")
        
        # بحث سريع (Server Side)
        if search:
            q = "SELECT * FROM public.variants WHERE stock > 0 AND (name ILIKE %s OR color ILIKE %s OR size ILIKE %s) LIMIT 21"
            p = (f"%{search}%", f"%{search}%", f"%{search}%")
        else:
            q = "SELECT * FROM public.variants WHERE stock > 0 ORDER BY id DESC LIMIT 21"
            p = None
            
        df = run_query(q, p, fetch_df=True)
        
        if not df.empty:
            cols = st.columns(3)
            for idx, row in df.iterrows():
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div class="product-card">
                        <div style="font-weight:bold; font-size:1.1em; color:white;">{row['name']}</div>
                        <div style="color:#aaa; font-size:0.9em;">{row['color']} | {row['size']}</div>
                        <div style="color:#B76E79; font-weight:800; font-size:1.2em;">{row['price']:,.0f}</div>
                        <div style="background:#333; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.8em; width:fit-content;">متبقي: {row['stock']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("🛒 أضف", key=f"add_{row['id']}", type="secondary"):
                        add_to_cart(row)
                    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
        else:
            st.info("لا توجد نتائج.")

    with col_cart:
        with st.container(border=True):
            st.markdown("### 🛒 السلة")
            if not st.session_state.cart:
                st.caption("فارغة")
            else:
                total = 0
                for pid, item in list(st.session_state.cart.items()):
                    line_total = item['price'] * item['qty']
                    total += line_total
                    c_txt, c_act = st.columns([3, 1])
                    with c_txt:
                        st.markdown(f"**{item['name']}**")
                        st.caption(f"{item['color']} | {item['size']}")
                        # تعديل الكمية
                        nq = st.number_input("العدد", 1, int(item['max']), int(item['qty']), key=f"q_{pid}", label_visibility="collapsed")
                        if nq != item['qty']:
                            st.session_state.cart[pid]['qty'] = nq
                            st.rerun()
                        st.markdown(f"<span style='color:#B76E79'>{line_total:,.0f}</span>", unsafe_allow_html=True)
                    with c_act:
                        if st.button("❌", key=f"d_{pid}"):
                            del st.session_state.cart[pid]
                            st.rerun()
                    st.divider()
                
                st.markdown(f"<h3 style='text-align:center; color:#B76E79'>{total:,.0f} د.ع</h3>", unsafe_allow_html=True)
                
                with st.form("checkout"):
                    name = st.text_input("العميل (مطلوب)")
                    phone = st.text_input("الهاتف")
                    addr = st.text_input("العنوان")
                    dur = st.selectbox("التوصيل", ["24 ساعة", "48 ساعة", "أسبوع"])
                    if st.form_submit_button("✅ تثبيت الطلب", type="primary"):
                        process_checkout(name, phone, addr, dur)

def add_to_cart(row):
    pid = row['id']
    if pid in st.session_state.cart:
        if st.session_state.cart[pid]['qty'] < row['stock']:
            st.session_state.cart[pid]['qty'] += 1
            st.toast("تمت الزيادة", icon="➕")
        else:
            st.toast("نفدت الكمية", icon="⚠️")
    else:
        st.session_state.cart[pid] = {
            'id': row['id'], 'name': row['name'], 'color': row['color'], 
            'size': row['size'], 'price': row['price'], 'max': row['stock'], 'qty': 1
        }
        st.toast("تمت الإضافة", icon="🛒")

def process_checkout(name, phone, addr, dur):
    if not name or not st.session_state.cart:
        st.error("الاسم والسلة مطلوبان")
        return
    try:
        conn = init_connection()
        with conn.cursor() as cur:
            # 1. العميل
            cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s,%s,%s,%s) RETURNING id", (name, phone, addr, name))
            cid = cur.fetchone()[0]
            # 2. الفاتورة
            now = get_baghdad_time()
            inv_id = now.strftime("%Y%m%d%H%M")
            # 3. العناصر
            for pid, item in st.session_state.cart.items():
                cur.execute("SELECT cost FROM public.variants WHERE id=%s", (pid,))
                cost = cur.fetchone()[0]
                profit = (item['price'] - cost) * item['qty']
                cur.execute("UPDATE public.variants SET stock=stock-%s WHERE id=%s", (item['qty'], pid))
                cur.execute("""INSERT INTO public.sales 
                    (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", 
                    (cid, pid, item['name'], item['qty'], item['price']*item['qty'], profit, now, inv_id, dur))
            conn.commit()
            st.session_state.cart = {}
            st.success("تم الطلب بنجاح! 🎉")
            st.balloons()
            time.sleep(1)
            st.rerun()
    except Exception as e:
        st.error(f"خطأ: {e}")

# === 2. سجل المبيعات (مع التعديل والحذف) ===
def tab_sales_log():
    st.header("📝 سجل المبيعات")
    # تحميل آخر 50 عملية فقط للسرعة
    df = run_query("""
        SELECT s.id, s.product_name, s.qty, s.total, s.date, c.name as customer, s.variant_id
        FROM public.sales s
        LEFT JOIN public.customers c ON s.customer_id = c.id
        ORDER BY s.id DESC LIMIT 50
    """, fetch_df=True)
    
    if not df.empty:
        for i, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                c1.markdown(f"**{row['product_name']}**")
                c1.caption(f"👤 {row['customer']} | 📅 {row['date'].strftime('%Y-%m-%d %H:%M')}")
                c2.markdown(f"العدد: {row['qty']}")
                c3.markdown(f"💰 {row['total']:,.0f}")
                
                # أزرار الإجراءات
                with c4:
                    if st.button("↩️ إرجاع", key=f"ret_{row['id']}"):
                        add_return(row)
                    if st.button("🗑️ حذف", key=f"del_sale_{row['id']}"):
                        delete_sale(row['id'], row['qty'], row['variant_id'])
    else:
        st.info("لا توجد مبيعات مسجلة")

def add_return(row):
    # إضافة لقائمة الرواجع
    try:
        run_query("""
            INSERT INTO public.returns (sale_id, variant_id, product_name, qty, return_amount, return_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
        """, (int(row['id']), int(row['variant_id']), row['product_name'], int(row['qty']), float(row['total']), get_baghdad_time()), commit=True)
        st.toast("تمت الإضافة للرواجع", icon="↩️")
    except Exception as e:
        st.error(f"خطأ: {e}")

def delete_sale(sid, qty, vid):
    # حذف وإرجاع المخزون
    try:
        conn = init_connection()
        with conn.cursor() as cur:
            cur.execute("UPDATE public.variants SET stock=stock+%s WHERE id=%s", (int(qty), int(vid)))
            cur.execute("DELETE FROM public.sales WHERE id=%s", (int(sid),))
        conn.commit()
        st.toast("تم الحذف وإرجاع المخزون", icon="🗑️")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"خطأ: {e}")

# === 3. الرواجع ===
def tab_returns():
    st.header("↩️ إدارة المرجوعات")
    df = run_query("SELECT * FROM public.returns WHERE status='Pending' ORDER BY id DESC", fetch_df=True)
    
    if not df.empty:
        for i, row in df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.markdown(f"**{row['product_name']}** (x{row['qty']})")
                c1.caption(f"استرجاع مبلغ: {row['return_amount']:,.0f} د.ع")
                
                if c2.button("📥 استلام للمخزن", key=f"rec_{row['id']}"):
                    process_return_receive(row)
    else:
        st.info("لا توجد رواجع معلقة")

def process_return_receive(row):
    try:
        conn = init_connection()
        with conn.cursor() as cur:
            # 1. إرجاع المخزون
            cur.execute("UPDATE public.variants SET stock=stock+%s WHERE id=%s", (int(row['qty']), int(row['variant_id'])))
            # 2. تحديث الحالة
            cur.execute("UPDATE public.returns SET status='Received' WHERE id=%s", (int(row['id']),))
            # 3. تسجيل مصروف (خروج كاش)
            cur.execute("INSERT INTO public.expenses (amount, reason, date) VALUES (%s, %s, %s)", 
                        (float(row['return_amount']), f"استرجاع فاتورة #{row['sale_id']}", get_baghdad_time()))
        conn.commit()
        st.success("تم الاستلام وإعادة للمخزون")
        st.rerun()
    except Exception as e:
        st.error(f"خطأ: {e}")

# === 4. العملاء (مع بحث سريع) ===
def tab_customers():
    st.header("👥 قاعدة بيانات العملاء")
    search = st.text_input("🔍 بحث عن عميل (اسم، هاتف)...")
    
    # Pagination Logic
    PAGE_SIZE = 10
    offset = st.session_state.page_cust * PAGE_SIZE
    
    if search:
        q = f"SELECT * FROM public.customers WHERE name ILIKE %s OR phone ILIKE %s LIMIT {PAGE_SIZE} OFFSET {offset}"
        p = (f"%{search}%", f"%{search}%")
    else:
        q = f"SELECT * FROM public.customers ORDER BY id DESC LIMIT {PAGE_SIZE} OFFSET {offset}"
        p = None
        
    df = run_query(q, p, fetch_df=True)
    
    if not df.empty:
        for i, row in df.iterrows():
            with st.container(border=True):
                st.markdown(f"**{row['name']}**")
                st.text(f"📞 {row['phone']} | 📍 {row['address']}")
    
    # Customer Pagination
    c1, c2 = st.columns(2)
    if c1.button("السابق", key="cp") and st.session_state.page_cust > 0:
        st.session_state.page_cust -= 1
        st.rerun()
    if c2.button("التالي", key="cn") and len(df) == PAGE_SIZE:
        st.session_state.page_cust += 1
        st.rerun()

# === 5. المخزن (سريع) ===
def tab_inventory():
    st.header("📦 المخزون")
    c1, c2 = st.columns([3, 1])
    search = c1.text_input("بحث مخزون...", key="inv_s")
    
    if c2.button("➕ صنف جديد"):
        add_product_dialog()
        
    PAGE_SIZE = 15
    offset = st.session_state.page_inv * PAGE_SIZE
    
    if search:
        q = f"SELECT * FROM public.variants WHERE name ILIKE %s ORDER BY id DESC LIMIT {PAGE_SIZE} OFFSET {offset}"
        df = run_query(q, (f"%{search}%",), fetch_df=True)
    else:
        q = f"SELECT * FROM public.variants ORDER BY id DESC LIMIT {PAGE_SIZE} OFFSET {offset}"
        df = run_query(q, fetch_df=True)
        
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    # Inv Pagination
    b1, b2 = st.columns(2)
    if b1.button("السابق ⬅️", key="ip") and st.session_state.page_inv > 0:
        st.session_state.page_inv -= 1
        st.rerun()
    if b2.button("التالي ➡️", key="in") and len(df) == PAGE_SIZE:
        st.session_state.page_inv += 1
        st.rerun()

@st.dialog("إضافة منتج")
def add_product_dialog():
    with st.form("new_p"):
        name = st.text_input("الاسم")
        c1, c2 = st.columns(2)
        col = c1.text_input("لون")
        siz = c2.text_input("قياس")
        c3, c4, c5 = st.columns(3)
        stk = c3.number_input("عدد", 1)
        prc = c4.number_input("بيع", 0.0)
        cst = c5.number_input("كلفة", 0.0)
        if st.form_submit_button("حفظ"):
            run_query("INSERT INTO public.variants (name,color,size,stock,price,cost) VALUES (%s,%s,%s,%s,%s,%s)", 
                      (name, col, siz, stk, prc, cst), commit=True)
            st.rerun()

# === 6. المصاريف ===
def tab_expenses():
    st.header("💸 المصاريف")
    with st.form("exp_f"):
        c1, c2 = st.columns([1, 3])
        amt = c1.number_input("المبلغ", step=1000.0)
        rsn = c2.text_input("السبب")
        if st.form_submit_button("تسجيل"):
            run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s,%s,%s)", 
                      (amt, rsn, get_baghdad_time()), commit=True)
            st.success("تم التسجيل")
            st.rerun()
            
    st.divider()
    st.caption("آخر 20 مصروف")
    df = run_query("SELECT * FROM public.expenses ORDER BY id DESC LIMIT 20", fetch_df=True)
    if not df.empty:
        st.dataframe(df, use_container_width=True)

# === 7. التقارير الذكية (Cached) ===
@st.cache_data(ttl=300)
def get_smart_reports():
    conn = init_connection()
    # 1. ملخص اليوم
    today = pd.read_sql("""
        SELECT 
            (SELECT COALESCE(SUM(total),0) FROM public.sales WHERE date >= CURRENT_DATE) as sales,
            (SELECT COALESCE(SUM(profit),0) FROM public.sales WHERE date >= CURRENT_DATE) as profit,
            (SELECT COALESCE(SUM(amount),0) FROM public.expenses WHERE date >= CURRENT_DATE) as expenses
    """, conn).iloc[0]
    
    # 2. أفضل المنتجات
    top_prods = pd.read_sql("""
        SELECT product_name, SUM(qty) as q, SUM(profit) as p 
        FROM public.sales GROUP BY product_name ORDER BY p DESC LIMIT 5
    """, conn)
    
    # 3. قيمة المخزون
    stock_val = pd.read_sql("SELECT SUM(stock * cost) as val FROM public.variants", conn).iloc[0]['val']
    
    return today, top_prods, stock_val

def tab_reports():
    st.header("📊 التقارير الذكية")
    today, top_prods, stock_val = get_smart_reports()
    
    # كروت الملخص
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("مبيعات اليوم", f"{today['sales']:,.0f}")
    c2.metric("صافي الربح", f"{today['profit'] - today['expenses']:,.0f}")
    c3.metric("مصاريف اليوم", f"{today['expenses']:,.0f}")
    c4.metric("قيمة المخزون (شراء)", f"{stock_val:,.0f}")
    
    st.divider()
    
    col_chart, col_data = st.columns(2)
    with col_chart:
        st.subheader("🏆 المنتجات الأكثر ربحاً")
        if not top_prods.empty:
            st.bar_chart(top_prods.set_index('product_name')['p'])
    
    with col_data:
        st.subheader("📋 تفاصيل")
        st.dataframe(top_prods, use_container_width=True)

# --- التشغيل الرئيسي ---
def main():
    with st.sidebar:
        st.title("نواعم بوتيك")
        st.image("https://cdn-icons-png.flaticon.com/512/3144/3144456.png", width=80)
        
        # القائمة الكاملة
        menu = st.radio("القائمة", [
            "🛒 نقطة البيع", 
            "📝 سجل المبيعات", 
            "↩️ الرواجع", 
            "👥 العملاء", 
            "📦 المخزن", 
            "💸 المصاريف", 
            "📊 التقارير"
        ])
        
        st.divider()
        if st.button("تحديث البيانات 🔄"):
            st.cache_data.clear()
            st.rerun()

    # التوجيه
    if menu == "🛒 نقطة البيع": tab_pos()
    elif menu == "📝 سجل المبيعات": tab_sales_log()
    elif menu == "↩️ الرواجع": tab_returns()
    elif menu == "👥 العملاء": tab_customers()
    elif menu == "📦 المخزن": tab_inventory()
    elif menu == "💸 المصاريف": tab_expenses()
    elif menu == "📊 التقارير": tab_reports()

if __name__ == "__main__":
    main()
