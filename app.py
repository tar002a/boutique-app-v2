import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
import itertools
import time
import plotly.graph_objects as go

# --- 1. إعداد الصفحة ---
st.set_page_config(
    page_title="نواعم بوتيك", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="collapsed"
)

# --- 2. تصميم CSS احترافي (إصلاح الألوان + الموبايل) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    :root {
        --primary: #D81B60;       /* وردي غامق */
        --bg-light: #F3F4F6;      /* خلفية عامة */
        --card-white: #FFFFFF;    /* خلفية البطاقات */
        --text-dark: #111827;     /* نص أسود */
        --text-grey: #6B7280;     /* نص رمادي */
    }

    * {font-family: 'Cairo', sans-serif !important;}
    
    /* إجبار الخلفية والنصوص على الوضع الفاتح */
    .stApp {
        direction: rtl;
        background-color: var(--bg-light);
        color: var(--text-dark);
    }
    
    /* إصلاح ألوان الحقول (Input Fields) لتكون مقروءة دائماً */
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stMultiSelect div {
        color: #000000 !important;
        background-color: #ffffff !important;
        border-color: #E5E7EB;
    }
    
    /* تسميات الحقول */
    label {
        color: var(--text-dark) !important;
        font-weight: 700 !important;
    }

    /* إخفاء القائمة الجانبية تماماً */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    
    /* شريط التنقل العلوي (NavBar) */
    div[role="radiogroup"] {
        background-color: var(--card-white);
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        border: 1px solid #e5e7eb;
        overflow-x: auto;
    }
    
    div[role="radiogroup"] label {
        background: transparent !important;
        border: none !important;
        color: var(--text-grey) !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: 0.3s;
        min-width: 80px;
        text-align: center;
    }
    
    div[role="radiogroup"] label[aria-checked="true"] {
        color: var(--primary) !important;
        background-color: #FCE4EC !important;
        border-radius: 10px !important;
    }

    /* تنسيق البطاقات (Containers) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--card-white);
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        padding: 15px;
    }

    /* الأزرار */
    .stButton button {
        border-radius: 12px; height: 48px; font-weight: bold; border: none; transition: 0.2s;
    }
    /* زر أساسي */
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #D81B60 0%, #AD1457 100%);
        color: white !important;
        box-shadow: 0 4px 6px rgba(216, 27, 96, 0.3);
    }
    /* زر ثانوي (للإضافة) */
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #F9FAFB;
        color: var(--text-dark) !important;
        border: 1px solid #D1D5DB !important;
    }
    
    /* تحسين الجداول */
    div[data-testid="stDataFrame"] {direction: rtl;}
    
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. الاتصال بقاعدة البيانات ---
@st.cache_resource
def init_connection():
    """إنشاء اتصال واحد وتخزينه في الذاكرة"""
    try:
        # تأكد من وضع DB_URL في st.secrets
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
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

# --- 4. إدارة الجلسة (Session) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'auth' not in st.session_state: st.session_state.auth = False

# --- 5. دوال الاستجابة الفورية (Callbacks) ---
# هذه الدوال تضمن تنفيذ الأوامر قبل إعادة تحميل الصفحة

def add_to_cart_callback(item_id, name, price, cost, qty, max_stock):
    """إضافة منتج للسلة فوراً"""
    if qty > max_stock:
        st.toast(f"الكمية المطلوبة غير متوفرة (المتوفر: {max_stock})", icon="⚠️")
        return

    if 'cart' not in st.session_state: st.session_state.cart = []

    found = False
    for item in st.session_state.cart:
        if item['id'] == item_id:
            item['qty'] += qty
            item['total'] += qty * price
            found = True
            break
    
    if not found:
        st.session_state.cart.append({
            "id": item_id, "name": name, "price": price, 
            "qty": qty, "total": qty * price, "cost": cost
        })
    
    st.toast(f"تمت إضافة: {name}", icon="✅")

def remove_from_cart_callback(index):
    """حذف من السلة فوراً"""
    try:
        st.session_state.cart.pop(index)
        st.toast("تم الحذف", icon="🗑️")
    except:
        pass

# --- 6. منطق التطبيق ---

def login_ui():
    """شاشة تسجيل الدخول"""
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:#D81B60;'>🌸 بوتيك نواعم</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:gray;'>نظام الإدارة المتكامل</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            pwd = st.text_input("🔑 كلمة المرور", type="password")
            if st.button("تسجيل الدخول", type="primary"):
                # كلمة المرور الافتراضية admin إذا لم توجد في الأسرار
                admin_pass = st.secrets.get("ADMIN_PASS", "admin")
                if pwd == admin_pass:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.toast("كلمة المرور خاطئة", icon="❌")

