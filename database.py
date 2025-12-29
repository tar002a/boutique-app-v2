import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import pytz

# --- 2. Database Layer ---

@st.cache_resource
def get_db_connection():
    """Create a singleton connection"""
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except psycopg2.Error as e:
        st.error(f"❌ Database connection error: {e}")
        st.stop()
    except KeyError:
        st.error("❌ Database configuration not found in secrets.toml")
        st.stop()

def run_query(query, params=None, fetch=True, commit=False):
    """Helper to execute queries safely"""
    conn = get_db_connection()
    try:
        # Basic check if connection is alive (psycopg2 connection object has 'closed' attribute)
        if conn.closed:
            st.cache_resource.clear()
            conn = get_db_connection()
            
        with conn.cursor() as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
                return True
            if fetch:
                if cur.description:
                    col_names = [desc[0] for desc in cur.description]
                    data = cur.fetchall()
                    return pd.DataFrame(data, columns=col_names)
                return None
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"❌ Database error: {e}")
        return None

def init_db():
    """Initialize tables on first run"""
    conn = get_db_connection()
    with conn.cursor() as c:
        # Table: Products (variants)
        c.execute("""CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, 
            cost REAL, price REAL, stock INTEGER
        )""")
        # Table: Customers
        c.execute("""CREATE TABLE IF NOT EXISTS public.customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        # Table: Sales
        c.execute("""CREATE TABLE IF NOT EXISTS public.sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TIMESTAMP, invoice_id TEXT, delivery_duration TEXT,
            discount REAL
        )""")
        # Table: Expenses
        c.execute("""CREATE TABLE IF NOT EXISTS public.expenses (
            id SERIAL PRIMARY KEY, amount REAL, reason TEXT, category TEXT, date TIMESTAMP
        )""")
        # Table: Returns
        c.execute("""CREATE TABLE IF NOT EXISTS public.returns (
            id SERIAL PRIMARY KEY, sale_id INTEGER, variant_id INTEGER, customer_id INTEGER,
            product_name TEXT, product_details TEXT, qty INTEGER, return_amount REAL, 
            return_date TIMESTAMP, status TEXT
        )""")
        conn.commit()

# --- 3. Data Fetching (Caching) ---

@st.cache_data(ttl=60)
def get_inventory():
    return run_query("SELECT * FROM public.variants ORDER BY name")

@st.cache_data(ttl=300)
def get_customers():
    return run_query("SELECT * FROM public.customers ORDER BY name")

@st.cache_data(ttl=60)
def get_sales(limit=100):
    return run_query(f"SELECT * FROM public.sales ORDER BY date DESC LIMIT {limit}")

@st.cache_data(ttl=300)
def get_expenses():
    return run_query("SELECT * FROM public.expenses ORDER BY date DESC")

def clear_all_cache():
    """Clear cache to refresh data"""
    get_inventory.clear()
    get_customers.clear()
    get_sales.clear()
    get_expenses.clear()

def get_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

def migrate_db():
    """Apply schema updates to existing databases"""
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            # Add discount column if strictly not exists
            try:
                c.execute("ALTER TABLE public.sales ADD COLUMN IF NOT EXISTS discount REAL DEFAULT 0")
                conn.commit()
            except psycopg2.Error:
                conn.rollback()
    except Exception:
        pass
