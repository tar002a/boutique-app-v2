import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import psycopg2
from psycopg2.extras import execute_values
import time
import plotly.express as px
import plotly.graph_objects as go

# --- 1. إعدادات النظام والأمان ---
st.set_page_config(
    page_title="Nawaem ERP Pro 🚀", 
    layout="wide", 
    page_icon="💎", 
    initial_sidebar_state="expanded"
)

# حقن CSS احترافي
def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
        :root { --primary: #D48896; --bg: #0E1117; --card: #1A1C24; }
        * { font-family: 'Cairo', sans-serif !important; direction: rtl; }
        .stApp { background-color: var(--bg); }
        .stMetric { background-color: var(--card); border: 1px solid #333; border-radius: 10px; padding: 10px; }
        .big-font { font-size: 20px !important; font-weight: bold; }
        /* تحسين حقول الإدخال لتشبه الأنظمة الحقيقية */
        input { background-color: #252830 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# --- 2. إدارة قاعدة البيانات (Backend Class) ---
class DatabaseManager:
    def __init__(self):
        try:
            # استبدل هذا ببياناتك أو st.secrets
            self.conn_params = st.secrets["postgres"]
        except:
            st.error("يرجى إعداد st.secrets للاتصال بقاعدة البيانات")
            st.stop()

    def get_conn(self):
        return psycopg2.connect(**self.conn_params)

    def init_schema(self):
        conn = self.get_conn()
        with conn.cursor() as c:
            # جدول المنتجات (تمت إضافة الباركود والمورد)
            c.execute("""CREATE TABLE IF NOT EXISTS variants (
                id SERIAL PRIMARY KEY, barcode TEXT UNIQUE, name TEXT, color TEXT, size TEXT, 
                cost REAL, price REAL, stock INTEGER, supplier_id INTEGER
            )""")
            # الموردين
            c.execute("""CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY, name TEXT, phone TEXT, balance REAL DEFAULT 0
            )""")
            # العملاء
            c.execute("""CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY, name TEXT, phone TEXT, points INTEGER DEFAULT 0
            )""")
            # المبيعات
            c.execute("""CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY, invoice_id TEXT, customer_id INTEGER, 
                total_amount REAL, discount REAL, final_amount REAL, 
                date TIMESTAMP, created_by TEXT
            )""")
            # تفاصيل الفاتورة (للحفاظ على البيانات حتى لو تغير سعر المنتج لاحقاً)
            c.execute("""CREATE TABLE IF NOT EXISTS sale_items (
                id SERIAL PRIMARY KEY, sale_id INTEGER, variant_id INTEGER, 
                product_name TEXT, qty INTEGER, unit_cost REAL, unit_price REAL, total REAL
            )""")
            # المصاريف
            c.execute("""CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY, category TEXT, amount REAL, note TEXT, date TIMESTAMP
            )""")
            conn.commit()
            conn.close()

    def run_query(self, query, params=None, fetch=True, commit=False):
        conn = self.get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if commit:
                    conn.commit()
                    return True
                if fetch:
                    cols = [desc[0] for desc in cur.description]
                    return pd.DataFrame(cur.fetchall(), columns=cols)
        except Exception as e:
            conn.rollback()
            st.toast(f"Error: {e}", icon="❌")
            return None
        finally:
            conn.close()

db = DatabaseManager()

# --- 3. الدوال المساعدة (Helpers) ---
def get_time(): return datetime.now(pytz.timezone('Asia/Baghdad'))

def check_login():
    if 'auth' not in st.session_state: st.session_state.auth = False
    
    if not st.session_state.auth:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image("https://cdn-icons-png.flaticon.com/512/9005/9005479.png", width=100)
            st.title("تسجيل الدخول للنظام")
            with st.form("login_form"):
                user = st.text_input("اسم المستخدم")
                pw = st.text_input("كلمة المرور", type="password")
                if st.form_submit_button("دخول"):
                    # نظام دخول بسيط (يمكن ربطه بقاعدة البيانات لاحقاً)
                    if user == "admin" and pw == "admin":
                        st.session_state.auth = True
                        st.session_state.role = "Admin"
                        st.rerun()
                    elif user == "cashier" and pw == "123":
                        st.session_state.auth = True
                        st.session_state.role = "Cashier"
                        st.rerun()
                    else:
                        st.error("بيانات خاطئة")
        st.stop()

def logout():
    st.session_state.auth = False
    st.rerun()

# --- 4. واجهات التطبيق (Modules) ---

# تهيئة الجلسة
if 'cart' not in st.session_state: st.session_state.cart = []
if 'db_ready' not in st.session_state: db.init_schema(); st.session_state.db_ready = True

# التحقق من الدخول
check_login()

# القائمة الجانبية
with st.sidebar:
    st.markdown(f"### 👤 مرحباً, {st.session_state.role}")
    if st.button("تسجيل خروج"): logout()
    st.divider()
    
    # تحديد القوائم بناء على الصلاحية
    if st.session_state.role == "Admin":
        pages = ["لوحة القيادة (BI)", "نقطة البيع (POS)", "المخزون والمنتجات", "الموردين والمشتريات", "العملاء", "المالية والمصاريف"]
        icons = ["graph-up", "cart4", "box-seam", "truck", "people", "wallet2"]
    else:
        pages = ["نقطة البيع (POS)", "العملاء"]
        icons = ["cart4", "people"]

    # استيراد القائمة (تأكد من تثبيت streamlit-option-menu)
    from streamlit_option_menu import option_menu
    selected = option_menu("القائمة الرئيسية", pages, icons=icons, menu_icon="cast", default_index=1)

# ==========================================
# 🛒 نقطة البيع (POS) - مطورة مع باركود
# ==========================================
if selected == "نقطة البيع (POS)":
    c1, c2 = st.columns([2, 1.2])
    
    with c1:
        st.subheader("🛒 عملية البيع")
        # 1. البحث بالباركود (الأولوية)
        barcode = st.text_input("📷 مسح الباركود (Scan)", key="barcode_input",  help="ضع المؤشر هنا واستخدم قارئ الباركود")
        
        # منطق الباركود
        if barcode:
            df = db.run_query("SELECT * FROM variants WHERE barcode = %s", (barcode,))
            if df is not None and not df.empty:
                item = df.iloc[0]
                if item['stock'] > 0:
                    # إضافة للسلة مباشرة
                    existing = next((x for x in st.session_state.cart if x['id'] == item['id']), None)
                    if existing:
                        existing['qty'] += 1
                        existing['total'] = existing['qty'] * existing['price']
                    else:
                        st.session_state.cart.append({
                            "id": int(item['id']), "name": item['name'], "price": float(item['price']),
                            "cost": float(item['cost']), "qty": 1, "total": float(item['price'])
                        })
                    st.toast(f"تمت إضافة: {item['name']}", icon="✅")
                    # تفريغ الحقل (يحتاج خدعة بسيطة في ستريم ليت، هنا نعتمد على إعادة التحميل)
                else:
                    st.error("نفذت الكمية!")
            else:
                st.warning("منتج غير موجود")
        
        # 2. البحث اليدوي (للطوارئ)
        st.markdown("---")
        df_inv = db.run_query("SELECT * FROM variants WHERE stock > 0 ORDER BY name")
        if not df_inv.empty:
            sel_manual = st.selectbox("بحث يدوي", df_inv['name'] + " | " + df_inv['color'], index=None)
            if sel_manual:
                # منطق مشابه للإضافة اليدوية...
                pass # (اختصاراً للكود، نفس منطق الباركود)

    with c2:
        st.subheader("🧾 الفاتورة")
        if st.session_state.cart:
            total_gross = sum(x['total'] for x in st.session_state.cart)
            
            for i, item in enumerate(st.session_state.cart):
                col_n, col_q, col_d = st.columns([3, 1, 1])
                col_n.text(f"{item['name']}")
                new_qty = col_q.number_input("العدد", 1, 100, item['qty'], key=f"q_{i}", label_visibility="collapsed")
                item['qty'] = new_qty
                item['total'] = new_qty * item['price']
                if col_d.button("x", key=f"d_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            st.divider()
            discount = st.number_input("خصم (مبلغ)", 0.0, total_gross, 0.0)
            final_total = total_gross - discount
            
            st.markdown(f"<h2 style='text-align:center; color:#D48896'>{final_total:,.0f} IQD</h2>", unsafe_allow_html=True)
            
            if st.button("✅ إتمام البيع (F10)", type="primary", use_container_width=True):
                # حفظ الفاتورة (Transaction)
                conn = db.get_conn()
                try:
                    with conn.cursor() as cur:
                        inv_id = get_time().strftime("%Y%m%d%H%M")
                        # رأس الفاتورة
                        cur.execute("""INSERT INTO sales (invoice_id, total_amount, discount, final_amount, date, created_by) 
                                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""", 
                                       (inv_id, total_gross, discount, final_total, get_time(), st.session_state.role))
                        sale_id = cur.fetchone()[0]
                        
                        # تفاصيل الفاتورة وتحديث المخزون
                        for it in st.session_state.cart:
                            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (it['qty'], it['id']))
                            cur.execute("""INSERT INTO sale_items (sale_id, variant_id, product_name, qty, unit_cost, unit_price, total)
                                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                           (sale_id, it['id'], it['name'], it['qty'], it['cost'], it['price'], it['total']))
                        
                        conn.commit()
                        st.session_state.cart = []
                        st.success(f"تم البيع! فاتورة #{inv_id}")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"خطأ: {e}")
        else:
            st.info("السلة فارغة")

# ==========================================
# 📦 المخزون والمنتجات (إدارة متقدمة)
# ==========================================
elif selected == "المخزون والمنتجات" and st.session_state.role == "Admin":
    st.title("📦 إدارة المخزون")
    
    tab1, tab2 = st.tabs(["تعديل سريع (Excel)", "إضافة صنف جديد"])
    
    with tab1:
        df = db.run_query("SELECT id, barcode, name, color, stock, cost, price FROM variants ORDER BY id")
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="inv_edit")
        
        if st.button("💾 حفظ التغييرات للمخزون"):
            # منطق تحديث ذكي (يمكن تحسينه للتعامل مع الفروقات فقط)
            conn = db.get_conn()
            with conn.cursor() as cur:
                for i, row in edited.iterrows():
                    if pd.notna(row['id']): # تحديث
                        cur.execute("UPDATE variants SET barcode=%s, name=%s, color=%s, stock=%s, cost=%s, price=%s WHERE id=%s",
                                    (row['barcode'], row['name'], row['color'], row['stock'], row['cost'], row['price'], row['id']))
                    elif row['name']: # إضافة جديد
                        cur.execute("INSERT INTO variants (barcode, name, color, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)",
                                    (row['barcode'], row['name'], row['color'], row['stock'], row['cost'], row['price']))
                conn.commit()
            st.success("تم التحديث!")
            st.rerun()

# ==========================================
# 📊 لوحة القيادة (Business Intelligence)
# ==========================================
elif selected == "لوحة القيادة (BI)" and st.session_state.role == "Admin":
    st.title("📈 التحليل المالي والتشغيلي")
    
    # جلب البيانات المعقدة
    df_sales = db.run_query("SELECT * FROM sales")
    df_items = db.run_query("SELECT * FROM sale_items")
    df_exp = db.run_query("SELECT * FROM expenses")
    
    if not df_sales.empty:
        # حسابات الأرباح والخسائر (P&L)
        total_revenue = df_sales['final_amount'].sum()
        
        # حساب تكلفة البضاعة المباعة COGS
        total_cogs = (df_items['unit_cost'] * df_items['qty']).sum() if not df_items.empty else 0
        
        total_expenses = df_exp['amount'].sum() if not df_exp.empty else 0
        
        gross_profit = total_revenue - total_cogs
        net_profit = gross_profit - total_expenses
        
        # عرض المؤشرات
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("إجمالي المبيعات", f"{total_revenue:,.0f}", delta="إيراد")
        col2.metric("تكلفة البضاعة (COGS)", f"{total_cogs:,.0f}", delta="تكلفة مباشرة", delta_color="inverse")
        col3.metric("المصاريف التشغيلية", f"{total_expenses:,.0f}", delta="رواتب/إيجار", delta_color="inverse")
        col4.metric("صافي الربح (Net Profit)", f"{net_profit:,.0f}", delta="الربح النهائي")
        
        st.markdown("---")
        
        # الرسوم البيانية
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("أداء المبيعات اليومي")
            df_sales['date'] = pd.to_datetime(df_sales['date'])
            daily = df_sales.groupby(df_sales['date'].dt.date)['final_amount'].sum().reset_index()
            fig = px.bar(daily, x='date', y='final_amount', color_discrete_sequence=['#D48896'])
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("توزيع المصاريف")
            if not df_exp.empty:
                fig2 = px.pie(df_exp, values='amount', names='category', hole=0.5)
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("لا توجد بيانات كافية للتحليل")

# ==========================================
# 🚚 الموردين (جديد)
# ==========================================
elif selected == "الموردين والمشتريات":
    st.title("🚚 إدارة الموردين")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("new_supplier"):
            st.write("إضافة مورد جديد")
            name = st.text_input("اسم المورد / الشركة")
            phone = st.text_input("رقم الهاتف")
            if st.form_submit_button("حفظ"):
                db.run_query("INSERT INTO suppliers (name, phone) VALUES (%s, %s)", (name, phone), commit=True, fetch=False)
                st.success("تم")
    
    with c2:
        st.write("قائمة الموردين")
        st.dataframe(db.run_query("SELECT * FROM suppliers"), use_container_width=True)

# ==========================================
# 💸 المالية (المصاريف)
# ==========================================
elif selected == "المالية والمصاريف":
    st.title("💸 المصاريف التشغيلية")
    with st.form("add_exp"):
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("البند", ["رواتب", "إيجار", "كهرباء/انترنت", "نثرية", "تسويق"])
        amt = c2.number_input("المبلغ", min_value=0.0)
        note = c3.text_input("ملاحظة")
        if st.form_submit_button("تسجيل مصروف"):
            db.run_query("INSERT INTO expenses (category, amount, note, date) VALUES (%s,%s,%s,%s)", 
                         (cat, amt, note, get_time()), commit=True, fetch=False)
            st.success("تم التسجيل")
    
    st.divider()
    st.dataframe(db.run_query("SELECT * FROM expenses ORDER BY date DESC"), use_container_width=True)
