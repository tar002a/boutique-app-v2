import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة (Mobile Friendly) ---
st.set_page_config(page_title="Nawaem Mobile Pro", layout="wide", page_icon="📱", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .stButton button {
        width: 100%;
        height: 50px;
        font-size: 16px !important;
        font-weight: bold;
        border-radius: 12px;
    }
    .block-container {padding-top: 1rem; padding-left: 0.5rem; padding-right: 0.5rem;}
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. قاعدة البيانات ---
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
    conn.commit()
    return conn

conn = init_db()

# --- 3. النوافذ المنبثقة (Dialogs) ---

# أ) نافذة تعديل عملية بيع
@st.dialog("تعديل عملية بيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"تعديل فاتورة: {product_name}")
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("السعر الإجمالي", value=float(current_total))
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ التعديل", type="primary"):
            cur = conn.cursor()
            diff = new_qty - int(current_qty)
            if diff != 0: # تعديل المخزون بناء على الفرق
                cur.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (diff, variant_id))
            cur.execute("UPDATE sales SET qty = ?, total = ? WHERE id = ?", (new_qty, new_total, sale_id))
            conn.commit()
            st.success("تم الحفظ"); st.rerun()
    with c2:
        if st.button("🗑️ حذف البيعة"):
            cur = conn.cursor()
            cur.execute("UPDATE variants SET stock = stock + ? WHERE id = ?", (int(current_qty), variant_id))
            cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            conn.commit()
            st.rerun()

# ب) نافذة تعديل المخزون (القطعة) - الميزة الجديدة
@st.dialog("تعديل بيانات المنتج")
def edit_stock_dialog(item_id, name, color, size, cost, price, stock):
    st.caption("يمكنك تعديل الاسم، اللون، القياس، أو السعر والكمية")
    
    with st.form("edit_stock_form"):
        new_name = st.text_input("اسم الموديل", value=name)
        c1, c2 = st.columns(2)
        new_color = c1.text_input("اللون", value=color)
        new_size = c2.text_input("القياس", value=size)
        
        c3, c4, c5 = st.columns(3)
        new_cost = c3.number_input("التكلفة", value=float(cost))
        new_price = c4.number_input("سعر البيع", value=float(price))
        new_stock = c5.number_input("المخزون", value=int(stock))
        
        save = st.form_submit_button("💾 حفظ التغييرات")
        if save:
            cur = conn.cursor()
            cur.execute("""
                UPDATE variants 
                SET name=?, color=?, size=?, cost=?, price=?, stock=? 
                WHERE id=?
            """, (new_name, new_color, new_size, new_cost, new_price, new_stock, item_id))
            conn.commit()
            st.success("تم تحديث بيانات المنتج!"); st.rerun()

    st.markdown("---")
    if st.button("🗑️ حذف هذا الصنف نهائياً"):
        cur = conn.cursor()
        cur.execute("DELETE FROM variants WHERE id = ?", (item_id,))
        conn.commit()
        st.error("تم حذف الصنف من المخزون"); st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    st.title("📱 بوتيك نواعم")
    password = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if password == "1234":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("خطأ")

# --- 5. التطبيق الرئيسي ---
def main_app():
    st.markdown("### 🛍️ نظام الإدارة")
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "📦 مخزن", "🏠 تقرير"])

    # === 1: نقطة البيع ===
    with tabs[0]:
        with st.container(border=True):
            df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
            search = st.text_input("🔍 بحث للبيع...", label_visibility="collapsed", placeholder="بحث...")
            if search:
                mask = df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)
                df = df[mask]
            
            if not df.empty:
                opts = df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1).tolist()
                sel = st.selectbox("اختر:", opts, label_visibility="collapsed")
                if sel:
                    row = df[df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1) == sel].iloc[0]
                    st.info(f"سعر: {row['price']:,.0f} | متوفر: {row['stock']}")
                    c1, c2 = st.columns(2)
                    qty = c1.number_input("العدد", 1, int(row['stock']), 1)
                    price = c2.number_input("السعر", value=float(row['price']))
                    if st.button("إضافة للسلة ➕", type="primary"):
                        st.session_state.cart.append({
                            "id": int(row['id']), "name": row['name'], "color": row['color'],
                            "size": row['size'], "cost": row['cost'], "price": price,
                            "qty": qty, "total": price * qty
                        })
                        st.toast("أضيف للسلة", icon="✅")

        if st.session_state.cart:
            st.divider()
            total = 0
            for idx, item in enumerate(st.session_state.cart):
                with st.container(border=True):
                    c_del, c_txt = st.columns([1, 4])
                    if c_del.button("❌", key=f"d{idx}"):
                        st.session_state.cart.pop(idx); st.rerun()
                    c_txt.caption(f"{item['name']} ({item['color']}) x{item['qty']} = {item['total']:,.0f}")
                    total += item['total']
            
            st.metric("الإجمالي", f"{total:,.0f}")
            
            with st.expander("إتمام البيع", expanded=True):
                cust_type = st.radio("", ["سابق", "جديد"], horizontal=True)
                cid, cname = None, ""
                if cust_type == "سابق":
                    c_df = pd.read_sql("SELECT id, name FROM customers", conn)
                    if not c_df.empty:
                        cname = st.selectbox("اختر:", c_df['name'].tolist())
                        cid = c_df[c_df['name']==cname]['id'].iloc[0]
                else:
                    cname = st.text_input("الاسم")
                    cph = st.text_input("هاتف")
                    cadd = st.text_input("عنوان")
                
                if st.button("✅ بيع الآن"):
                    if not cname: st.error("الاسم مطلوب"); st.stop()
                    cur = conn.cursor()
                    if cust_type=="جديد":
                        cur.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (cname, cph, cadd))
                        cid = cur.lastrowid
                    inv = datetime.now().strftime("%Y%m%d%H%M")
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    for it in st.session_state.cart:
                        cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (it['qty'], it['id']))
                        prof = (it['price']-it['cost'])*it['qty']
                        cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?,?)",
                                    (cid, it['id'], it['name'], it['qty'], it['total'], prof, dt, inv))
                    conn.commit()
                    st.session_state.cart=[]
                    st.success("تم البيع!"); st.rerun()

    # === 2: سجل العمليات ===
    with tabs[1]:
        df_s = pd.read_sql("SELECT s.*, c.name as cn FROM sales s LEFT JOIN customers c ON s.customer_id=c.id ORDER BY s.id DESC LIMIT 30", conn)
        for i, r in df_s.iterrows():
            with st.container(border=True):
                ca, cb = st.columns([3,1])
                ca.markdown(f"**{r['product_name']}** | {r['total']:,.0f}")
                ca.caption(f"{r['cn']} | {r['date']}")
                if cb.button("⚙️", key=f"ed{r['id']}"):
                    edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])

    # === 3: المخزون (تم التعديل للحذف والتعديل) ===
    with tabs[2]:
        # إضافة جديد
        with st.expander("➕ إضافة صنف جديد"):
            with st.form("new_st"):
                nm = st.text_input("اسم")
                clrs = st.text_input("ألوان (،)")
                szs = st.text_input("قياسات (،)")
                stk = st.number_input("عدد", 1)
                cst = st.number_input("كلفة", 0.0)
                prc = st.number_input("بيع", 0.0)
                if st.form_submit_button("توليد وحفظ"):
                    clist = [x.strip() for x in clrs.replace('،',',').split(',') if x.strip()]
                    slist = [x.strip() for x in szs.replace('،',',').split(',') if x.strip()]
                    cur = conn.cursor()
                    for c in clist:
                        for s in slist:
                            cur.execute("INSERT INTO variants (name,color,size,cost,price,stock) VALUES (?,?,?,?,?,?)", (nm,c,s,cst,prc,stk))
                    conn.commit(); st.success("تم!"); st.rerun()
        
        st.divider()
        # بحث وعرض للتعديل
        st.caption("اضغط ⚙️ لتعديل أو حذف أي قطعة")
        search_st = st.text_input("بحث في المخزون...", placeholder="اسم، لون...")
        
        query = "SELECT * FROM variants"
        df_inv = pd.read_sql(query, conn)
        
        if search_st:
            mask = df_inv['name'].str.contains(search_st, case=False) | df_inv['color'].str.contains(search_st, case=False)
            df_inv = df_inv[mask]
            
        # عرض المخزون كروت
        for i, row in df_inv.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"{row['color']} | {row['size']}")
                with c2:
                    st.markdown(f"العدد: **{row['stock']}**")
                    st.caption(f"{row['price']:,.0f} د.ع")
                with c3:
                    # زر التعديل
                    if st.button("⚙️", key=f"inv_{row['id']}"):
                        edit_stock_dialog(row['id'], row['name'], row['color'], row['size'], row['cost'], row['price'], row['stock'])

    # === 4: تقرير ===
    with tabs[3]:
        dt = datetime.now().strftime("%Y-%m-%d")
        res = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{dt}%'", conn).iloc[0]
        st.metric("مبيعات اليوم", f"{res[0] or 0:,.0f}")
        st.metric("أرباح اليوم", f"{res[1] or 0:,.0f}")
        if st.button("خروج"):
            st.session_state.logged_in=False; st.rerun()

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
