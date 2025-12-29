import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
from difflib import SequenceMatcher
import time

# --- 1. إعداد الصفحة والتصميم (UI/UX) ---
st.set_page_config(
    page_title="Nawaem POS 🚀", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# ألوان وتصميم عصري (Glassmorphism)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    :root {
        --primary: #D48896; /* لون وردي غامق راقي */
        --bg-dark: #121212;
        --card-bg: #1E1E1E;
        --text-main: #E0E0E0;
        --success: #4CAF50;
    }

    /* تعميم الخط والاتجاه */
    * { font-family: 'Cairo', sans-serif !important; direction: rtl; }
    
    .stApp { background-color: var(--bg-dark); }

    /* تحسين القائمة الجانبية */
    section[data-testid="stSidebar"] {
        background-color: #181818;
        border-left: 1px solid #333;
    }
    
    /* الكروت */
    .metric-card {
        background: rgba(30, 30, 30, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: var(--primary); }
    
    .metric-value { font-size: 24px; font-weight: 800; color: var(--primary); }
    .metric-label { font-size: 14px; color: #888; margin-bottom: 5px; }

    /* الأزرار */
    .stButton button {
        border-radius: 12px;
        font-weight: 700;
        transition: all 0.3s ease;
    }
    .stButton button:hover { transform: scale(1.02); }
    
    /* الجداول */
    div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; border: 1px solid #333; }
    
    /* حقول الإدخال */
    div[data-baseweb="input"] { background-color: #252525; border-radius: 10px; border: none; }
</style>
""", unsafe_allow_html=True)

# --- 2. إدارة الاتصال وقاعدة البيانات (Backend Optimization) ---

@st.cache_resource
def init_connection():
    """اتصال واحد فقط يتم مشاركته (Singleton) لتقليل الضغط"""
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except Exception as e:
        st.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        st.stop()

conn = init_connection()

# تهيئة الجداول (مرة واحدة فقط عند التشغيل)
def init_db():
    with conn.cursor() as c:
        # إنشاء الجداول إذا لم تكن موجودة
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

# --- 3. دوال البيانات السريعة (Cached Data Functions) ---
# السرعة تأتي من هنا: لا نطلب البيانات من السيرفر إلا عند الضرورة

@st.cache_data(ttl=300)
def get_inventory_data():
    """جلب المخزون وتخزينه في الكاش لمدة 5 دقائق أو حتى التحديث"""
    try:
        return pd.read_sql("SELECT * FROM public.variants ORDER BY name", conn)
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_customers_data():
    try:
        return pd.read_sql("SELECT * FROM public.customers ORDER BY name", conn)
    except: return pd.DataFrame()

@st.cache_data(ttl=60) 
def get_sales_data(limit=100):
    try:
        return pd.read_sql(f"SELECT * FROM public.sales ORDER BY date DESC LIMIT {limit}", conn)
    except: return pd.DataFrame()

def clear_cache():
    """وظيفة لتنظيف الكاش عند إجراء تعديل لإجبار البرنامج على جلب بيانات جديدة"""
    get_inventory_data.clear()
    get_customers_data.clear()
    get_sales_data.clear()

def get_baghdad_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- 4. واجهة التطبيق (Modules) ---

# تهيئة الجلسة
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = 'pos'

# --- القائمة الجانبية (Navigation) ---
with st.sidebar:
    st.markdown("### 🌸 نواعم بوتيك")
    st.markdown("---")
    
    page = st.radio("القائمة الرئيسية", 
             ["🛒 نقطة البيع", "📦 إدارة المخزون", "👥 العملاء", "📝 السجل والرواجع", "📊 التقارير", "💸 المصاريف"],
             label_visibility="collapsed"
    )
    
    st.markdown("---")
    if st.button("🔄 تحديث البيانات", help="اضغط هنا إذا أجريت تعديلاً ولا يظهر"):
        clear_cache()
        st.toast("✅ تم تحديث البيانات بنجاح")
        time.sleep(0.5)
        st.rerun()

# --- الصفحة 1: نقطة البيع (POS) ---
if "نقطة البيع" in page:
    st.title("🛒 نقطة البيع السريع")
    
    col_products, col_cart = st.columns([2, 1.2]) # تقسيم الشاشة: منتجات (يسار) وسلة (يمين)

    # --- قسم المنتجات ---
    with col_products:
        df_inv = get_inventory_data()
        
        # فلتر ذكي سريع
        if not df_inv.empty:
            df_active = df_inv[df_inv['stock'] > 0].copy()
            df_active['display_name'] = df_active['name'] + " | " + df_active['color'] + " (" + df_active['size'] + ")"
            
            search_val = st.selectbox("🔍 ابحث عن منتج (اكتب الاسم أو اللون)", 
                                      options=df_active['display_name'].tolist(),
                                      index=None,
                                      placeholder="ابحث هنا...")
            
            if search_val:
                # العثور على المنتج المختار بسرعة
                selected_item = df_active[df_active['display_name'] == search_val].iloc[0]
                
                with st.form("add_to_cart_form", clear_on_submit=True):
                    st.markdown(f"**{selected_item['name']}** - {selected_item['color']}")
                    c1, c2, c3 = st.columns(3)
                    qty = c1.number_input("العدد", min_value=1, max_value=int(selected_item['stock']), value=1)
                    price = c2.number_input("سعر البيع", value=float(selected_item['price']))
                    c3.markdown(f"<br><span style='color:#888'>متوفر: {selected_item['stock']}</span>", unsafe_allow_html=True)
                    
                    if st.form_submit_button("🛒 إضافة للسلة", type="primary", use_container_width=True):
                        item = {
                            "id": int(selected_item['id']),
                            "name": selected_item['name'],
                            "color": selected_item['color'],
                            "size": selected_item['size'],
                            "price": price,
                            "qty": qty,
                            "cost": float(selected_item['cost']),
                            "total": price * qty
                        }
                        st.session_state.cart.append(item)
                        st.toast(f"تمت إضافة {selected_item['name']}", icon="✅")
                        st.rerun()

    # --- قسم السلة والدفع ---
    with col_cart:
        st.markdown("### 🧾 الفاتورة الحالية")
        with st.container(border=True):
            if not st.session_state.cart:
                st.info("السلة فارغة")
            else:
                total_bill = 0
                for idx, item in enumerate(st.session_state.cart):
                    c_nm, c_pr, c_del = st.columns([3, 2, 1])
                    c_nm.text(f"{item['name']} ({item['qty']})")
                    c_nm.caption(f"{item['color']} | {item['size']}")
                    c_pr.text(f"{item['total']:,.0f}")
                    if c_del.button("❌", key=f"del_{idx}"):
                        st.session_state.cart.pop(idx)
                        st.rerun()
                    total_bill += item['total']
                
                st.markdown("---")
                st.markdown(f"<h3 style='text-align: center; color: var(--primary);'>{total_bill:,.0f} د.ع</h3>", unsafe_allow_html=True)
                
                # إتمام البيع
                with st.expander("👤 بيانات العميل والدفع", expanded=True):
                    df_cust = get_customers_data()
                    cust_options = ["عميل جديد"] + df_cust['name'].tolist() if not df_cust.empty else ["عميل جديد"]
                    cust_selection = st.selectbox("اختر العميل", cust_options)
                    
                    cust_name, cust_phone, cust_addr = "", "", ""
                    
                    if cust_selection == "عميل جديد":
                        cust_name = st.text_input("الاسم")
                        cust_phone = st.text_input("الهاتف")
                        cust_addr = st.text_input("العنوان")
                    else:
                        cust_data = df_cust[df_cust['name'] == cust_selection].iloc[0]
                        cust_name = cust_data['name']
                        cust_phone = cust_data['phone']
                        cust_addr = cust_data['address']
                        st.caption(f"📍 {cust_addr} | 📞 {cust_phone}")

                    del_dur = st.selectbox("مدة التوصيل", ["24 ساعة", "48 ساعة", "3 أيام"], index=1)

                    if st.button("✅ تأكيد البيع وطباعة", type="primary", use_container_width=True):
                        if not st.session_state.cart:
                            st.warning("السلة فارغة!"); st.stop()
                        if not cust_name:
                            st.warning("اسم العميل مطلوب!"); st.stop()
                            
                        # تنفيذ البيع (DB Transaction)
                        try:
                            with conn.cursor() as cur:
                                # معالجة العميل
                                cust_id = None
                                if cust_selection == "عميل جديد":
                                    cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s, %s, %s, %s) RETURNING id", 
                                                (cust_name, cust_phone, cust_addr, cust_name))
                                    cust_id = cur.fetchone()[0]
                                else:
                                    cust_id = int(cust_data['id'])
                                
                                inv_id = get_baghdad_time().strftime("%Y%m%d%H%M")
                                
                                for item in st.session_state.cart:
                                    # تحديث المخزون
                                    cur.execute("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
                                    # تسجيل البيع
                                    profit = (item['price'] - item['cost']) * item['qty']
                                    cur.execute("""INSERT INTO public.sales 
                                        (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                        (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, get_baghdad_time(), inv_id, del_dur))
                                
                                conn.commit()
                                
                                # إعداد رسالة الفاتورة
                                msg = f"فاتورة طلبية ({inv_id})\nالعميل: {cust_name}\n"
                                for it in st.session_state.cart:
                                    msg += f"- {it['name']} ({it['color']}) x{it['qty']} = {it['total']:,.0f}\n"
                                msg += f"\nالإجمالي: {total_bill:,.0f} د.ع\nالعنوان: {cust_addr}"
                                
                                st.session_state.last_inv = msg
                                st.session_state.cart = []
                                clear_cache() # تحديث البيانات فوراً
                                st.toast("تمت عملية البيع بنجاح!", icon="🎉")
                                st.balloons()
                                st.rerun()
                                
                        except Exception as e:
                            conn.rollback()
                            st.error(f"حدث خطأ: {e}")

    if 'last_inv' in st.session_state:
        st.success("تم الحفظ! انسخ الفاتورة:")
        st.code(st.session_state.last_inv)
        if st.button("طلب جديد"):
            del st.session_state.last_inv
            st.rerun()

# --- الصفحة 2: إدارة المخزون (Excel Style) ---
elif "إدارة المخزون" in page:
    st.title("📦 المخزن (تعديل سريع)")
    
    # 1. إضافة صنف جديد
    with st.expander("➕ إضافة منتج جديد", expanded=False):
        with st.form("new_prod"):
            c1, c2, c3, c4 = st.columns(4)
            n = c1.text_input("الاسم")
            co = c2.text_input("اللون")
            sz = c3.text_input("القياس")
            stk = c4.number_input("العدد", 1)
            c5, c6 = st.columns(2)
            cost = c5.number_input("التكلفة", 0.0)
            price = c6.number_input("سعر البيع", 0.0)
            if st.form_submit_button("حفظ"):
                try:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO public.variants (name, color, size, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)",
                                    (n, co, sz, int(stk), float(cost), float(price)))
                        conn.commit()
                    clear_cache()
                    st.success("تمت الإضافة")
                except: st.error("خطأ")

    # 2. تعديل البيانات (Excel Style)
    st.markdown("### ✏️ تعديل الكميات والأسعار")
    df = get_inventory_data()
    
    if not df.empty:
        # Data Editor allows direct edits!
        edited_df = st.data_editor(
            df,
            column_config={
                "id": None, # Hide ID
                "name": "الاسم",
                "color": "اللون",
                "size": "القياس",
                "stock": st.column_config.NumberColumn("المخزون", min_value=0, required=True),
                "price": st.column_config.NumberColumn("سعر البيع", format="%d IQD"),
                "cost": st.column_config.NumberColumn("التكلفة", format="%d IQD"),
            },
            use_container_width=True,
            num_rows="fixed",
            key="inventory_editor"
        )
        
        if st.button("💾 حفظ التغييرات في الجدول", type="primary"):
            # هذا الجزء معقد قليلاً، لمعرفة ما تغير، لكن سنقوم بتحديث الكل للأمان والسرعة في التطوير
            # الأفضل هو مقارنة df بـ edited_df وتحديث المتغير فقط
            try:
                # تحويل إلى tuples للتحديث السريع
                data_to_update = []
                for i, row in edited_df.iterrows():
                    # نقارن مع البيانات الأصلية لتحديث المتغير فقط (Optimized)
                    orig_row = df.iloc[i]
                    if (row['stock'] != orig_row['stock']) or (row['price'] != orig_row['price']) or (row['cost'] != orig_row['cost']):
                        data_to_update.append((int(row['stock']), float(row['price']), float(row['cost']), int(row['id'])))
                
                if data_to_update:
                    with conn.cursor() as cur:
                        cur.executemany("UPDATE public.variants SET stock=%s, price=%s, cost=%s WHERE id=%s", data_to_update)
                        conn.commit()
                    clear_cache()
                    st.toast(f"تم تحديث {len(data_to_update)} منتج", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.info("لم تقم بتغيير أي شيء")
            except Exception as e:
                st.error(f"خطأ: {e}")

# --- الصفحة 3: التقارير (Dashboard) ---
elif "التقارير" in page:
    st.title("📊 لوحة المعلومات (Dashboard)")
    
    # جلب البيانات
    df_sales = get_sales_data(limit=1000)
    
    if not df_sales.empty:
        df_sales['date'] = pd.to_datetime(df_sales['date'])
        
        # فلتر اليوم
        today = pd.Timestamp.now().normalize()
        sales_today = df_sales[df_sales['date'] >= today]
        
        # إحصائيات سريعة
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown('<div class="metric-card"><div class="metric-label">مبيعات اليوم</div><div class="metric-value">{:,.0f}</div></div>'.format(sales_today['total'].sum()), unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="metric-card"><div class="metric-label">عدد الطلبات</div><div class="metric-value">{}</div></div>'.format(len(sales_today)), unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="metric-card"><div class="metric-label">أرباح اليوم</div><div class="metric-value">{:,.0f}</div></div>'.format(sales_today['profit'].sum()), unsafe_allow_html=True)
        with c4:
            avg = sales_today['total'].mean() if not sales_today.empty else 0
            st.markdown('<div class="metric-card"><div class="metric-label">متوسط السلة</div><div class="metric-value">{:,.0f}</div></div>'.format(avg), unsafe_allow_html=True)

        st.markdown("---")
        
        col_charts1, col_charts2 = st.columns(2)
        with col_charts1:
            st.subheader("📈 المبيعات بمرور الوقت")
            # تجميع حسب اليوم
            daily_sales = df_sales.groupby(df_sales['date'].dt.date)['total'].sum()
            st.line_chart(daily_sales, color="#D48896")
            
        with col_charts2:
            st.subheader("🏆 المنتجات الأكثر مبيعاً")
            top_products = df_sales.groupby('product_name')['qty'].sum().sort_values(ascending=False).head(5)
            st.bar_chart(top_products, color="#D48896")

    else:
        st.info("لا توجد بيانات مبيعات كافية")

# --- الصفحات الأخرى (بشكل مبسط وسريع) ---
elif "العملاء" in page:
    st.title("👥 قاعدة بيانات العملاء")
    df_c = get_customers_data()
    st.dataframe(df_c, use_container_width=True, hide_index=True)

elif "المصاريف" in page:
    st.title("💸 المصاريف")
    with st.form("exp"):
        amount = st.number_input("المبلغ", 0.0)
        reason = st.text_input("السبب")
        if st.form_submit_button("تسجيل"):
            with conn.cursor() as cur:
                cur.execute("INSERT INTO public.expenses (amount, reason, date) VALUES (%s,%s,%s)", (amount, reason, get_baghdad_time()))
                conn.commit()
            st.success("تم التسجيل")
            
elif "السجل والرواجع" in page:
    st.title("📝 سجل المبيعات")
    df_s = get_sales_data(limit=50)
    
    # عرض الجدول مع إمكانية التفاعل
    for i, row in df_s.iterrows():
        with st.container(border=True):
            col_info, col_btn = st.columns([4, 1])
            col_info.markdown(f"**{row['product_name']}** (x{row['qty']}) - {row['total']:,.0f} د.ع")
            col_info.caption(f"📅 {row['date']} | 🆔 {row['invoice_id']}")
            
            if col_btn.button("↩️ إرجاع", key=f"ret_{row['id']}"):
                # منطق الإرجاع المبسط
                try:
                    with conn.cursor() as cur:
                        # 1. إرجاع للمخزن
                        cur.execute("UPDATE public.variants SET stock = stock + %s WHERE id = %s", (row['qty'], row['variant_id']))
                        # 2. تسجيل كمرتجع
                        cur.execute("INSERT INTO public.returns (sale_id, product_name, qty, return_amount, return_date, status) VALUES (%s,%s,%s,%s,%s,%s)",
                                    (row['id'], row['product_name'], row['qty'], row['total'], get_baghdad_time(), 'Received'))
                        # 3. حذف أو تعديل البيع (اختياري، هنا سنبقيه للسجل لكن نسجل مصروف عكسي)
                        cur.execute("INSERT INTO public.expenses (amount, reason, date) VALUES (%s,%s,%s)", (row['total'], f"إرجاع فاتورة #{row['id']}", get_baghdad_time()))
                        conn.commit()
                    clear_cache()
                    st.toast("تم إرجاع القطعة للمخزن", icon="↩️")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"خطأ: {e}")

# تهيئة قاعدة البيانات عند أول تشغيل
if 'db_inited' not in st.session_state:
    init_db()
    st.session_state.db_inited = True
