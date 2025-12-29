def get_main_style():
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    :root {
        --primary: #D48896;
        --primary-dark: #B86B7A;
        --primary-light: #E8A5B0;
        --bg-dark: #0E1117;
        --bg-card: #1A1D24;
        --bg-elevated: #22262F;
        --text-primary: #FFFFFF;
        --text-secondary: #9CA3AF;
        --text-muted: #6B7280;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --border-color: rgba(255, 255, 255, 0.08);
    }

    /* تطبيق الخط العربي فقط على المحتوى - بدون التأثير على أيقونات Streamlit */
    .stApp, .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, span, label, button { 
        font-family: 'Cairo', sans-serif !important; 
    }
    
    /* اتجاه RTL للمحتوى فقط */
    .stApp {
        direction: rtl;
    }
    
    .stApp { 
        background: linear-gradient(135deg, var(--bg-dark) 0%, #151820 100%);
    }
    
    /* === القائمة الجانبية المحسّنة === */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161A22 0%, #1A1E28 100%);
        border-left: 1px solid var(--border-color);
    }

    /* === الكروت والحاويات === */
    div.stContainer, div[data-testid="stExpander"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 16px;
        backdrop-filter: blur(10px);
    }
    
    /* === حقول الإدخال المحسّنة === */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: var(--bg-elevated) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
        color: var(--text-primary) !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(212, 136, 150, 0.15) !important;
    }

    /* === الأزرار المحسّنة === */
    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        border: none;
        padding: 0.65rem 1.3rem;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        text-shadow: none;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(212, 136, 150, 0.25);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* زر أساسي */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    }
    
    /* === مقاييس الأداء === */
    div[data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
    }
    
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
    }
    
    div[data-testid="stMetricDelta"] > div {
        font-weight: 600 !important;
    }

    /* === كروت المقاييس === */
    div[data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 18px !important;
    }
    
    /* === جداول البيانات === */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* === الفواصل === */
    hr {
        border-color: var(--border-color) !important;
        margin: 1.5rem 0 !important;
    }
    
    /* === شارات الحالة === */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-success { background: rgba(16, 185, 129, 0.15); color: var(--success); }
    .status-warning { background: rgba(245, 158, 11, 0.15); color: var(--warning); }
    .status-danger { background: rgba(239, 68, 68, 0.15); color: var(--danger); }
    
    /* === عناصر السلة === */
    .cart-item {
        background: var(--bg-elevated);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
        border: 1px solid var(--border-color);
        transition: all 0.2s ease;
    }
    .cart-item:hover {
        border-color: var(--primary);
        transform: translateX(-4px);
    }
    
    /* === مجموع الفاتورة === */
    .total-card {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, rgba(212, 136, 150, 0.12) 0%, rgba(212, 136, 150, 0.05) 100%);
        border-radius: 16px;
        border: 1px solid rgba(212, 136, 150, 0.2);
        margin-bottom: 16px;
    }
    .total-label { 
        font-size: 13px; 
        color: var(--text-secondary);
        margin-bottom: 4px;
    }
    .total-value { 
        font-size: 36px; 
        font-weight: 800; 
        color: var(--primary);
        line-height: 1.2;
    }
    .total-currency {
        font-size: 16px;
        color: var(--primary-light);
    }
    
    /* === حالة السلة الفارغة === */
    .empty-cart {
        text-align: center;
        padding: 40px 20px;
        color: var(--text-muted);
    }
    .empty-cart-icon {
        font-size: 48px;
        margin-bottom: 12px;
        opacity: 0.5;
    }
    
    /* === رأس العلامة التجارية === */
    .brand-header {
        text-align: center;
        padding: 24px 12px;
        margin-bottom: 8px;
    }
    .brand-icon {
        font-size: 52px;
        display: block;
        margin-bottom: 8px;
    }
    .brand-name {
        font-size: 22px;
        font-weight: 800;
        color: var(--primary);
        margin: 0;
    }
    .brand-tagline {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 4px;
    }
    
    /* === بطاقة المنتج المختار === */
    .product-preview {
        background: var(--bg-elevated);
        border-radius: 14px;
        padding: 16px;
        border: 1px solid var(--border-color);
        margin: 12px 0;
    }
    
    /* === تحسين الـ Expander === */
    div[data-testid="stExpander"] > details > summary {
        background: var(--bg-elevated);
        border-radius: 10px;
        padding: 12px 16px !important;
    }
    
    /* === الرسائل === */
    .stAlert {
        border-radius: 12px !important;
    }
    
    /* === شريط التقدم للمخزون === */
    .stock-bar {
        height: 6px;
        border-radius: 3px;
        background: var(--bg-elevated);
        overflow: hidden;
    }
    .stock-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    /* === تخصيص شريط التمرير === */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-dark);
    }
    ::-webkit-scrollbar-thumb {
        background: var(--bg-elevated);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #3A3F4B;
    }
    
    /* === عرض مخزون الملابس === */
    .model-card {
        background: linear-gradient(135deg, #22262F 0%, #1E2128 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
        transition: all 0.2s ease;
    }
    .model-card:hover {
        border-color: #D48896;
        transform: translateY(-2px);
    }
    .model-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .model-name {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
    }
    .model-total {
        background: rgba(212, 136, 150, 0.15);
        color: #D48896;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .colors-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .color-block {
        background: #2A2E38;
        border-radius: 10px;
        padding: 12px;
        min-width: 140px;
        flex: 1;
    }
    .color-name {
        font-size: 14px;
        font-weight: 600;
        color: #E8A5B0;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .sizes-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .size-chip {
        padding: 6px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        text-align: center;
        min-width: 45px;
    }
    .size-chip.stock-good {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .size-chip.stock-low {
        background: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .size-chip.stock-out {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
        text-decoration: line-through;
        opacity: 0.6;
    }
    .price-tag {
        font-size: 11px;
        color: #9CA3AF;
        margin-top: 6px;
    }
    .legend {
        display: flex;
        gap: 16px;
        justify-content: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: #9CA3AF;
    }
    .legend-dot {
        width: 12px;
        height: 12px;
        border-radius: 4px;
    }
</style>
"""
