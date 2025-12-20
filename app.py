import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem System", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

# --- إعدادات الأمان والاتصال ---
# يفضل وضع كلمة المرور في st.secrets لكن وضعت هنا قيمة افتراضية للعمل المباشر
ADMIN_PASSWORD = st.secrets.get("APP_PASSWORD", "1234") 

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS (نفس التصميم الرائع الخاص بك) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@200;300;400;500;600;700;800;900&display=swap');
    :root {
        --primary-color: #B76E79; --secondary-color: #D4A5A5;
        --bg-color: #1C1C1E; --card-bg: #2C2C2E;
        --text-color: #FFFFFF; --subtext-color: #AEAEB2;
        --border-radius: 16px; --input-bg: #2C2C2E; --border-color: #3A3A3C;
    }
    .stApp { direction: rtl; font-family: 'Cairo', sans-serif; background-color: var(--bg-color); color: var(--text-color); }
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, div, label, .stButton, .stTextInput, .stNumberInput, .stSelectbox {
        text-align: right !important; direction: rtl !important;
    }
    .stButton button {
        width: 100%; height: 50px; border-radius: 50px; border: none;
        background-color: var(--primary-color); color: white; font-weight: 700;
        box-shadow: 0 4px 10px rgba(183, 110, 121, 0.3); transition: all 0.3s;
    }
    .stButton button:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(183, 110, 121, 0.4); }
    div[data-testid="metric-container"] {
        background-color: var(--card-bg); padding: 20px; border-radius: var(--border-radius);
        border: 1px solid var(--border-color); text-align: center;
    }
    div[data-baseweb="input"], div[data-baseweb="select"] > div {
        background-color: var(--input-bg); border-radius: 12px; border: 1px solid var(--border-color); color: white;
    }
    div[data-baseweb="input"] input, div[data-baseweb="select"] span { color: white !important; }
    .css-card {
        background-color: var(--card-bg); padding: 18px; border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2); margin-bottom: 12px;
        border: 1px solid var(--border-color); transition: all 0.2s ease;
    }
    .css-card:hover { transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'sale_success' not in st.session_state: st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state: st.session_state.last_invoice_text = ""
if 'last_customer_username' not in st.session_state: st.session_state.last_customer_username = None

# --- 2. دالة الاتصال وتنفيذ الاستعلامات (محسنة) ---
def get_connection():
    # استخدام st.secrets للاتصال
    return psycopg2.connect(**st.secrets["postgres"])

def run_query(query, params=None, fetch=False, commit=False):
    """دالة مركزية لتنفيذ الاستعلامات بشكل آمن"""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
            if fetch:
                return cur.fetchall()
            return True
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"خطأ في قاعدة البيانات: {e}")
        return None
    finally:
        if conn: conn.close()

def run_insert_returning(query, params):
    """دالة خاصة للإدخال وإرجاع ID"""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            new_id = cur.fetchone()[0]
            conn.commit()
            return new_id
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"خطأ: {e}")
        return None
    finally:
        if conn: conn.close()

