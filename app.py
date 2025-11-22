import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
import itertools # مكتبة مهمة لتوليد الاحتمالات (ألوان x مقاسات)

# --- 1. إعداد الصفحة ---
st.set_page_config(
    page_title="نواعم بوتيك", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="collapsed"
)

# --- 2. CSS مخصص (تحسينات بصرية) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    
    * {font-family: 'Cairo', sans-serif !important;}
    .stApp {direction: rtl; background-color: #f4f6f9;}

    /* إخفاء القائمة الجانبية */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    
    /* شريط التنقل العلوي */
    div[role="radiogroup"] {
        flex-direction: row-reverse;
        background: white;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        justify-content: space-between;
        display: flex;
        width: 100%;
        overflow-x: auto;
    }
    
    /* تنسيق أزرار التنقل */
    div[role="radiogroup"] label {
        background: transparent !important;
        border: none !important;
        color: #666 !important;
        font-weight: 600 !important;
        transition: 0.3s;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
    }
    div[role="radiogroup"] label[aria-checked="true"] {
        color: #e91e63 !important;
        border-bottom: 3px solid #e91e63 !important;
    }

    /* تنسيق البطاقات والحاويات */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        padding: 20px;
        border: 1px solid #f0f0f0;
    }

    /* الأزرار */
    .stButton button {
        border-radius: 10px; font-weight: bold; height: 45px;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(45deg, #e91e63, #c2185b); 
        border: none; box-shadow: 0 4px 10px rgba(233, 30, 99, 0.3);
    }
    
    /* تحسينات الجداول */
    div[data-testid="stDataFrame"] {direction: rtl;}

    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. دوال قاعدة البيانات ---
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception:
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

# --- 4. الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'auth' not in st.session_state: st.session_state.auth = False

# --- 5. شاشات التطبيق ---

def login_ui():
    c1, c2, c3 = st.columns([1, 5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #e91e63;'>🌸 نواعم بوتيك</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            pwd = st.text_input("🔑 الرمز السري", type="password")
            if st.button("دخول", type="primary"):
                if pwd == st.secrets.get("ADMIN_PASS", "admin"):
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.toast("الرمز خطأ", icon="❌")

# دالة البيع (نفس المنطق السابق)
def process_sale(customer_name):
    conn = init_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        dt = datetime.now(pytz.timezone('Asia/Baghdad'))
        inv_id = dt.strftime("%Y%m%d%H%M")
        
        cur.execute("SELECT id FROM customers WHERE name = %s", (customer_name,))
        res = cur.fetchone()
        if res: cust_id = res[0]
        else:
            cur.execute("INSERT INTO customers (name) VALUES (%s) RETURNING id", (customer_name,))
            cust_id = cur.fetchone()[0]
        
        for item in st.session_state.cart:
            cur.execute("SELECT stock FROM variants WHERE id = %s FOR UPDATE", (item['id'],))
            if cur.fetchone()[0] < item['qty']: raise Exception(f"نفذت الكمية: {item['name']}")
            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
            profit = (item['price'] - item['cost']) * item['qty']
            cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
        conn.commit(); cur.close(); return True
    except Exception as e:
        conn.rollback(); st.toast(f"خطأ: {e}", icon="⚠️"); return False

def main_app():
    # Header
    col_t1, col_t2 = st.columns([6, 1])
    col_t1.markdown("### 🌸 بوتيك نواعم")
    if col_t2.button("خروج"): st.session_state.auth = False; st.rerun()

    # NavBar
    selected = st.radio("menu", ["نقطة البيع 🛒", "المخزون 📦", "التقارير 📊", "الفواتير 🧾"], horizontal=True, label_visibility="collapsed")
    st.markdown("---")

    # ==========================
    # 1. نقطة البيع (نفس السابق)
    # ==========================
    if "نقطة البيع" in selected:
        t1, t2 = st.tabs(["🛍️ المنتجات", f"🛒 السلة ({len(st.session_state.cart)})"])
        with t1:
            s_term = st.text_input("بحث...", label_visibility="collapsed", placeholder="اسم المنتج أو اللون...")
            q = "SELECT * FROM variants WHERE is_active = TRUE AND stock > 0"
            p = []
            if s_term:
                q += " AND (name ILIKE %s OR color ILIKE %s)"
                p = [f"%{s_term}%", f"%{s_term}%"]
            q += " ORDER BY name ASC, id DESC LIMIT 30"
            
            items = run_query(q, tuple(p), fetch_data=True)
            if items is not None and not items.empty:
                cols = st.columns(2)
                for i, row in items.iterrows():
                    with cols[i % 2]:
                        with st.container(border=True):
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['color']} | {row['size']} | {int(row['price']):,} د.ع")
                            c_q, c_b = st.columns([1, 2])
                            qty = c_q.number_input("عدد", 1, max_value=row['stock'], key=f"q_{row['id']}", label_visibility="collapsed")
                            if c_b.button("أضف", key=f"b_{row['id']}"):
                                found = False
                                for x in st.session_state.cart:
                                    if x['id'] == row['id']:
                                        x['qty'] += qty; x['total'] += qty*row['price']; found=True; break
                                if not found: st.session_state.cart.append({"id":row['id'], "name":row['name'], "price":row['price'], "qty":qty, "total":qty*row['price'], "cost":row['cost']})
                                st.toast("تمت الإضافة", icon="✅"); st.rerun()
            else: st.info("لا توجد منتجات")

        with t2:
            if st.session_state.cart:
                for i, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"{item['name']} (x{item['qty']})"); c1.caption(f"{item['total']:,.0f}")
                        if c2.button("❌", key=f"d_{i}"): st.session_state.cart.pop(i); st.rerun()
                st.success(f"المجموع: {sum(x['total'] for x in st.session_state.cart):,.0f} د.ع")
                c_n = st.text_input("العميل")
                if st.button("✅ إتمام", type="primary", use_container_width=True):
                    if c_n and process_sale(c_n): st.session_state.cart = []; st.balloons(); st.rerun()
            else: st.info("السلة فارغة")

    # ==============================================
    # 2. المخزون (تحديث جذري - المولد السريع)
    # ==============================================
    elif "المخزون" in selected:
        
        # --- الجزء الأول: إضافة سريعة (Bulk Add) ---
        with st.expander("➕ إضافة بضاعة جديدة (مولد سريع)", expanded=False):
            st.markdown("##### بيانات المنتج الأساسية")
            c_main1, c_main2 = st.columns(2)
            prod_name = c_main1.text_input("اسم المنتج (مثال: فستان سهرة)")
            
            # خيارات الألوان والمقاسات الجاهزة
            colors_list = ["أحمر", "أسود", "أبيض", "أزرق", "أخضر", "بيج", "وردي", "رصاصي", "ذهبي", "فضي"]
            sizes_list = ["S", "M", "L", "XL", "XXL", "36", "38", "40", "42", "44", "Free Size"]
            
            selected_colors = st.multiselect("🎨 اختر الألوان المتوفرة", colors_list)
            selected_sizes = st.multiselect("📏 اختر القياسات المتوفرة", sizes_list)
            
            st.markdown("##### تفاصيل السعر والعدد")
            c_num1, c_num2, c_num3 = st.columns(3)
            base_cost = c_num1.number_input("سعر التكلفة (شراء)", 0.0, step=1000.0)
            base_price = c_num2.number_input("سعر البيع", 0.0, step=1000.0)
            base_qty = c_num3.number_input("العدد لكل قطعة", 1, step=1)
            
            # زر التوليد والحفظ
            if st.button("🚀 توليد وإضافة للمخزون", type="primary"):
                if not prod_name or not selected_colors or not selected_sizes:
                    st.error("يرجى إدخال الاسم واختيار لون واحد ومقاس واحد على الأقل")
                else:
                    # توليد جميع الاحتمالات (Cross Product)
                    combinations = list(itertools.product(selected_colors, selected_sizes))
                    conn = init_connection()
                    cur = conn.cursor()
                    try:
                        count = 0
                        for color, size in combinations:
                            cur.execute("""
                                INSERT INTO variants (name, color, size, stock, cost, price, is_active)
                                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                            """, (prod_name, color, size, base_qty, base_cost, base_price))
                            count += 1
                        conn.commit()
                        st.toast(f"تم إضافة {count} صنف جديد بنجاح!", icon="🎉")
                        # تفريغ الحقول بإعادة التحميل (اختياري)
                        st.rerun()
                    except Exception as e:
                        st.error(f"حدث خطأ: {e}")
                        conn.rollback()
                    finally:
                        cur.close()

        st.divider()
        
        # --- الجزء الثاني: عرض المخزون الذكي ---
        st.markdown("### 📦 جرد المخزون")
        
        # بحث وفلترة
        search_inv = st.text_input("🔍 بحث في المخزون", placeholder="ابحث عن اسم، لون، أو مقاس...")
        
        # الاستعلام الذكي: يعرض المتوفر أولاً (stock > 0)
        # ثم يرتب حسب الاسم
        query_inv = """
            SELECT id, name, color, size, stock, price, cost, is_active 
            FROM variants 
        """
        params_inv = []
        
        if search_inv:
            query_inv += " WHERE name ILIKE %s OR color ILIKE %s OR size ILIKE %s"
            params_inv = [f"%{search_inv}%", f"%{search_inv}%", f"%{search_inv}%"]
            
        # الترتيب: المخزون الأكبر من صفر أولاً، ثم الاسم
        query_inv += " ORDER BY (stock > 0) DESC, name ASC, id DESC"
        
        df_inv = run_query(query_inv, tuple(params_inv), fetch_data=True)
        
        if df_inv is not None:
            # تلوين الصفوف (في Streamlit data_editor التلوين محدود، لذا سنعتمد على الترتيب)
            # لكن يمكننا استبدال الجدول بـ data_editor للتعديل المباشر
            
            edited_df = st.data_editor(
                df_inv,
                column_config={
                    "id": None, # إخفاء المعرف
                    "name": "المنتج",
                    "color": "اللون",
                    "size": st.column_config.TextColumn("المقاس", width="small"),
                    "stock": st.column_config.NumberColumn("الكمية المتوفرة", min_value=0, format="%d"),
                    "price": st.column_config.NumberColumn("سعر البيع", format="%d"),
                    "cost": st.column_config.NumberColumn("التكلفة", format="%d"),
                    "is_active": "نشط؟"
                },
                use_container_width=True,
                num_rows="dynamic", # السماح بالإضافة اليدوية أيضاً
                key="inventory_main_editor",
                height=500
            )
            
            if st.button("💾 حفظ تعديلات الجدول"):
                conn = init_connection()
                cur = conn.cursor()
                try:
                    # تحديث البيانات المعدلة (هنا نقوم بحفظ بسيط للصفوف المعدلة)
                    # ملاحظة: st.data_editor يعيد الجدول كاملاً مع التعديلات
                    # لأجل الأداء العالي، يفضل استخدام diff ولكن هنا سنستخدم Loop للحفظ
                    # (يمكن تحسينه لاحقاً باستخدام session_state لتتبع التغييرات فقط)
                    
                    # للتسهيل والأمان: سنحدث فقط الصفوف الموجودة، والجديدة نضيفها
                    for index, row in edited_df.iterrows():
                        if row['id'] and not pd.isna(row['id']): # تحديث
                             cur.execute("""
                                UPDATE variants SET name=%s, color=%s, size=%s, stock=%s, price=%s, cost=%s, is_active=%s
                                WHERE id=%s
                            """, (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], row['is_active'], row['id']))
                        else: # جديد (تم إضافته يدوياً من الجدول)
                             cur.execute("""
                                INSERT INTO variants (name, color, size, stock, price, cost, is_active)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], True))
                    
                    conn.commit()
                    st.toast("تم حفظ التعديلات!", icon="💾")
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"خطأ في الحفظ: {e}")

    # ==========================
    # 3. التقارير (نفس السابق)
    # ==========================
    elif "التقارير" in selected:
        st.markdown("### 📊 ملخص الأداء")
        d_sel = st.selectbox("الفترة", [1, 7, 30, 365], format_func=lambda x: "اليوم" if x==1 else f"{x} يوم")
        dt_start = (datetime.now() - timedelta(days=d_sel)).strftime('%Y-%m-%d')
        df_rep = run_query(f"SELECT SUM(total) as s, SUM(profit) as p FROM sales WHERE date >= '{dt_start}'", fetch_data=True)
        c1, c2 = st.columns(2)
        val_s = df_rep.iloc[0]['s'] if df_rep is not None and df_rep.iloc[0]['s'] else 0
        val_p = df_rep.iloc[0]['p'] if df_rep is not None and df_rep.iloc[0]['p'] else 0
        c1.metric("المبيعات", f"{val_s:,.0f}")
        c2.metric("الأرباح", f"{val_p:,.0f}")

    # ==========================
    # 4. الفواتير (نفس السابق)
    # ==========================
    elif "الفواتير" in selected:
        st.markdown("### 🧾 الأرشيف")
        df_logs = run_query("SELECT s.invoice_id, c.name, s.total, s.date FROM sales s JOIN customers c ON s.customer_id=c.id ORDER BY s.id DESC LIMIT 50", fetch_data=True)
        st.dataframe(df_logs, use_container_width=True)

if __name__ == "__main__":
    if st.session_state.auth: main_app()
    else: login_ui()
