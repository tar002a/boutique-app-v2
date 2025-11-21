import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import pytz
import io # للمساعدة في تحميل الملفات

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem Ultimate", layout="wide", page_icon="💎", initial_sidebar_state="expanded")

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .stButton button {
        width: 100%;
        height: 45px;
        border-radius: 10px;
        font-weight: bold;
    }
    /* تمييز القطع التي أوشكت على النفاذ */
    .low-stock {
        color: #d32f2f;
        font-weight: bold;
        border: 1px solid #d32f2f;
        padding: 2px 5px;
        border-radius: 5px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'sale_success' not in st.session_state: st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state: st.session_state.last_invoice_text = ""

# --- قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, username TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
        qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
    )""")
    # جدول جديد للمصاريف
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, amount REAL, date TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- النوافذ المنبثقة ---
@st.dialog("تعديل عملية بيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"تعديل فاتورة: {product_name}")
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("الإجمالي", value=float(current_total))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ التعديل", type="primary"):
            cur = conn.cursor()
            diff = new_qty - int(current_qty)
            if diff != 0: cur.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (diff, variant_id))
            cur.execute("UPDATE sales SET qty = ?, total = ? WHERE id = ?", (new_qty, new_total, sale_id))
            conn.commit(); st.rerun()
    with c2:
        if st.button("🗑️ حذف البيعة"):
            cur = conn.cursor()
            cur.execute("UPDATE variants SET stock = stock + ? WHERE id = ?", (int(current_qty), variant_id))
            cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            conn.commit(); st.rerun()

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
        if st.form_submit_button("💾 حفظ"):
            conn.execute("UPDATE variants SET name=?, color=?, size=?, cost=?, price=?, stock=? WHERE id=?", 
                         (n_name, n_col, n_siz, n_cst, n_prc, n_stk, item_id))
            conn.commit(); st.rerun()
    if st.button("🗑️ حذف نهائي"):
        conn.execute("DELETE FROM variants WHERE id=?", (item_id,))
        conn.commit(); st.rerun()

# --- تسجيل الدخول ---
def login_screen():
    st.title("💎 نواعم بوتيك - النظام المتكامل")
    if st.button("دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

# --- التطبيق الرئيسي ---
def main_app():
    # === القائمة الجانبية (Backup) ===
    with st.sidebar:
        st.header("نسخ احتياطي 💾")
        st.info("احفظ بياناتك دائماً!")
        
        # تصدير المبيعات
        df_sales_export = pd.read_sql("SELECT * FROM sales", conn)
        csv_sales = df_sales_export.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 تحميل سجل المبيعات (Excel)", data=csv_sales, file_name="sales_backup.csv", mime="text/csv")
        
        # تصدير المخزون
        df_stock_export = pd.read_sql("SELECT * FROM variants", conn)
        csv_stock = df_stock_export.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 تحميل جرد المخزون (Excel)", data=csv_stock, file_name="stock_backup.csv", mime="text/csv")

    tabs = st.tabs(["🛒 بيع", "📋 سجل", "💸 مصاريف", "👥 عملاء", "📦 مخزن", "📊 تقارير"])

    # === 1. البيع ===
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم الحجز بنجاح!")
            st.balloons()
            st.code(st.session_state.last_invoice_text, language="text")
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False; st.session_state.last_invoice_text = ""; st.rerun()
        else:
            with st.container(border=True):
                df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
                srch = st.text_input("🔍 بحث سريع...", label_visibility="collapsed")
                if srch:
                    mask = df['name'].str.contains(srch, case=False) | df['color'].str.contains(srch, case=False)
                    df = df[mask]
                if not df.empty:
                    opts = df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1).tolist()
                    sel = st.selectbox("اختر:", opts, label_visibility="collapsed")
                    if sel:
                        r = df[df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1) == sel].iloc[0]
                        st.caption(f"سعر: {r['price']:,.0f} | متوفر: {r['stock']}")
                        c1, c2 = st.columns(2)
                        q = c1.number_input("العدد", 1, int(r['stock']), 1)
                        p = c2.number_input("سعر", value=float(r['price']))
                        if st.button("أضف للسلة ➕", type="secondary"):
                            st.session_state.cart.append({"id": int(r['id']), "name": r['name'], "color": r['color'], "size": r['size'], "cost": r['cost'], "price": p, "qty": q, "total": p*q})
                            st.toast("تم!", icon="✅")

            if st.session_state.cart:
                st.divider()
                st.markdown("##### بيانات العميل")
                with st.container(border=True):
                    cust_type = st.radio("نوع العميل", ["جديد", "سابق"], horizontal=True)
                    cust_id_val, cust_name_val = None, ""
                    if cust_type == "سابق":
                        curr_custs = pd.read_sql("SELECT id, name, phone FROM customers", conn)
                        if not curr_custs.empty:
                            c_sel = st.selectbox("الاسم:", curr_custs.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist())
                            cust_name_val = c_sel.split(" - ")[0]
                            cust_id_val = curr_custs[curr_custs['name'] == cust_name_val]['id'].iloc[0]
                        else: st.warning("لا يوجد")
                    else:
                        c_n = st.text_input("الاسم"); c_p = st.text_input("الهاتف"); c_a = st.text_input("العنوان")
                        cust_name_val = c_n
                
                tot = 0; invoice_msg = "تم حجز الطلب ✅\n"
                for x in st.session_state.cart:
                    tot += x['total']
                    invoice_msg += f"{x['name']}\n{x['color']}\n{x['size']}\n"
                    if len(st.session_state.cart) > 1: invoice_msg += "---\n"
                invoice_msg += f"{tot:,.0f}\nالتوصيل مجاني\nالف عافية حياتي 🌸🌸🌸🌸"
                st.markdown(f"**الإجمالي: {tot:,.0f} د.ع**")

                if st.button("✅ إتمام ونسخ", type="primary"):
                    if not cust_name_val: st.error("مطلوب اسم العميل"); st.stop()
                    cur = conn.cursor()
                    if cust_type == "جديد":
                        cur.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (c_n, c_p, c_a))
                        cust_id_val = cur.lastrowid
                    baghdad_now = get_baghdad_time()
                    inv = baghdad_now.strftime("%Y%m%d%H%M")
                    dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
                    for x in st.session_state.cart:
                        cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (x['qty'], x['id']))
                        prf = (x['price']-x['cost'])*x['qty']
                        cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?,?)", (cust_id_val, x['id'], x['name'], x['qty'], x['total'], prf, dt, inv))
                    conn.commit(); st.session_state.cart = []; st.session_state.sale_success = True; st.session_state.last_invoice_text = invoice_msg; st.rerun()

    # === 2. السجل ===
    with tabs[1]:
        st.caption("سجل المبيعات")
        df_s = pd.read_sql("SELECT s.*, c.name as customer_name FROM sales s LEFT JOIN customers c ON s.customer_id = c.id ORDER BY s.id DESC LIMIT 30", conn)
        for i, r in df_s.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4,1])
                c_name = r['customer_name'] if r['customer_name'] else "غير مسجل"
                c1.markdown(f"**{r['product_name']}** ({r['qty']})")
                c1.caption(f"👤 {c_name} | 💰 {r['total']:,.0f}")
                if c2.button("⚙️", key=f"e{r['id']}"): edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])

    # === 3. المصاريف (جديد) ===
    with tabs[2]:
        st.header("💸 تسجيل المصروفات")
        with st.form("exp_form"):
            c_ex1, c_ex2 = st.columns(2)
            desc = c_ex1.text_input("بند الصرف (مثلاً: انترنت، أكياس)")
            amount = c_ex2.number_input("المبلغ", min_value=0.0, step=1000.0)
            if st.form_submit_button("تسجيل مصروف"):
                dt = get_baghdad_time().strftime("%Y-%m-%d %H:%M")
                conn.execute("INSERT INTO expenses (description, amount, date) VALUES (?,?,?)", (desc, amount, dt))
                conn.commit(); st.success("تم التسجيل"); st.rerun()
        
        st.divider()
        st.subheader("سجل المصاريف")
        df_exp = pd.read_sql("SELECT * FROM expenses ORDER BY id DESC LIMIT 20", conn)
        if not df_exp.empty: st.dataframe(df_exp, use_container_width=True)
        else: st.info("لا توجد مصاريف مسجلة")

    # === 4. العملاء ===
    with tabs[3]:
        df_cust = pd.read_sql("SELECT * FROM customers ORDER BY id DESC", conn)
        if not df_cust.empty: st.dataframe(df_cust, use_container_width=True)
        else: st.info("فارغ")

    # === 5. المخزون (تنبيهات النواقص) ===
    with tabs[4]:
        with st.expander("➕ إضافة بضاعة"):
            with st.form("add"):
                nm = st.text_input("اسم"); cl = st.text_input("ألوان (،)"); sz = st.text_input("قياسات (،)")
                stk = st.number_input("عدد", 1); pr = st.number_input("بيع", 0.0); cst = st.number_input("كلفة", 0.0)
                if st.form_submit_button("توليد"):
                    for c in cl.replace('،',',').split(','):
                        for s in sz.replace('،',',').split(','):
                            if c.strip() and s.strip(): conn.execute("INSERT INTO variants (name,color,size,stock,price,cost) VALUES (?,?,?,?,?,?)", (nm, c.strip(), s.strip(), stk, pr, cst))
                    conn.commit(); st.rerun()
        st.divider()
        
        df_inv = pd.read_sql("SELECT * FROM variants WHERE stock > 0 ORDER BY name", conn)
        if not df_inv.empty:
            for p in df_inv['name'].unique():
                with st.container(border=True):
                    pdf = df_inv[df_inv['name']==p]
                    st.markdown(f"#### 👗 {p}")
                    for c in pdf['color'].unique():
                        # منطق تمييز المخزون المنخفض
                        items = []
                        for _,r in pdf[pdf['color']==c].iterrows():
                            stock_num = r['stock']
                            # إذا المخزون أقل من 3 نلونه بالأحمر
                            style_class = "color: red; font-weight: bold;" if stock_num < 3 else ""
                            icon = "⚠️" if stock_num < 3 else ""
                            items.append(f"<span style='{style_class}'>{r['size']} ({stock_num}) {icon}</span>")
                        
                        szs = " | ".join(items)
                        st.markdown(f"🎨 **{c}:** {szs}", unsafe_allow_html=True)
                    
                    with st.expander("تعديل"):
                        for _,r in pdf.iterrows():
                            if st.button(f"{r['color']} {r['size']}", key=f"bx{r['id']}"): edit_stock_dialog(r['id'], r['name'], r['color'], r['size'], r['cost'], r['price'], r['stock'])

    # === 6. التقارير (الصافي الحقيقي) ===
    with tabs[5]:
        st.header("📊 الأداء المالي")
        today_baghdad = get_baghdad_time().strftime("%Y-%m-%d")
        
        # المبيعات والأرباح التشغيلية
        sales_data = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{today_baghdad}%'", conn).iloc[0]
        total_sales = sales_data[0] or 0
        gross_profit = sales_data[1] or 0
        
        # المصاريف
        exp_data = pd.read_sql(f"SELECT SUM(amount) FROM expenses WHERE date LIKE '{today_baghdad}%'", conn).iloc[0]
        total_exp = exp_data[0] or 0
        
        # الصافي الحقيقي
        net_profit = gross_profit - total_exp
        
        c1, c2, c3 = st.columns(3)
        c1.metric("مبيعات اليوم", f"{total_sales:,.0f}")
        c2.metric("مصاريف اليوم", f"{total_exp:,.0f}", delta_color="inverse")
        c3.metric("الربح الصافي (الحقيقي)", f"{net_profit:,.0f}", delta="الخلاصة")
        
        st.caption("* الربح الصافي = (المبيعات - تكلفة البضاعة) - المصاريف (إيجار، انترنت..)")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