def process_sale(customer_name):
    """تنفيذ عملية البيع وحفظها في قاعدة البيانات"""
    conn = init_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        dt = datetime.now(pytz.timezone('Asia/Baghdad'))
        inv_id = dt.strftime("%Y%m%d%H%M") # رقم فاتورة فريد
        
        # 1. التعامل مع العميل
        cur.execute("SELECT id FROM customers WHERE name = %s", (customer_name,))
        res = cur.fetchone()
        if res:
            cust_id = res[0]
        else:
            cur.execute("INSERT INTO customers (name) VALUES (%s) RETURNING id", (customer_name,))
            cust_id = cur.fetchone()[0]
        
        # 2. خصم المخزون وحفظ المبيعات
        for item in st.session_state.cart:
            # قفل الصف لتجنب تضارب البيانات
            cur.execute("SELECT stock FROM variants WHERE id = %s FOR UPDATE", (item['id'],))
            current_stock = cur.fetchone()[0]
            
            if current_stock < item['qty']:
                raise Exception(f"نفذت كمية المنتج: {item['name']}")
            
            # تحديث المخزون
            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
            
            # حساب الربح
            profit = (item['price'] - item['cost']) * item['qty']
            
            # تسجيل العملية
            cur.execute("""
                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
            
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.toast(f"حدث خطأ: {e}", icon="⚠️")
        return False

def main_app():
    """واجهة التطبيق الرئيسية"""
    # ترويسة الصفحة وزر الخروج
    col_head, col_out = st.columns([5, 1])
    col_head.markdown("<h3 style='margin:0; color:#D81B60;'>🌸 نواعم بوتيك</h3>", unsafe_allow_html=True)
    if col_out.button("خروج", key="logout_btn"):
        st.session_state.auth = False
        st.rerun()

    st.write("") # مسافة

    # شريط التنقل العلوي (Nav Bar)
    selected_page = st.radio(
        "nav", 
        ["نقطة البيع 🛒", "المخزون 📦", "التقارير 📊", "الفواتير 🧾"], 
        horizontal=True, 
        label_visibility="collapsed"
    )
    
    st.write("")

    # ==========================================
    # صفحة 1: نقطة البيع (POS)
    # ==========================================
    if "نقطة البيع" in selected_page:
        # شريط المعلومات العائم
        cart_total = sum(i['total'] for i in st.session_state.cart)
        st.info(f"💰 إجمالي السلة: **{cart_total:,.0f} د.ع** | عدد العناصر: **{len(st.session_state.cart)}**")
        
        tab_products, tab_cart = st.tabs(["🛍️ المنتجات", f"🛒 السلة ({len(st.session_state.cart)})"])
        
        # --- عرض المنتجات ---
        with tab_products:
            search_term = st.text_input("بحث سريع", placeholder="اسم المنتج أو اللون...", label_visibility="collapsed")
            
            # استعلام ذكي
            query = "SELECT * FROM variants WHERE is_active = TRUE AND stock > 0"
            params = []
            if search_term:
                query += " AND (name ILIKE %s OR color ILIKE %s)"
                params = [f"%{search_term}%", f"%{search_term}%"]
            query += " ORDER BY name ASC, id DESC LIMIT 20"
            
            items_df = run_query(query, tuple(params), fetch_data=True)
            
            if items_df is not None and not items_df.empty:
                # شبكة عرض المنتجات (Grid)
                grid_cols = st.columns(2)
                for index, row in items_df.iterrows():
                    with grid_cols[index % 2]:
                        with st.container(border=True):
                            # تفاصيل المنتج
                            st.markdown(f"<div style='font-weight:bold; font-size:1.1em'>{row['name']}</div>", unsafe_allow_html=True)
                            st.caption(f"🎨 {row['color']} | 📏 {row['size']}")
                            
                            # السعر والمخزون
                            c_pr, c_st = st.columns(2)
                            c_pr.markdown(f"<span style='color:#D81B60; font-weight:bold'>{int(row['price']):,} د.ع</span>", unsafe_allow_html=True)
                            c_st.markdown(f"<span style='color:gray; font-size:0.8em'>متبقي: {row['stock']}</span>", unsafe_allow_html=True)
                            
                            # أدوات الإضافة
                            c_input, c_btn = st.columns([1, 2])
                            qty_val = c_input.number_input("Q", 1, max_value=row['stock'], key=f"q_{row['id']}", label_visibility="collapsed")
                            
                            # زر الإضافة باستخدام Callback (الحل الجذري)
                            c_btn.button(
                                "أضف ➕", 
                                key=f"add_{row['id']}", 
                                type="secondary",
                                on_click=add_to_cart_callback,
                                args=(row['id'], row['name'], row['price'], row['cost'], qty_val, row['stock'])
                            )
            else:
                st.warning("لا توجد منتجات مطابقة أو المخزون نفذ")

        # --- عرض السلة ---
        with tab_cart:
            if st.session_state.cart:
                for idx, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        col_n, col_p, col_d = st.columns([3, 2, 1])
                        with col_n:
                            st.markdown(f"**{item['name']}**")
                            st.caption(f"العدد: {item['qty']}")
                        with col_p:
                            st.markdown(f"**{item['total']:,.0f}**")
                        with col_d:
                            st.button("🗑️", key=f"rem_{idx}", on_click=remove_from_cart_callback, args=(idx,))
                
                st.divider()
                st.markdown(f"<h2 style='text-align:center; color:#D81B60'>{cart_total:,.0f} د.ع</h2>", unsafe_allow_html=True)
                
                cust_input = st.text_input("اسم العميل", placeholder="الاسم لحفظ الفاتورة")
                
                if st.button("✅ إتمام البيع", type="primary", use_container_width=True):
                    if cust_input:
                        if process_sale(cust_input):
                            st.session_state.cart = [] # تصفير
                            st.balloons()
                            st.success("تمت العملية بنجاح!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("يجب إدخال اسم العميل")
            else:
                st.info("السلة فارغة. اذهب لتبويب المنتجات للإضافة.")

    # ==========================================
    # صفحة 2: المخزون (Inventory)
    # ==========================================
    elif "المخزون" in selected_page:
        
        # قسم: المولد السريع للمنتجات (Bulk Add)
        with st.expander("➕ إضافة بضاعة جديدة (متعددة الألوان/المقاسات)", expanded=False):
            st.markdown("##### 1. المعلومات الأساسية")
            prod_name = st.text_input("اسم المنتج (مثال: فستان سهرة)")
            
            c_c, c_s = st.columns(2)
            colors_list = ["أحمر", "أسود", "أبيض", "أزرق", "أخضر", "بيج", "وردي", "ذهبي", "فضي", "رصاصي"]
            sizes_list = ["S", "M", "L", "XL", "XXL", "Free Size", "36", "38", "40", "42", "44"]
            
            sel_colors = c_c.multiselect("الألوان المتوفرة", colors_list)
            sel_sizes = c_s.multiselect("المقاسات المتوفرة", sizes_list)
            
            st.markdown("##### 2. السعر والكمية")
            col_num1, col_num2, col_num3 = st.columns(3)
            cost_p = col_num1.number_input("سعر التكلفة", 0.0, step=1000.0)
            sell_p = col_num2.number_input("سعر البيع", 0.0, step=1000.0)
            stock_p = col_num3.number_input("العدد لكل قطعة", 1)
            
            if st.button("🚀 إنشاء المنتجات وإضافتها", type="primary"):
                if prod_name and sel_colors and sel_sizes:
                    # توليد الاحتمالات
                    combinations = list(itertools.product(sel_colors, sel_sizes))
                    conn = init_connection()
                    cur = conn.cursor()
                    try:
                        for color, size in combinations:
                            cur.execute("""
                                INSERT INTO variants (name, color, size, stock, cost, price, is_active)
                                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                            """, (prod_name, color, size, stock_p, cost_p, sell_p))
                        conn.commit()
                        st.toast(f"تم إضافة {len(combinations)} صنف جديد!", icon="🎉")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"خطأ: {e}")
                else:
                    st.error("يرجى ملء جميع الحقول")

        st.write("---")
        st.markdown("### 📦 جرد المخزون الحالي")
        
        # البحث والفلترة
        filter_txt = st.text_input("🔍 تصفية الجدول", placeholder="ابحث بالاسم، اللون...")
        
        # استعلام العرض (المتوفر أولاً)
        inv_query = "SELECT id, name, color, size, stock, price, cost, is_active FROM variants"
        inv_params = []
        if filter_txt:
            inv_query += " WHERE name ILIKE %s OR color ILIKE %s"
            inv_params = [f"%{filter_txt}%", f"%{filter_txt}%"]
        
        # ترتيب: المتوفر > الاسم
        inv_query += " ORDER BY (stock > 0) DESC, name ASC"
        
        df_inv = run_query(inv_query, tuple(inv_params), fetch_data=True)
        
        if df_inv is not None:
            # محرر البيانات (Data Editor)
            edited_df = st.data_editor(
                df_inv,
                column_config={
                    "id": None, # إخفاء
                    "name": "اسم المنتج",
                    "color": "اللون",
                    "size": st.column_config.TextColumn("المقاس", width="small"),
                    "stock": st.column_config.NumberColumn("الكمية", min_value=0, format="%d"),
                    "price": st.column_config.NumberColumn("سعر البيع", format="%d"),
                    "cost": st.column_config.NumberColumn("التكلفة", format="%d"),
                    "is_active": "نشط؟"
                },
                use_container_width=True,
                num_rows="dynamic", # يسمح بالإضافة
                key="inventory_main_edit",
                height=500
            )
            
            if st.button("💾 حفظ التغييرات في المخزون", type="primary"):
                conn = init_connection()
                cur = conn.cursor()
                try:
                    # ملاحظة: هذا تحديث بسيط، للتطبيقات الكبيرة يفضل تتبع التغييرات فقط
                    for index, row in edited_df.iterrows():
                        if row['id'] and not pd.isna(row['id']): # تحديث
                            cur.execute("""
                                UPDATE variants SET name=%s, color=%s, size=%s, stock=%s, price=%s, cost=%s, is_active=%s
                                WHERE id=%s
                            """, (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], row['is_active'], row['id']))
                        else: # جديد
                             cur.execute("""
                                INSERT INTO variants (name, color, size, stock, price, cost, is_active)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], True))
                    conn.commit()
                    st.toast("تم الحفظ بنجاح", icon="💾")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"خطأ: {e}")

    # ==========================================
    # صفحة 3: التقارير (Reports)
    # ==========================================
    elif "التقارير" in selected_page:
        st.markdown("### 📊 ملخص الأداء المالي")
        
        days_opt = st.selectbox("الفترة الزمنية", [1, 7, 30, 365], format_func=lambda x: "اليوم" if x==1 else f"آخر {x} يوم")
        start_d = (datetime.now() - timedelta(days=days_opt)).strftime('%Y-%m-%d')
        
        # جلب البيانات الإجمالية
        df_sum = run_query(f"SELECT SUM(total) as s, SUM(profit) as p FROM sales WHERE date >= '{start_d}'", fetch_data=True)
        
        # البطاقات
        m1, m2, m3 = st.columns(3)
        sales_val = df_sum.iloc[0]['s'] if df_sum is not None and df_sum.iloc[0]['s'] else 0
        profit_val = df_sum.iloc[0]['p'] if df_sum is not None and df_sum.iloc[0]['p'] else 0
        margin = (profit_val / sales_val * 100) if sales_val > 0 else 0
        
        with m1: st.container(border=True).metric("المبيعات", f"{sales_val:,.0f}", "د.ع")
        with m2: st.container(border=True).metric("الأرباح", f"{profit_val:,.0f}", "د.ع")
        with m3: st.container(border=True).metric("هامش الربح", f"{margin:.1f}%")
        
        # الرسم البياني
        st.subheader("📈 الرسم البياني")
        df_daily = run_query(f"""
            SELECT date::date as day, SUM(total) as total 
            FROM sales WHERE date >= '{start_d}' 
            GROUP BY day ORDER BY day
        """, fetch_data=True)
        
        if df_daily is not None and not df_daily.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_daily['day'], y=df_daily['total'], mode='lines+markers', name='المبيعات', line=dict(color='#D81B60', width=3)))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد بيانات كافية للرسم البياني")

    # ==========================================
    # صفحة 4: الفواتير (Invoices)
    # ==========================================
    elif "الفواتير" in selected_page:
        st.markdown("### 🧾 أرشيف الفواتير")
        
        df_logs = run_query("""
            SELECT s.invoice_id as "رقم الفاتورة", c.name as "العميل", 
                   s.product_name as "المنتج", s.qty as "العدد", s.total as "القيمة", s.date as "التوقيت"
            FROM sales s 
            JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC LIMIT 100
        """, fetch_data=True)
        
        st.dataframe(df_logs, use_container_width=True, hide_index=True)

# --- نقطة البدء ---
if __name__ == "__main__":
    if st.session_state.auth:
        main_app()
    else:
        login_ui()