# تهيئة الجداول
def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
        )""",
        """CREATE TABLE IF NOT EXISTS public.customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""",
        # قمنا بتغيير date إلى TIMESTAMP لضمان الدقة في التقارير
        """CREATE TABLE IF NOT EXISTS public.sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TIMESTAMP, invoice_id TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS public.expenses (
            id SERIAL PRIMARY KEY, amount REAL, reason TEXT, date TIMESTAMP
        )"""
    ]
    for q in queries:
        run_query(q, commit=True)

init_db()

# --- 3. النوافذ المنبثقة ---
@st.dialog("تعديل عملية بيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"فاتورة: {product_name}")
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("الإجمالي", value=float(current_total))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ التعديلات", type="primary"):
            diff = new_qty - int(current_qty)
            # تحديث المخزون أولاً
            if diff != 0:
                run_query("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (int(diff), int(variant_id)), commit=True)
            # تحديث البيع
            run_query("UPDATE public.sales SET qty = %s, total = %s WHERE id = %s", (int(new_qty), float(new_total), int(sale_id)), commit=True)
            st.rerun()
    with c2:
        if st.button("🗑️ حذف العملية"):
            # إرجاع المخزون
            run_query("UPDATE public.variants SET stock = stock + %s WHERE id = %s", (int(current_qty), int(variant_id)), commit=True)
            run_query("DELETE FROM public.sales WHERE id = %s", (int(sale_id),), commit=True)
            st.rerun()

@st.dialog("تعديل المخزون")
def edit_stock_dialog(item_id, name, color, size, cost, price, stock):
    with st.form("edit_stk"):
        n_name = st.text_input("الاسم", value=name)
        c1, c2 = st.columns(2)
        n_col = c1.text_input("اللون", value=color)
        n_siz = c2.text_input("القياس", value=size)
        c3, c4, c5 = st.columns(3)
        n_cst = c3.number_input("كلفة", value=float(cost))
        n_prc = c4.number_input("بيع", value=float(price))
        n_stk = c5.number_input("عدد", value=int(stock))
        if st.form_submit_button("💾 حفظ التعديلات"):
            run_query("""
                UPDATE public.variants 
                SET name=%s, color=%s, size=%s, cost=%s, price=%s, stock=%s 
                WHERE id=%s
            """, (n_name, n_col, n_siz, float(n_cst), float(n_prc), int(n_stk), int(item_id)), commit=True)
            st.rerun()
    if st.button("🗑️ حذف الصنف نهائياً"):
        run_query("DELETE FROM public.variants WHERE id=%s", (int(item_id),), commit=True)
        st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>✨ نواعم بوتيك</h1>", unsafe_allow_html=True)
        with st.form("login"):
            password = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("🔓 دخول للنظام"):
                if password == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة")

# --- 5. التطبيق الرئيسي ---
def main_app():
    # Sidebar logout
    with st.sidebar:
        if st.button("تسجيل الخروج"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["🛍️ بيع", "📝 سجل", "👥 عملاء", "📦 مخزن", "💸 مصاريف", "📊 تقارير"])

    # === 1. البيع ===
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب!")
            st.balloons()
            st.markdown("### 📋 انسخ الرسالة:")
            st.code(st.session_state.last_invoice_text, language="text")
            
            if st.session_state.last_customer_username:
                ig_url = f"https://ig.me/m/{st.session_state.last_customer_username}"
                st.link_button(" إرسال الفاتورة عبر انستغرام", ig_url, type="primary")
            
            st.divider()
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False; st.session_state.last_invoice_text = ""; st.rerun()
        else:
            with st.container(border=True):
                # بحث SQL سريع بدلاً من Pandas
                srch = st.text_input("🔍 بحث عن منتج...", placeholder="اكتب اسم المنتج أو اللون...")
                
                results = []
                if srch:
                    search_term = f"%{srch}%"
                    results = run_query("""
                        SELECT * FROM public.variants 
                        WHERE (name ILIKE %s OR color ILIKE %s) AND stock > 0 
                        LIMIT 20
                    """, (search_term, search_term), fetch=True)
                else:
                    # عرض أحدث الإضافات إذا لم يكن هناك بحث
                    results = run_query("SELECT * FROM public.variants WHERE stock > 0 ORDER BY id DESC LIMIT 5", fetch=True)

                if results:
                    # تحويل النتائج لقائمة منسدلة
                    opts = {f"{r['name']} | {r['color']} ({r['size']})": r for r in results}
                    sel_key = st.selectbox("اختر المنتج:", list(opts.keys()), label_visibility="collapsed")
                    
                    if sel_key:
                        r = opts[sel_key]
                        st.caption(f"سعر: {r['price']:,.0f} | متوفر: {r['stock']}")
                        c1, c2 = st.columns(2)
                        q = c1.number_input("العدد", 1, int(r['stock']), 1)
                        p = c2.number_input("سعر البيع", value=float(r['price']))
                        
                        if st.button("🛒 أضف للسلة", type="secondary"):
                            # تحقق مزدوج من المخزون
                            current_stock = run_query("SELECT stock FROM public.variants WHERE id=%s", (r['id'],), fetch=True)
                            if current_stock and current_stock[0]['stock'] >= q:
                                item_dict = {
                                    "id": int(r['id']), "name": r['name'], "color": r['color'], "size": r['size'], 
                                    "cost": float(r['cost']), "price": float(p), "qty": int(q), "total": float(p*q)
                                }
                                st.session_state.cart.append(item_dict)
                                st.toast("تمت الإضافة", icon="✅")
                            else:
                                st.error("عذراً، الكمية لم تعد متوفرة!")

            if st.session_state.cart:
                st.divider()
                st.markdown("### 🛒 سلة المشتريات")
                for i, item in enumerate(st.session_state.cart):
                    st.markdown(f"""
                    <div class="css-card" style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="text-align: right;">
                            <div style="font-weight: 800; font-size: 1.1em; color: var(--text-color);">{item['name']}</div>
                            <div style="color: var(--subtext-color); font-size: 0.9em;">{item['color']} | {item['size']}</div>
                            <div style="color: var(--primary-color); font-weight: 600;">{item['qty']} × {item['price']:,.0f}</div>
                        </div>
                        <div style="text-align: left; font-weight: 800; color: var(--primary-color); font-size: 1.2em;">
                            {item['total']:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # زر حذف السلة
                if st.button("إفراغ السلة"):
                    st.session_state.cart = []
                    st.rerun()

                st.divider()
                st.markdown("##### 👤 بيانات العميل")
                with st.container(border=True):
                    cust_type = st.radio("نوع العميل", ["جديد", "سابق"], horizontal=True)
                    cust_id_val, cust_name_val, cust_username_val, cust_phone_val, cust_address_val = None, "", "", "", ""
                    
                    if cust_type == "سابق":
                        # جلب العملاء للبحث
                        all_custs = run_query("SELECT id, name, phone, username, address FROM public.customers ORDER BY name", fetch=True)
                        if all_custs:
                            c_opts = {f"{x['name']} - {x['phone']}": x for x in all_custs}
                            c_sel = st.selectbox("الاسم:", list(c_opts.keys()))
                            if c_sel:
                                selected_row = c_opts[c_sel]
                                cust_id_val = int(selected_row['id'])
                                cust_name_val = selected_row['name']
                                cust_username_val = selected_row['username']
                                cust_phone_val = selected_row['phone']
                                cust_address_val = selected_row['address']
                        else: st.warning("لا يوجد عملاء")
                    else:
                        c_n = st.text_input("الاسم (حساب الانستغرام)")
                        c_p = st.text_input("الهاتف")
                        c_a = st.text_input("العنوان")
                        cust_name_val = c_n
                        cust_username_val = c_n
                        cust_phone_val = c_p
                        cust_address_val = c_a
                
                tot = sum(x['total'] for x in st.session_state.cart)
                
                # Invoice Text
                invoice_msg = f"🌸 تم تثبيت طلبج بنجاح حبيبتي\n📄 تفاصيل الطلب:\n"
                for i, x in enumerate(st.session_state.cart):
                    invoice_msg += f"{x['name']} | {x['color']} ({x['size']})\nالعدد: {x['qty']} | السعر: {x['price']:,.0f}\n"
                invoice_msg += f"---\nالمجموع الكلي: {tot:,.0f} د.ع\n📍 العنوان: {cust_address_val}\n📞 الهاتف: {cust_phone_val}\n\n✨ التوصيل خلال 2-4 أيام، يرجى فحص الطلب مع المندوب."

                st.markdown(f"""
                <div style="background-color: var(--input-bg); padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid var(--border-color);">
                    <div style="font-size: 0.9em; color: var(--subtext-color);">المجموع الكلي</div>
                    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">{tot:,.0f} د.ع</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("✅ إتمام البيع", type="primary"):
                    if not cust_name_val: st.error("الاسم مطلوب!"); st.stop()
                    
                    try:
                        # 1. معالجة العميل
                        if cust_type == "جديد":
                            # التحقق من التكرار
                            exist = run_query("SELECT id FROM public.customers WHERE phone = %s", (c_p,), fetch=True)
                            if exist:
                                cust_id_val = exist[0]['id'] # استخدام العميل الموجود
                            else:
                                cust_id_val = run_insert_returning(
                                    "INSERT INTO public.customers (name, phone, address, username) VALUES (%s,%s,%s,%s) RETURNING id",
                                    (c_n, c_p, c_a, c_n)
                                )
                        
                        baghdad_now = get_baghdad_time()
                        inv = baghdad_now.strftime("%Y%m%d%H%M")
                        
                        # 2. إدخال المبيعات
                        for x in st.session_state.cart:
                            # تحديث المخزون
                            run_query("UPDATE public.variants SET stock=stock-%s WHERE id=%s", (int(x['qty']), int(x['id'])), commit=True)
                            
                            profit_calc = (x['price'] - x['cost']) * x['qty']
                            run_query("""
                                INSERT INTO public.sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) 
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                            """, (int(cust_id_val), int(x['id']), x['name'], int(x['qty']), float(x['total']), float(profit_calc), baghdad_now, inv), commit=True)
                        
                        st.session_state.cart = []
                        st.session_state.sale_success = True
                        st.session_state.last_invoice_text = invoice_msg
                        st.session_state.last_customer_username = cust_username_val
                        st.rerun()
                    except Exception as e:
                        st.error(f"حدث خطأ: {e}")

    # === 2. السجل ===
    with tabs[1]:
        st.caption("آخر العمليات (محدث)")
        sales_log = run_query("""
            SELECT s.*, c.name as customer_name, v.color, v.size 
            FROM public.sales s 
            LEFT JOIN public.customers c ON s.customer_id = c.id 
            LEFT JOIN public.variants v ON s.variant_id = v.id 
            ORDER BY s.id DESC LIMIT 30
        """, fetch=True)
        
        if sales_log:
            for r in sales_log:
                with st.container(border=True):
                    c1, c2 = st.columns([4,1])
                    c_name = r['customer_name'] if r['customer_name'] else "غير مسجل"
                    details = f" | 🎨 {r['color']} - {r['size']}" if r['color'] else ""
                    
                    c1.markdown(f"**{r['product_name']}** ({r['qty']})")
                    c1.caption(f"👤 {c_name} | 💰 {r['total']:,.0f}{details}")
                    if c2.button("⚙️", key=f"e{r['id']}"): 
                        edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])
        else:
            st.info("لا توجد مبيعات بعد")

    # === 3. العملاء ===
    with tabs[2]:
        search_query = st.text_input("🔍 بحث عن عميل (الاسم أو الهاتف)", "")
        
        query_cust = """
            SELECT c.id, c.name, c.phone, c.username, c.address,
                   COALESCE(SUM(s.total), 0) as total_spend,
                   MAX(s.date) as last_purchase
            FROM public.customers c
            LEFT JOIN public.sales s ON c.id = s.customer_id
        """
        params = ()
        if search_query:
            query_cust += " WHERE c.name ILIKE %s OR c.phone ILIKE %s OR c.username ILIKE %s"
            term = f"%{search_query}%"
            params = (term, term, term)
            
        query_cust += " GROUP BY c.id ORDER BY total_spend DESC LIMIT 50"
        
        df_cust = pd.DataFrame(run_query(query_cust, params, fetch=True) or [])
        
        if not df_cust.empty:
            col1, col2 = st.columns(2)
            for i, r in df_cust.iterrows():
                with (col1 if i % 2 == 0 else col2):
                    with st.container(border=True):
                        st.markdown(f"**{r['name']}**")
                        st.caption(f"📞 {r['phone']} | 📍 {r['address']}")
                        c_s1, c_s2 = st.columns(2)
                        c_s1.metric("الشراء", f"{r['total_spend']:,.0f}")
                        if pd.notna(r['last_purchase']):
                            c_s2.caption(f"آخر ظهور: {str(r['last_purchase']).split(' ')[0]}")
        else:
            st.info("لا يوجد نتائج")

    # === 4. المخزون ===
    with tabs[3]:
        # إحصائيات سريعة
        stats = run_query("SELECT SUM(stock) as cnt, SUM(stock*price) as val, SUM(stock*cost) as cst FROM public.variants", fetch=True)[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("📦 عدد القطع", f"{stats['cnt'] or 0}")
        m2.metric("💰 قيمة البيع", f"{stats['val'] or 0:,.0f}")
        m3.metric("💵 ربح متوقع", f"{(stats['val'] or 0) - (stats['cst'] or 0):,.0f}")
        
        st.divider()
        
        c_ctrl1, c_ctrl2 = st.columns([3, 1])
        with c_ctrl1:
            search_stock = st.text_input("🔍 بحث في المخزون...", label_visibility="collapsed")
        with c_ctrl2:
            with st.popover("➕ إضافة صنف"):
                with st.form("add_new_stock"):
                    nm = st.text_input("اسم المنتج")
                    cl = st.text_input("اللون")
                    sz = st.text_input("القياس")
                    c_f1, c_f2 = st.columns(2)
                    stk = c_f1.number_input("العدد", 1)
                    pr = c_f2.number_input("سعر البيع", 0.0)
                    cst = st.number_input("سعر التكلفة", 0.0)
                    if st.form_submit_button("حفظ"):
                        run_query("INSERT INTO public.variants (name,color,size,stock,price,cost) VALUES (%s,%s,%s,%s,%s,%s)", 
                                  (nm, cl, sz, int(stk), float(pr), float(cst)), commit=True)
                        st.rerun()

        # عرض البيانات
        q_stock = "SELECT * FROM public.variants"
        p_stock = ()
        if search_stock:
            q_stock += " WHERE name ILIKE %s OR color ILIKE %s"
            p_stock = (f"%{search_stock}%", f"%{search_stock}%")
        q_stock += " ORDER BY name"
        
        df_inv = pd.DataFrame(run_query(q_stock, p_stock, fetch=True) or [])
        
        if not df_inv.empty:
            view_mode = st.radio("العرض", ["كروت", "جدول"], horizontal=True, label_visibility="collapsed")
            if view_mode == "جدول":
                st.dataframe(df_inv[['name', 'color', 'size', 'stock', 'price', 'cost']], use_container_width=True)
            else:
                unique_names = df_inv['name'].unique()
                for p_name in unique_names:
                    p_group = df_inv[df_inv['name'] == p_name]
                    with st.container(border=True):
                        st.markdown(f"#### 👗 {p_name}")
                        for color in p_group['color'].unique():
                            c_group = p_group[p_group['color'] == color]
                            r1, r2 = st.columns([1, 4])
                            r1.markdown(f"**🎨 {color}**")
                            with r2:
                                chips = '<div style="display: flex; gap: 5px; flex-wrap: wrap;">'
                                for _, row in c_group.iterrows():
                                    bc = "#30D158" if row['stock'] >= 5 else "#FF9F0A"
                                    if row['stock'] == 0: bc = "#FF453A"
                                    chips += f'<span style="background:{bc}33; border:1px solid {bc}; padding:2px 8px; border-radius:10px; font-size:0.8em">{row["size"]} | {row["stock"]}</span>'
                                chips += "</div>"
                                st.markdown(chips, unsafe_allow_html=True)
                                
                                with st.expander("تعديل"):
                                    cols = st.columns(4)
                                    for idx, (_, row) in enumerate(c_group.iterrows()):
                                        with cols[idx % 4]:
                                            if st.button(f"{row['size']}", key=f"ed_{row['id']}"):
                                                edit_stock_dialog(row['id'], row['name'], row['color'], row['size'], row['cost'], row['price'], row['stock'])

    # === 5. المصاريف ===
    with tabs[4]:
        with st.form("add_exp"):
            c1, c2 = st.columns([1, 3])
            amount = c1.number_input("المبلغ", min_value=1.0, step=250.0)
            reason = c2.text_input("السبب")
            if st.form_submit_button("تسجيل"):
                if reason:
                    run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s, %s, %s)", 
                              (float(amount), reason, get_baghdad_time()), commit=True)
                    st.success("تم التسجيل"); st.rerun()

        st.subheader("سجل المصاريف")
        exps = run_query("SELECT * FROM public.expenses ORDER BY id DESC LIMIT 20", fetch=True)
        if exps:
            for x in exps:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1,3,1])
                    c1.markdown(f"**{x['amount']:,.0f}**")
                    c2.text(x['reason'])
                    # عرض التاريخ بشكل جميل
                    d_str = str(x['date']).split('.')[0] if x['date'] else ""
                    c3.caption(d_str)
                    if c3.button("🗑️", key=f"dx{x['id']}"):
                        run_query("DELETE FROM public.expenses WHERE id=%s", (x['id'],), commit=True)
                        st.rerun()

    # === 6. التقارير (SQL Native) ===
    with tabs[5]:
        st.header("📊 ذكاء الأعمال (BI)")
        
        # دوال مساعدة للتقارير تستخدم SQL Time
        def get_sql_stats(interval_condition):
            q = f"""
                SELECT COALESCE(SUM(total), 0) as sales, COALESCE(SUM(profit), 0) as profit, COUNT(DISTINCT invoice_id) as invs 
                FROM public.sales WHERE {interval_condition}
            """
            return run_query(q, fetch=True)[0]

        def get_sql_exp(interval_condition):
            q = f"SELECT COALESCE(SUM(amount), 0) as amt FROM public.expenses WHERE {interval_condition}"
            res = run_query(q, fetch=True)
            return res[0]['amt'] if res else 0

        # الاستعلامات تعتمد على تحويل العمود إلى Date للمقارنة
        # ملاحظة: ::date في بوستجريس تقوم باقتطاع الوقت، وهو المطلوب هنا
        
        # 1. اليوم
        s_today = get_sql_stats("date::date = CURRENT_DATE")
        e_today = get_sql_exp("date::date = CURRENT_DATE")
        
        st.markdown("##### 📅 اليوم")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("مبيعات", f"{s_today['sales']:,.0f}", f"{s_today['invs']} فاتورة")
        c2.metric("أرباح", f"{s_today['profit']:,.0f}")
        c3.metric("مصاريف", f"{e_today:,.0f}", delta_color="inverse")
        c4.metric("صافي", f"{s_today['profit'] - e_today:,.0f}")
        
        st.divider()
        
        # 2. الأسبوع (آخر 7 أيام)
        s_week = get_sql_stats("date >= CURRENT_DATE - INTERVAL '7 days'")
        e_week = get_sql_exp("date >= CURRENT_DATE - INTERVAL '7 days'")
        
        st.markdown("##### 🗓️ آخر 7 أيام")
        c1, c2, c3 = st.columns(3)
        c1.metric("مبيعات", f"{s_week['sales']:,.0f}")
        c2.metric("مصاريف", f"{e_week:,.0f}", delta_color="inverse")
        c3.metric("صافي الربح", f"{s_week['profit'] - e_week:,.0f}")
        
        st.divider()

        # 3. الأفضل مبيعاً
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            st.subheader("🏆 المنتجات الأكثر ربحاً")
            top_prod = run_query("""
                SELECT product_name, SUM(profit) as prf, SUM(qty) as q 
                FROM public.sales GROUP BY product_name ORDER BY prf DESC LIMIT 5
            """, fetch=True)
            if top_prod:
                st.dataframe(pd.DataFrame(top_prod), hide_index=True, use_container_width=True)

        with c_b2:
            st.subheader("🎨 الألوان الأكثر طلباً")
            top_col = run_query("""
                SELECT v.color, SUM(s.qty) as q 
                FROM public.sales s JOIN public.variants v ON s.variant_id = v.id 
                GROUP BY v.color ORDER BY q DESC LIMIT 5
            """, fetch=True)
            if top_col:
                st.bar_chart(pd.DataFrame(top_col).set_index("color"))

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
