import streamlit as st
from database import initialize_system
from auth import authenticate_user, log_audit, check_superuser_session, end_superuser_session, get_all_users, start_superuser_session, get_user_by_id, create_user, update_user, delete_user
from utils import *
from svg_icons import get_svg
import pandas as pd
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Bank Sampah Wani Luru - Sistem Manajemen",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tema biru putih dan UI yang lebih baik
st.markdown("""
<style>
    /* Main theme colors */
    :root {
        --primary-blue: #1E88E5;
        --dark-blue: #0D47A1;
        --light-blue: #E3F2FD;
        --success-green: #4CAF50;
        --warning-orange: #FF9800;
        --error-red: #F44336;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1E88E5 0%, #0D47A1 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: #E3F2FD;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    /* Card styling */
    .info-card {
        background: white;
        border: 2px solid #E3F2FD;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .info-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(30,136,229,0.03) 0%, transparent 70%);
        pointer-events: none;
    }
    
    .info-card:hover {
        box-shadow: 0 8px 16px rgba(30,136,229,0.2);
        transform: translateY(-4px);
        border-color: #1E88E5;
    }
    
    .info-card h3 {
        color: #1E88E5;
        margin-top: 0;
        border-bottom: 3px solid #E3F2FD;
        padding-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Metric cards with SVG background */
    .metric-card {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-radius: 15px;
        padding: 2rem 1.5rem;
        text-align: center;
        border: 2px solid #1E88E5;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: -20px;
        right: -20px;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
        border-radius: 50%;
    }
    
    .metric-card:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 12px rgba(30,136,229,0.2);
    }
    
    .metric-card h2 {
        color: #0D47A1;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .metric-card p {
        color: #1E88E5;
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1E88E5 0%, #1976D2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transform: translateY(-2px);
    }
    
    /* Form styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border: 2px solid #E3F2FD;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #1E88E5;
        box-shadow: 0 0 0 3px rgba(30,136,229,0.1);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: #E3F2FD;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: #1E88E5;
        border: 2px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1E88E5 0%, #1976D2 100%);
        color: white;
        border-color: #0D47A1;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        border: 2px solid #E3F2FD;
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: #E8F5E9;
        border-left: 4px solid #4CAF50;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stError {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stWarning {
        background-color: #FFF3E0;
        border-left: 4px solid #FF9800;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stInfo {
        background-color: #E3F2FD;
        border-left: 4px solid #1E88E5;
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #E3F2FD 0%, #BBDEFB 100%);
    }
    
    [data-testid="stSidebar"] h1 {
        color: #0D47A1;
    }
    
    /* Login page special styling */
    .login-container {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-radius: 15px;
        padding: 3rem;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    
    .login-title {
        color: #0D47A1;
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 2rem;
    }
    
    /* Role badge */
    .role-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .role-superuser {
        background: linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%);
        color: white;
    }
    
    .role-panitia {
        background: linear-gradient(135deg, #1E88E5 0%, #1565C0 100%);
        color: white;
    }
    
    .role-warga {
        background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
        color: white;
    }
    
    /* Help text */
    .help-text {
        background: #E3F2FD;
        border-left: 4px solid #1E88E5;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-size: 0.95rem;
        color: #0D47A1;
    }
    
    /* Transaction item */
    .transaction-item {
        background: white;
        border: 2px solid #E3F2FD;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .transaction-item:hover {
        border-color: #1E88E5;
        box-shadow: 0 2px 8px rgba(30,136,229,0.15);
    }
    
    /* SVG Card Container */
    .svg-card {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        border: 3px solid #1E88E5;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .svg-card::after {
        content: '';
        position: absolute;
        bottom: -50px;
        right: -50px;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(255,255,255,0.4) 0%, transparent 70%);
        border-radius: 50%;
    }
    
    /* Empty State Container */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        background: linear-gradient(135deg, #E3F2FD 0%, #F5F5F5 100%);
        border-radius: 15px;
        border: 2px dashed #90CAF9;
    }
    
    .empty-state svg {
        margin: 0 auto 1rem auto;
        display: block;
    }
    
    .empty-state h3 {
        color: #0D47A1;
        margin: 1rem 0 0.5rem 0;
    }
    
    .empty-state p {
        color: #1E88E5;
        margin: 0;
    }
    
    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .stat-item {
        background: white;
        border-left: 5px solid #1E88E5;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
    }
    
    .stat-item:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 12px rgba(30,136,229,0.2);
    }
    
    .stat-item h4 {
        color: #90CAF9;
        font-size: 0.85rem;
        margin: 0 0 0.5rem 0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stat-item h2 {
        color: #0D47A1;
        font-size: 2rem;
        margin: 0;
        font-weight: 700;
    }

</style>
""", unsafe_allow_html=True)

# Initialize database
initialize_system()

# Initialize session state
if 'user' not in st.session_state:
    st.session_state['user'] = None

def login_page():
    """Display login page"""
    
    # Header
    st.markdown("""
    <div class="main-header" style="text-align: center;">
        <h1>♻️ Bank Sampah Wani Luru</h1>
        <p>Sistem Manajemen Bank Sampah Digital</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown('<h2 class="login-title">🔐 Masuk ke Sistem</h2>', unsafe_allow_html=True)
        
        username = st.text_input("👤 Username", placeholder="Masukkan username Anda")
        password = st.text_input("🔒 Password", type="password", placeholder="Masukkan password Anda")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 Login Sekarang", use_container_width=True):
            if username and password:
                with st.spinner("Memproses login..."):
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state['user'] = user
                        log_audit(user['id'], 'LOGIN', f"User {username} logged in")
                        st.success(f"✅ Selamat datang, {user['full_name']}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Username atau password salah!")
            else:
                st.warning("⚠️ Silakan isi username dan password!")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Help section
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("ℹ️ Bantuan Login - Klik untuk melihat"):
            st.markdown("""
            <div class="info-card">
                <h3>📚 Panduan Login</h3>
                <p><strong>Untuk pengguna baru:</strong></p>
                <ul>
                    <li>Hubungi administrator untuk mendapatkan akun</li>
                    <li>Gunakan username dan password yang diberikan</li>
                    <li>Ganti password setelah login pertama kali</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Akun Demo untuk Testing:**")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.info("""
                **🟣 Super User**  
                Username: `superuser`  
                Password: `admin123`  
                *Akses penuh sistem*
                """)
                
            with col_b:
                st.info("""
                **🔵 Panitia**  
                Username: `panitia1`  
                Password: `panitia123`  
                *Input transaksi & keuangan*
                """)
                
                st.info("""
                **🟢 Warga**  
                Username: `warga1`  
                Password: `warga123`  
                *Cek saldo & performa*
                """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #1E88E5; font-size: 0.9rem;">
        <p>💙 Bank Sampah Wani Luru - Untuk Lingkungan yang Lebih Bersih dan Sejahtera</p>
        <p style="font-size: 0.8rem; color: #90CAF9;">© 2026 Bank Sampah Wani Luru Management System</p>
    </div>
    """, unsafe_allow_html=True)

def show_superuser_banner():
    """Show banner when superuser is acting as another user"""
    if check_superuser_session():
        st.warning(f"⚠️ Anda login sebagai **{st.session_state['user']['full_name']}** | "
                  f"Akun Asli: **{st.session_state['superuser_original_name']}**")
        if st.button("🔙 Kembali ke Akun Super User"):
            end_superuser_session()

def dashboard_pengepul():
    """Dashboard for Pengepul (Collector) role"""
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📦 Dashboard Pengepul</h1>
        <p>Kelola kategori sampah, set harga, dan monitor performa penjualan</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Kelola Kategori", "📈 Riwayat Harga", "📊 Performa Barang", "📋 Riwayat Transaksi"])
    
    with tab1:
        st.subheader("Kelola Kategori Sampah")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Daftar Kategori")
            categories = get_all_categories()
            
            if categories:
                df_categories = pd.DataFrame(
                    [(c['id'], c['name'], f"Rp {c['price_per_kg']:,.0f}", 
                      c['updated_at']) for c in categories],
                    columns=['ID', 'Nama Kategori', 'Harga/Kg', 'Update Terakhir']
                )
                st.dataframe(df_categories, use_container_width=True, hide_index=True)
                
                # Update price section
                st.markdown("### Update Harga")
                col_a, col_b, col_c = st.columns([2, 1, 1])
                
                with col_a:
                    category_options = {c['name']: c['id'] for c in categories}
                    selected_category = st.selectbox("Pilih Kategori", list(category_options.keys()))
                
                with col_b:
                    new_price = st.number_input("💰 Harga Baru (Rp/Kg)", min_value=0, step=100,
                                               help="Masukkan harga baru per kilogram")
                
                with col_c:
                    st.write("")
                    st.write("")
                    if st.button("💾 Update Harga", use_container_width=True, type="primary"):
                        if new_price > 0:
                            category_id = category_options[selected_category]
                            update_category_price(category_id, new_price)
                            log_audit(st.session_state['user']['id'], 'UPDATE_PRICE', 
                                    f"Updated price for {selected_category} to Rp {new_price}")
                            st.success(f"✅ Harga {selected_category} berhasil diupdate menjadi Rp {new_price:,.0f}/Kg!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("⚠️ Harga harus lebih dari 0!")
            else:
                st.info("📝 Belum ada kategori sampah. Silakan tambah kategori baru terlebih dahulu.")
        
        with col2:
            st.markdown("### Tambah Kategori Baru")
            
            with st.form("add_category_form"):
                new_category_name = st.text_input("Nama Kategori")
                new_category_price = st.number_input("Harga/Kg (Rp)", min_value=0, step=100)
                
                submitted = st.form_submit_button("Tambah Kategori", use_container_width=True)
                
                if submitted:
                    if new_category_name and new_category_price > 0:
                        success, message = create_category(new_category_name, new_category_price)
                        if success:
                            log_audit(st.session_state['user']['id'], 'CREATE_CATEGORY', 
                                    f"Created category {new_category_name}")
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(f"Gagal menambah kategori: {message}")
                    else:
                        st.warning("Silakan isi semua field!")
    
    with tab2:
        st.subheader("Riwayat Perubahan Harga")
        
        # Get price history from transactions
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT c.name, t.price_per_kg, DATE(t.transaction_date) as date
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            ORDER BY t.transaction_date DESC
            LIMIT 50
        ''')
        price_history = cursor.fetchall()
        conn.close()
        
        if price_history:
            df_history = pd.DataFrame(
                [(h['name'], f"Rp {h['price_per_kg']:,.0f}", h['date']) for h in price_history],
                columns=['Kategori', 'Harga/Kg', 'Tanggal']
            )
            st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat transaksi")
    
    with tab3:
        st.subheader("Performa Barang yang Dibeli")
        
        # Period filter
        col1, col2 = st.columns([1, 3])
        
        with col1:
            period = st.selectbox("Periode", ["Bulan Ini", "3 Bulan Terakhir", "Tahun Ini", "Semua Waktu"], key="perf_period")
            
            # Calculate date range
            today = datetime.now()
            if period == "Bulan Ini":
                start_date = today.replace(day=1)
            elif period == "3 Bulan Terakhir":
                start_date = today - timedelta(days=90)
            elif period == "Tahun Ini":
                start_date = today.replace(month=1, day=1)
            else:
                start_date = None
        
        # Get performance statistics per category
        conn = get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT c.name, c.price_per_kg as current_price,
                   COUNT(t.id) as total_transactions,
                   SUM(t.weight_kg) as total_weight,
                   AVG(t.price_per_kg) as avg_price,
                   SUM(t.total_amount) as total_revenue
            FROM categories c
            LEFT JOIN transactions t ON c.id = t.category_id
        '''
        
        params = []
        if start_date:
            query += ' WHERE DATE(t.transaction_date) >= ?'
            params.append(start_date.strftime('%Y-%m-%d'))
        
        query += ' GROUP BY c.id ORDER BY total_revenue DESC'
        
        cursor.execute(query, params)
        category_performance = cursor.fetchall()
        conn.close()
        
        if category_performance:
            # Summary metrics
            total_trans = sum(cp['total_transactions'] or 0 for cp in category_performance)
            total_weight = sum(cp['total_weight'] or 0 for cp in category_performance)
            total_rev = sum(cp['total_revenue'] or 0 for cp in category_performance)
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                st.metric("Total Transaksi", total_trans)
            
            with metric_col2:
                st.metric("Total Berat Dibeli", f"{total_weight:.2f} Kg")
            
            with metric_col3:
                st.metric("Total Revenue", f"Rp {total_rev:,.0f}")
            
            st.markdown("---")
            st.markdown("### Detail per Kategori")
            
            # Detailed table
            df_performance = pd.DataFrame(
                [(cp['name'], 
                  f"Rp {cp['current_price']:,.0f}",
                  cp['total_transactions'] or 0,
                  f"{cp['total_weight'] or 0:.2f} Kg",
                  f"Rp {cp['avg_price'] or 0:,.0f}",
                  f"Rp {cp['total_revenue'] or 0:,.0f}") for cp in category_performance],
                columns=['Kategori', 'Harga Saat Ini', 'Total Transaksi', 'Total Berat', 'Harga Rata-rata', 'Total Revenue']
            )
            st.dataframe(df_performance, use_container_width=True, hide_index=True)
            
            # Chart - Top 5 categories by weight
            st.markdown("### Top 5 Kategori (Berdasarkan Berat)")
            top_5_weight = sorted(category_performance, key=lambda x: x['total_weight'] or 0, reverse=True)[:5]
            
            if top_5_weight:
                chart_data = pd.DataFrame(
                    [(cp['name'], cp['total_weight'] or 0) for cp in top_5_weight],
                    columns=['Kategori', 'Berat (Kg)']
                )
                st.bar_chart(chart_data.set_index('Kategori'))
        else:
            st.info("Belum ada data transaksi")
    
    with tab4:
        st.subheader("Riwayat Transaksi dari Panitia")
        
        # Date filter
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            start_date_trans = st.date_input("Dari Tanggal", value=datetime.now() - timedelta(days=30), key="trans_start")
        
        with col2:
            end_date_trans = st.date_input("Sampai Tanggal", value=datetime.now(), key="trans_end")
        
        with col3:
            # Category filter
            all_categories = get_all_categories()
            category_filter_options = ["Semua Kategori"] + [c['name'] for c in all_categories]
            selected_category_filter = st.selectbox("Filter Kategori", category_filter_options)
        
        # Get transactions
        conn = get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT t.*, u.full_name as warga_name, c.name as category_name,
                   p.full_name as processed_by_name
            FROM transactions t
            JOIN users u ON t.warga_id = u.id
            JOIN categories c ON t.category_id = c.id
            JOIN users p ON t.processed_by = p.id
            WHERE DATE(t.transaction_date) BETWEEN ? AND ?
        '''
        params = [start_date_trans, end_date_trans]
        
        if selected_category_filter != "Semua Kategori":
            query += ' AND c.name = ?'
            params.append(selected_category_filter)
        
        query += ' ORDER BY t.transaction_date DESC LIMIT 100'
        
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        conn.close()
        
        if transactions:
            # Summary
            total_transactions = len(transactions)
            total_weight_trans = sum(t['weight_kg'] for t in transactions)
            total_revenue_trans = sum(t['total_amount'] for t in transactions)
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                st.metric("Jumlah Transaksi", total_transactions)
            
            with metric_col2:
                st.metric("Total Berat", f"{total_weight_trans:.2f} Kg")
            
            with metric_col3:
                st.metric("Total Revenue", f"Rp {total_revenue_trans:,.0f}")
            
            st.markdown("---")
            
            # Transaction table
            df_trans = pd.DataFrame(
                [(t['transaction_date'],
                  t['warga_name'],
                  t['category_name'],
                  f"{t['weight_kg']:.2f} Kg",
                  f"Rp {t['price_per_kg']:,.0f}",
                  f"Rp {t['total_amount']:,.0f}",
                  t['processed_by_name'],
                  t['notes'] or '-') for t in transactions],
                columns=['Tanggal', 'Warga', 'Kategori', 'Berat', 'Harga/Kg', 'Total', 'Diproses Oleh', 'Catatan']
            )
            st.dataframe(df_trans, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada transaksi pada periode dan filter yang dipilih")

def dashboard_panitia():
    """Dashboard for Panitia (Committee) role"""
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📊 Dashboard Panitia</h1>
        <p>Input transaksi, kelola keuangan warga, dan buat laporan lengkap</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "➕ Input Transaksi", "💰 Kelola Keuangan", "👥 Kelola Warga", "📑 Laporan", "📈 Performa Warga", "💵 Pendapatan Panitia"
    ])
    
    with tab1:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.subheader("➕ Input Transaksi Penjualan Sampah")
        
        # Help text
        st.markdown("""
        <div class="help-text">
            <strong>📝 Cara Input Transaksi:</strong><br>
            1. Pilih nama warga yang menjual sampah<br>
            2. Pilih kategori sampah (harga otomatis muncul)<br>
            3. Timbang dan masukkan berat dalam Kg<br>
            4. Sistem akan otomatis hitung: Total, Fee Panitia (10%), dan Saldo Warga
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("transaction_form"):
                st.markdown("### 📝 Form Input Transaksi")
                
                # Get warga list
                warga_list = get_all_users('warga')
                warga_options = {f"👤 {w['full_name']} ({w['username']})": w['id'] for w in warga_list}
                
                selected_warga = st.selectbox("👤 Pilih Warga", list(warga_options.keys()), 
                                              help="Pilih warga yang menjual sampah")
                
                # Get categories
                categories = get_all_categories()
                category_options = {f"♻️ {c['name']} - Rp {c['price_per_kg']:,.0f}/Kg": c['id'] for c in categories}
                
                selected_category = st.selectbox("♻️ Pilih Kategori Sampah", list(category_options.keys()),
                                                help="Kategori sampah beserta harga per Kg saat ini")
                
                weight = st.number_input("⚖️ Berat (Kg)", min_value=0.0, step=0.1, format="%.2f",
                                        help="Masukkan berat sampah dalam kilogram (Kg)")
                
                # Show preview calculation
                if weight > 0:
                    selected_cat_id = category_options[selected_category]
                    cat_data = next(c for c in categories if c['id'] == selected_cat_id)
                    preview_total = weight * cat_data['price_per_kg']
                    preview_fee = preview_total * 0.10
                    preview_net = preview_total - preview_fee
                    
                    st.markdown(f"""
                    <div style="background: #E3F2FD; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                        <p style="margin: 0; color: #0D47A1; font-weight: 600;">💡 Preview Perhitungan:</p>
                        <p style="margin: 0.3rem 0; color: #1E88E5;">Total Kotor: <strong>Rp {preview_total:,.0f}</strong></p>
                        <p style="margin: 0.3rem 0; color: #1E88E5;">Fee Panitia (10%): <strong>Rp {preview_fee:,.0f}</strong></p>
                        <p style="margin: 0.3rem 0; color: #0D47A1; font-size: 1.1rem;">Warga Terima: <strong>Rp {preview_net:,.0f}</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                notes = st.text_area("📌 Catatan (Opsional)", 
                                    help="Tambahkan catatan jika diperlukan, misal: kondisi sampah, dll")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("🚀 Proses Transaksi Sekarang", use_container_width=True, type="primary")
                
                if submitted:
                    if weight > 0:
                        warga_id = warga_options[selected_warga]
                        category_id = category_options[selected_category]
                        
                        with st.spinner("⏳ Memproses transaksi..."):
                            success, transaction_id, details = create_transaction(
                                warga_id, category_id, weight, 
                                st.session_state['user']['id'], notes
                            )
                        
                        if success:
                            log_audit(st.session_state['user']['id'], 'CREATE_TRANSACTION',
                                    f"Transaction {transaction_id} for warga {warga_id}")
                            
                            st.success("✅ Transaksi berhasil diproses!")
                            st.balloons()
                            
                            # Better detail display
                            st.markdown(f"""
                            <div class="info-card" style="background: #E8F5E9; border-color: #4CAF50;">
                                <h3 style="color: #2E7D32; margin-top: 0;">💰 Detail Transaksi #{transaction_id}</h3>
                                <table style="width: 100%; color: #1B5E20;">
                                    <tr><td><strong>Total Kotor:</strong></td><td style="text-align: right;"><strong>Rp {details['total_amount']:,.0f}</strong></td></tr>
                                    <tr><td>Fee Panitia (10%):</td><td style="text-align: right;">Rp {details['committee_fee']:,.0f}</td></tr>
                                    <tr style="border-top: 2px solid #4CAF50;"><td><strong>Diterima Warga:</strong></td><td style="text-align: right; font-size: 1.2rem;"><strong>Rp {details['net_amount']:,.0f}</strong></td></tr>
                                    <tr><td><strong>Saldo Baru Warga:</strong></td><td style="text-align: right; color: #2E7D32; font-size: 1.2rem;"><strong>Rp {details['new_balance']:,.0f}</strong></td></tr>
                                </table>
                            </div>
                            """, unsafe_allow_html=True)
                            st.rerun()
                    else:
                        st.warning("⚠️ Berat harus lebih dari 0!")
        
        with col2:
            st.markdown("### 🕐 Transaksi Terakhir")
            recent_transactions = get_transactions(limit=5)
            
            if recent_transactions:
                for t in recent_transactions:
                    st.markdown(f"""
                    <div class="transaction-item">
                        <strong style="color: #0D47A1;">👤 {t['warga_name']}</strong><br>
                        <span style="color: #1E88E5;">♻️ {t['category_name']} - {t['weight_kg']} Kg</span><br>
                        <strong style="color: #4CAF50; font-size: 1.1rem;">Rp {t['net_amount']:,.0f}</strong><br>
                        <small style="color: #90CAF9;">🕐 {t['transaction_date']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(
                    """
<div class="empty-state">
    """ + get_svg('empty_state') + """
    <h3>Belum Ada Transaksi</h3>
    <p>Transaksi terbaru akan muncul di sini</p>
</div>
                    """,
                    unsafe_allow_html=True,
                )
    
    with tab2:
        st.subheader("Kelola Keuangan Warga")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 Penarikan Saldo")
            
            with st.form("withdrawal_form"):
                warga_list = get_all_users('warga')
                warga_options_w = {f"{w['full_name']} - Saldo: Rp {w['balance']:,.0f}": w['id'] for w in warga_list}
                
                selected_warga_w = st.selectbox("Pilih Warga", list(warga_options_w.keys()), key="withdraw_warga")
                withdrawal_amount = st.number_input("Jumlah Penarikan (Rp)", min_value=0, step=1000)
                withdrawal_notes = st.text_area("Catatan", key="withdraw_notes")
                
                submitted_w = st.form_submit_button("Proses Penarikan", use_container_width=True)
                
                if submitted_w:
                    if withdrawal_amount > 0:
                        warga_id = warga_options_w[selected_warga_w]
                        success, result = process_withdrawal(
                            warga_id, withdrawal_amount,
                            st.session_state['user']['id'], withdrawal_notes
                        )
                        
                        if success:
                            log_audit(st.session_state['user']['id'], 'WITHDRAWAL',
                                    f"Withdrawal Rp {withdrawal_amount} for warga {warga_id}")
                            st.success(f"✅ Penarikan berhasil! Saldo baru: Rp {result:,.0f}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result}")
                    else:
                        st.warning("Jumlah harus lebih dari 0!")
        
        with col2:
            st.markdown("### 📥 Deposit/Setor")
            
            with st.form("deposit_form"):
                warga_list_d = get_all_users('warga')
                warga_options_d = {f"{w['full_name']} - Saldo: Rp {w['balance']:,.0f}": w['id'] for w in warga_list_d}
                
                selected_warga_d = st.selectbox("Pilih Warga", list(warga_options_d.keys()), key="deposit_warga")
                deposit_amount = st.number_input("Jumlah Deposit (Rp)", min_value=0, step=1000)
                deposit_notes = st.text_area("Catatan", key="deposit_notes")
                
                submitted_d = st.form_submit_button("Proses Deposit", use_container_width=True)
                
                if submitted_d:
                    if deposit_amount > 0:
                        warga_id = warga_options_d[selected_warga_d]
                        success, result = process_deposit(
                            warga_id, deposit_amount,
                            st.session_state['user']['id'], deposit_notes
                        )
                        
                        if success:
                            log_audit(st.session_state['user']['id'], 'DEPOSIT',
                                    f"Deposit Rp {deposit_amount} for warga {warga_id}")
                            st.success(f"✅ Deposit berhasil! Saldo baru: Rp {result:,.0f}")
                            st.rerun()
                        else:
                            st.error(f"❌ {result}")
                    else:
                        st.warning("Jumlah harus lebih dari 0!")
        
        # Recent movements
        st.markdown("### Riwayat Keuangan Terbaru")
        recent_movements = get_financial_movements(limit=10)
        
        if recent_movements:
            df_movements = pd.DataFrame(
                [(m['warga_name'], 
                  'Penarikan' if m['type'] == 'withdrawal' else 'Deposit',
                  f"Rp {m['amount']:,.0f}",
                  f"Rp {m['balance_after']:,.0f}",
                  m['movement_date'],
                  m['processed_by_name']) for m in recent_movements],
                columns=['Warga', 'Tipe', 'Jumlah', 'Saldo Akhir', 'Tanggal', 'Diproses Oleh']
            )
            st.dataframe(df_movements, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat keuangan")
    
    with tab3:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.subheader("👥 Kelola Data Warga")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add/Edit/Delete tabs
        manage_tab1, manage_tab2, manage_tab3 = st.tabs(["➕ Tambah Warga", "✏️ Edit Warga", "🗑️ Hapus Warga"])
        
        with manage_tab1:
            st.markdown("### Tambah Warga Baru")
            
            with st.form("add_warga_form"):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    new_username = st.text_input("👤 Username", help="Username untuk login")
                    new_password = st.text_input("🔒 Password", type="password", help="Password minimal 6 karakter")
                    new_full_name = st.text_input("📝 Nama Lengkap", help="Nama lengkap sesuai KTP")
                    new_nickname = st.text_input("🏷️ Nama Panggilan", help="Nama panggilan yang umum digunakan")
                
                with col_b:
                    new_address = st.text_area("🏠 Alamat Lengkap", help="Alamat sesuai KTP")
                    new_rt = st.text_input("🏘️ RT", help="RT tempat tinggal")
                    new_rw = st.text_input("🏘️ RW", help="RW tempat tinggal")
                    new_whatsapp = st.text_input("📱 No. WhatsApp", help="Nomor WA yang aktif")
                    new_role = st.selectbox("👔 Role", ["warga", "panitia"], help="Pilih role untuk user baru")
                
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("➕ Tambah Warga", use_container_width=True, type="primary")
                
                if submitted:
                    if new_username and new_password and new_full_name:
                        if len(new_password) < 6:
                            st.error("❌ Password minimal 6 karakter!")
                        else:
                            success, result = create_user(
                                new_username, new_password, new_full_name, new_role,
                                new_nickname, new_address, new_rt, new_rw, new_whatsapp
                            )
                            
                            if success:
                                log_audit(st.session_state['user']['id'], 'CREATE_USER',
                                        f"Created user {new_username} with role {new_role}")
                                st.success(f"✅ Warga berhasil ditambahkan dengan ID: {result}")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ Gagal menambah warga: {result}")
                    else:
                        st.warning("⚠️ Username, Password, dan Nama Lengkap wajib diisi!")
        
        with manage_tab2:
            st.markdown("### Edit Data Warga")
            
            warga_list = get_all_users('warga')
            
            if warga_list:
                warga_options = {f"{w['full_name']} ({w['username']})": w for w in warga_list}
                selected_warga_edit = st.selectbox("Pilih Warga untuk Edit", list(warga_options.keys()))
                
                if selected_warga_edit:
                    warga = warga_options[selected_warga_edit]
                    
                    with st.form("edit_warga_form"):
                        st.info(f"📝 Edit data untuk: **{warga['username']}**")
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            edit_full_name = st.text_input("📝 Nama Lengkap", value=warga['full_name'] or "")
                            edit_nickname = st.text_input("🏷️ Nama Panggilan", value=warga.get('nickname') or "")
                        
                        with col_b:
                            edit_address = st.text_area("🏠 Alamat Lengkap", value=warga['address'] or "")
                            edit_rt = st.text_input("🏘️ RT", value=warga.get('rt') or "")
                            edit_rw = st.text_input("🏘️ RW", value=warga.get('rw') or "")
                            edit_whatsapp = st.text_input("📱 No. WhatsApp", value=warga.get('whatsapp') or "")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        submitted_edit = st.form_submit_button("💾 Simpan Perubahan", use_container_width=True, type="primary")
                        
                        if submitted_edit:
                            if edit_full_name:
                                success, message = update_user(
                                    warga['id'], edit_full_name, edit_nickname, edit_address, edit_rt, edit_rw, edit_whatsapp
                                )
                                
                                if success:
                                    log_audit(st.session_state['user']['id'], 'UPDATE_USER',
                                            f"Updated user {warga['username']}")
                                    st.success(f"✅ {message}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Gagal update: {message}")
                            else:
                                st.warning("⚠️ Nama Lengkap wajib diisi!")
            else:
                st.info("📝 Belum ada data warga")
        
        with manage_tab3:
            st.markdown("### Hapus Warga")
            st.warning("⚠️ **Perhatian:** Menghapus warga akan menghapus semua data terkait!")
            
            warga_list = get_all_users('warga')
            
            if warga_list:
                warga_options_delete = {f"{w['full_name']} ({w['username']}) - Saldo: Rp {w['balance']:,.0f}": w['id'] for w in warga_list}
                selected_warga_delete = st.selectbox("Pilih Warga untuk Dihapus", list(warga_options_delete.keys()))
                
                col_a, col_b = st.columns([2, 1])
                
                with col_b:
                    if st.button("🗑️ Hapus Warga", use_container_width=True, type="primary"):
                        warga_id = warga_options_delete[selected_warga_delete]
                        
                        # Check balance first
                        warga_data = next(w for w in warga_list if w['id'] == warga_id)
                        if warga_data['balance'] > 0:
                            st.error(f"❌ Tidak bisa hapus! Warga masih punya saldo Rp {warga_data['balance']:,.0f}. Tarik dulu saldonya!")
                        else:
                            success, message = delete_user(warga_id)
                            
                            if success:
                                log_audit(st.session_state['user']['id'], 'DELETE_USER',
                                        f"Deleted user ID {warga_id}")
                                st.success(f"✅ {message}")
                                st.rerun()
                            else:
                                st.error(f"❌ Gagal hapus: {message}")
            else:
                st.info("📝 Belum ada data warga")
        
        # Display current warga list
        st.markdown("---")
        st.markdown("### 📋 Daftar Warga Terdaftar")
        
        all_warga = get_all_users('warga')
        
        if all_warga:
                        df_warga = pd.DataFrame(
                                [(w['id'], w['username'], w['full_name'], w.get('nickname') or '-',
                                    f"RT {w.get('rt') or '-'} / RW {w.get('rw') or '-'}",
                                    w.get('whatsapp') or '-', f"Rp {w['balance']:,.0f}",
                                    'Aktif' if w['active'] else 'Non-Aktif') for w in all_warga],
                                columns=['ID', 'Username', 'Nama Lengkap', 'Panggilan', 'RT/RW', 'WhatsApp', 'Saldo', 'Status']
                        )
            st.dataframe(df_warga, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                """
<div class="empty-state">
    """ + get_svg('user') + """
    <h3>Belum Ada Warga Terdaftar</h3>
    <p>Tambahkan warga baru menggunakan form di atas</p>
</div>
                """,
                unsafe_allow_html=True,
            )
    
    with tab4:
        st.subheader("Laporan Keuangan")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_type = st.selectbox("Pilih Periode", ["Bulanan", "Tahunan"])
            
            if report_type == "Bulanan":
                col_a, col_b = st.columns(2)
                with col_a:
                    year = st.number_input("Tahun", min_value=2020, max_value=2030, value=datetime.now().year)
                with col_b:
                    month = st.number_input("Bulan", min_value=1, max_value=12, value=datetime.now().month)
                
                if st.button("Generate Laporan Bulanan"):
                    stats = get_monthly_statistics(year, month)
                    committee_earnings = get_committee_total_earnings(
                        f"{year}-{month:02d}-01",
                        f"{year}-{month:02d}-31"
                    )
                    
                    st.markdown("### 📈 Statistik Bulanan")
                    
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    
                    with metric_col1:
                        st.metric("Total Transaksi", stats['total_transactions'])
                    
                    with metric_col2:
                        st.metric("Total Berat", f"{stats['total_weight']:.2f} Kg")
                    
                    with metric_col3:
                        st.metric("Total Revenue", f"Rp {stats['total_revenue']:,.0f}")
                    
                    with metric_col4:
                        st.metric("Pendapatan Panitia", f"Rp {committee_earnings:,.0f}")
            
            else:  # Tahunan
                year = st.number_input("Tahun", min_value=2020, max_value=2030, value=datetime.now().year, key="year_annual")
                
                if st.button("Generate Laporan Tahunan"):
                    stats = get_yearly_statistics(year)
                    committee_earnings = get_committee_total_earnings(
                        f"{year}-01-01",
                        f"{year}-12-31"
                    )
                    
                    st.markdown("### 📈 Statistik Tahunan")
                    
                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
                    
                    with metric_col1:
                        st.metric("Total Transaksi", stats['total_transactions'])
                    
                    with metric_col2:
                        st.metric("Total Berat", f"{stats['total_weight']:.2f} Kg")
                    
                    with metric_col3:
                        st.metric("Total Revenue", f"Rp {stats['total_revenue']:,.0f}")
                    
                    with metric_col4:
                        st.metric("Pendapatan Panitia", f"Rp {committee_earnings:,.0f}")
        
        with col2:
            st.markdown("### Riwayat Transaksi")
            
            # Date filter
            col_start, col_end = st.columns(2)
            with col_start:
                start_date = st.date_input("Dari Tanggal", value=datetime.now() - timedelta(days=30))
            with col_end:
                end_date = st.date_input("Sampai Tanggal", value=datetime.now())
            
            transactions = get_transactions(start_date=start_date, end_date=end_date)
            
            if transactions:
                df_trans = pd.DataFrame(
                    [(t['warga_name'], t['category_name'], t['weight_kg'],
                      f"Rp {t['total_amount']:,.0f}", f"Rp {t['committee_fee']:,.0f}",
                      f"Rp {t['net_amount']:,.0f}", t['transaction_date']) for t in transactions],
                    columns=['Warga', 'Kategori', 'Berat (Kg)', 'Total', 'Fee Panitia', 'Diterima Warga', 'Tanggal']
                )
                st.dataframe(df_trans, use_container_width=True, hide_index=True)
                
                # Summary
                total_revenue = sum(t['total_amount'] for t in transactions)
                total_fee = sum(t['committee_fee'] for t in transactions)
                
                st.info(f"**Total Revenue:** Rp {total_revenue:,.0f} | **Total Fee Panitia:** Rp {total_fee:,.0f}")
            else:
                st.info("Tidak ada transaksi pada periode ini")
    
    with tab5:
        st.subheader("Performa Warga")
        
        # Select warga
        warga_list = get_all_users('warga')
        warga_options = {w['full_name']: w['id'] for w in warga_list}
        
        selected_warga_perf = st.selectbox("Pilih Warga", list(warga_options.keys()))
        
        col1, col2 = st.columns(2)
        
        with col1:
            period = st.selectbox("Periode", ["Bulan Ini", "3 Bulan Terakhir", "Tahun Ini", "Semua Waktu"])
        
        # Calculate date range
        today = datetime.now()
        if period == "Bulan Ini":
            start_date = today.replace(day=1)
        elif period == "3 Bulan Terakhir":
            start_date = today - timedelta(days=90)
        elif period == "Tahun Ini":
            start_date = today.replace(month=1, day=1)
        else:
            start_date = None
        
        warga_id = warga_options[selected_warga_perf]
        performance = get_warga_performance(warga_id, 
                                           start_date.strftime('%Y-%m-%d') if start_date else None,
                                           today.strftime('%Y-%m-%d'))
        
        # Display metrics
        st.markdown(f"### Performa: {selected_warga_perf}")
        
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric("Total Transaksi", performance['total_transactions'])
        
        with metric_col2:
            st.metric("Total Berat", f"{performance['total_weight']:.2f} Kg")
        
        with metric_col3:
            st.metric("Total Pendapatan", f"Rp {performance['total_earned']:,.0f}")
        
        with metric_col4:
            current_balance = get_user_balance(warga_id)
            st.metric("Saldo Saat Ini", f"Rp {current_balance:,.0f}")
        
        # Transaction history for this warga
        st.markdown("### Riwayat Transaksi")
        warga_transactions = get_transactions(warga_id=warga_id, limit=20)
        
        if warga_transactions:
            df_warga_trans = pd.DataFrame(
                [(t['category_name'], t['weight_kg'], f"Rp {t['net_amount']:,.0f}",
                  t['transaction_date'], t['processed_by_name']) for t in warga_transactions],
                columns=['Kategori', 'Berat (Kg)', 'Diterima', 'Tanggal', 'Diproses Oleh']
            )
            st.dataframe(df_warga_trans, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada transaksi")
    
    with tab6:
        st.subheader("Pendapatan Panitia")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Date filter
            st.markdown("### Filter Periode")
            start_date_comm = st.date_input("Dari", value=datetime.now() - timedelta(days=30), key="comm_start")
            end_date_comm = st.date_input("Sampai", value=datetime.now(), key="comm_end")
            
            total_earnings = get_committee_total_earnings(start_date_comm, end_date_comm)
            
            st.metric("Total Pendapatan Panitia", f"Rp {total_earnings:,.0f}")
        
        with col2:
            st.markdown("### Detail Pendapatan")
            
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ce.*, t.transaction_date, u.full_name as warga_name, c.name as category_name
                FROM committee_earnings ce
                JOIN transactions t ON ce.transaction_id = t.id
                JOIN users u ON t.warga_id = u.id
                JOIN categories c ON t.category_id = c.id
                WHERE DATE(ce.earned_date) BETWEEN ? AND ?
                ORDER BY ce.earned_date DESC
            ''', (start_date_comm, end_date_comm))
            earnings_detail = cursor.fetchall()
            conn.close()
            
            if earnings_detail:
                df_earnings = pd.DataFrame(
                    [(e['warga_name'], e['category_name'], f"Rp {e['amount']:,.0f}",
                      e['earned_date']) for e in earnings_detail],
                    columns=['Warga', 'Kategori', 'Fee (10%)', 'Tanggal']
                )
                st.dataframe(df_earnings, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada pendapatan pada periode ini")

def dashboard_warga():
    """Dashboard for Warga (Resident) role"""
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>💰 Dashboard Warga</h1>
        <p>Cek saldo, performa penjualan sampah, dan riwayat keuangan Anda</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_id = st.session_state['user']['id']
    
    # Get current balance
    balance = get_user_balance(user_id)
    
    # Display balance with SVG and better styling
    col_svg, col_balance = st.columns([1, 3])
    
    with col_svg:
        st.markdown(get_svg('money'), unsafe_allow_html=True)
    
    with col_balance:
        st.markdown(f"""
        <div class="metric-card" style="font-size: 1.2rem; margin: 0; text-align: left;">
            <p style="margin: 0; font-size: 1rem; color: #90CAF9;">💰 SALDO ANDA SAAT INI</p>
            <h2 style="margin: 0.5rem 0; font-size: 3rem; color: #0D47A1;">Rp {balance:,.0f}</h2>
            <p style="margin: 0; font-size: 0.9rem; color: #1E88E5;">✓ Dapat ditarik kapan saja melalui Panitia</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📊 Performa Saya", "📋 Riwayat Transaksi", "💳 Riwayat Keuangan"])
    
    with tab1:
        st.markdown('<div class="svg-card">', unsafe_allow_html=True)
        st.subheader("📊 Performa Anda")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        period = st.selectbox("🗓️ Periode", ["Bulan Ini", "3 Bulan Terakhir", "Tahun Ini", "Semua Waktu"])
        
        # Calculate date range
        today = datetime.now()
        if period == "Bulan Ini":
            start_date = today.replace(day=1)
        elif period == "3 Bulan Terakhir":
            start_date = today - timedelta(days=90)
        elif period == "Tahun Ini":
            start_date = today.replace(month=1, day=1)
        else:
            start_date = None
        
        performance = get_warga_performance(user_id,
                                           start_date.strftime('%Y-%m-%d') if start_date else None,
                                           today.strftime('%Y-%m-%d'))
        
        # Better metrics display
        st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="stat-item" style="border-left-color: #1E88E5;">
                <h4>Total Transaksi</h4>
                <h2>{performance['total_transactions']}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-item" style="border-left-color: #4CAF50;">
                <h4>Total Berat Sampah</h4>
                <h2>{performance['total_weight']:.2f} Kg</h2>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-item" style="border-left-color: #FF9800;">
                <h4>Total Pendapatan</h4>
                <h2>Rp {performance['total_earned']:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Category breakdown
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Breakdown per Kategori")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.name, SUM(t.weight_kg) as total_weight, 
                   SUM(t.net_amount) as total_earned, COUNT(*) as count
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.warga_id = ?
            GROUP BY c.name
            ORDER BY total_earned DESC
        ''', (user_id,))
        category_breakdown = cursor.fetchall()
        conn.close()
        
        if category_breakdown:
            df_category = pd.DataFrame(
                [(cb['name'], cb['count'], f"{cb['total_weight']:.2f} Kg",
                  f"Rp {cb['total_earned']:,.0f}") for cb in category_breakdown],
                columns=['Kategori', 'Transaksi', 'Total Berat', 'Total Pendapatan']
            )
            st.dataframe(df_category, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                """
<div class="empty-state">
    """ + get_svg('recycle') + """
    <h3>Belum Ada Data Transaksi</h3>
    <p>Mulai jual sampah Anda untuk melihat statistik di sini</p>
</div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.subheader("📋 Riwayat Transaksi Penjualan Sampah")
        
        transactions = get_transactions(warga_id=user_id, limit=50)
        
        if transactions:
            df_trans = pd.DataFrame(
                [(t['category_name'], t['weight_kg'], f"Rp {t['price_per_kg']:,.0f}",
                  f"Rp {t['total_amount']:,.0f}", f"Rp {t['net_amount']:,.0f}",
                  t['transaction_date'], t['processed_by_name']) for t in transactions],
                columns=['Kategori', 'Berat (Kg)', 'Harga/Kg', 'Total', 'Diterima', 'Tanggal', 'Diproses Oleh']
            )
            st.dataframe(df_trans, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                """
<div class="empty-state">
    """ + get_svg('transaction') + """
    <h3>Belum Ada Transaksi</h3>
    <p>Riwayat transaksi penjualan sampah Anda akan muncul di sini</p>
</div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.subheader("💳 Riwayat Penarikan & Deposit")
        
        movements = get_financial_movements(warga_id=user_id, limit=50)
        
        if movements:
            df_movements = pd.DataFrame(
                [('Penarikan' if m['type'] == 'withdrawal' else 'Deposit',
                  f"Rp {m['amount']:,.0f}",
                  f"Rp {m['balance_before']:,.0f}",
                  f"Rp {m['balance_after']:,.0f}",
                  m['movement_date'],
                  m['processed_by_name'],
                  m['notes'] or '-') for m in movements],
                columns=['Tipe', 'Jumlah', 'Saldo Sebelum', 'Saldo Sesudah', 'Tanggal', 'Diproses Oleh', 'Catatan']
            )
            st.dataframe(df_movements, use_container_width=True, hide_index=True)
        else:
            st.markdown(
                """
<div class="empty-state">
    """ + get_svg('wallet') + """
    <h3>Belum Ada Riwayat Keuangan</h3>
    <p>Riwayat penarikan dan deposit Anda akan muncul di sini</p>
</div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown('</div>', unsafe_allow_html=True)

def dashboard_superuser():
    """Dashboard for Super User role"""
    # Header
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%);">
        <h1>⚡ Dashboard Super User</h1>
        <p>Kontrol penuh sistem - Kelola user, monitoring, dan akses semua fitur</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Kelola User", "🔐 Login Sebagai User Lain", "📜 Audit Log", "📊 Statistik Global"])
    
    with tab1:
        st.subheader("Kelola Pengguna")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Daftar Pengguna")
            
            users = get_all_users()
            
            if users:
                df_users = pd.DataFrame(
                    [(u['id'], u['username'], u['full_name'], u['role'], 
                      f"Rp {u['balance']:,.0f}", 'Aktif' if u['active'] else 'Non-Aktif',
                      u['created_at']) for u in users],
                    columns=['ID', 'Username', 'Nama Lengkap', 'Role', 'Saldo', 'Status', 'Dibuat']
                )
                st.dataframe(df_users, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada pengguna")
        
        with col2:
            st.markdown("### Tambah Pengguna Baru")
            
            with st.form("create_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_full_name = st.text_input("Nama Lengkap")
                new_role = st.selectbox("Role", ["warga", "panitia", "superuser"])
                
                submitted = st.form_submit_button("Tambah User", use_container_width=True)
                
                if submitted:
                    if new_username and new_password and new_full_name:
                        from auth import create_user
                        success, result = create_user(new_username, new_password, new_full_name, new_role)
                        
                        if success:
                            log_audit(st.session_state['user']['id'], 'CREATE_USER',
                                    f"Created user {new_username} with role {new_role}")
                            st.success(f"✅ User berhasil dibuat dengan ID: {result}")
                            st.rerun()
                        else:
                            st.error(f"❌ Gagal membuat user: {result}")
                    else:
                        st.warning("Silakan isi semua field!")
    
    with tab2:
        st.subheader("Login Sebagai User Lain")
        
        st.info("💡 Fitur ini memungkinkan Anda login sebagai user lain tanpa mengetahui password mereka")
        
        # Get all users except current user
        all_users = get_all_users()
        other_users = [u for u in all_users if u['id'] != st.session_state['user']['id']]
        
        if other_users:
            user_options = {f"{u['full_name']} ({u['username']}) - {u['role']}": u['id'] for u in other_users}
            
            selected_user = st.selectbox("Pilih User", list(user_options.keys()))
            
            if st.button("🔐 Login Sebagai User Ini"):
                target_user_id = user_options[selected_user]
                target_user = get_user_by_id(target_user_id)
                
                # Save original super user info
                st.session_state['superuser_original_id'] = st.session_state['user']['id']
                st.session_state['superuser_original_name'] = st.session_state['user']['full_name']
                
                # Switch to target user
                st.session_state['user'] = {
                    'id': target_user['id'],
                    'username': target_user['username'],
                    'full_name': target_user['full_name'],
                    'role': target_user['role']
                }
                
                # Log the action
                start_superuser_session(st.session_state['superuser_original_id'], target_user_id)
                log_audit(st.session_state['superuser_original_id'], 'LOGIN_AS_USER',
                         f"Super user logged in as {target_user['username']}")
                
                st.success(f"✅ Berhasil login sebagai {target_user['full_name']}")
                st.rerun()
        else:
            st.warning("Tidak ada user lain")
    
    with tab3:
        st.subheader("Audit Log")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Filter")
            
            all_users = get_all_users()
            user_filter_options = {"Semua User": None}
            user_filter_options.update({f"{u['full_name']} ({u['username']})": u['id'] for u in all_users})
            
            selected_user_filter = st.selectbox("Filter User", list(user_filter_options.keys()))
            
            limit = st.number_input("Jumlah Record", min_value=10, max_value=1000, value=100, step=10)
        
        with col2:
            st.markdown("### Log Aktivitas")
            
            user_id_filter = user_filter_options[selected_user_filter]
            logs = get_audit_logs(user_id=user_id_filter, limit=limit)
            
            if logs:
                df_logs = pd.DataFrame(
                    [(log['username'], log['full_name'], log['role'], log['action'],
                      log['details'] or '-', log['timestamp']) for log in logs],
                    columns=['Username', 'Nama', 'Role', 'Action', 'Details', 'Timestamp']
                )
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada log")
    
    with tab4:
        st.subheader("Statistik Global")
        
        # Overall statistics
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total users by role
        cursor.execute('''
            SELECT role, COUNT(*) as count
            FROM users
            WHERE active = 1
            GROUP BY role
        ''')
        user_stats = cursor.fetchall()
        
        # Total transactions
        cursor.execute('SELECT COUNT(*) FROM transactions')
        total_transactions = cursor.fetchone()[0]
        
        # Total revenue
        cursor.execute('SELECT SUM(total_amount) FROM transactions')
        total_revenue = cursor.fetchone()[0] or 0
        
        # Total weight
        cursor.execute('SELECT SUM(weight_kg) FROM transactions')
        total_weight = cursor.fetchone()[0] or 0
        
        # Committee earnings
        cursor.execute('SELECT SUM(amount) FROM committee_earnings')
        total_committee = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transaksi", total_transactions)
        
        with col2:
            st.metric("Total Berat", f"{total_weight:.2f} Kg")
        
        with col3:
            st.metric("Total Revenue", f"Rp {total_revenue:,.0f}")
        
        with col4:
            st.metric("Pendapatan Panitia", f"Rp {total_committee:,.0f}")
        
        st.markdown("---")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("### Pengguna per Role")
            if user_stats:
                df_user_stats = pd.DataFrame(
                    [(us['role'].title(), us['count']) for us in user_stats],
                    columns=['Role', 'Jumlah']
                )
                st.dataframe(df_user_stats, use_container_width=True, hide_index=True)
        
        with col_b:
            st.markdown("### Top 5 Warga Teraktif")
            
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.full_name, COUNT(*) as transaction_count,
                       SUM(t.weight_kg) as total_weight,
                       SUM(t.net_amount) as total_earned
                FROM transactions t
                JOIN users u ON t.warga_id = u.id
                GROUP BY t.warga_id
                ORDER BY transaction_count DESC
                LIMIT 5
            ''')
            top_warga = cursor.fetchall()
            conn.close()
            
            if top_warga:
                df_top = pd.DataFrame(
                    [(tw['full_name'], tw['transaction_count'], f"{tw['total_weight']:.2f} Kg",
                      f"Rp {tw['total_earned']:,.0f}") for tw in top_warga],
                    columns=['Nama', 'Transaksi', 'Total Berat', 'Total Pendapatan']
                )
                st.dataframe(df_top, use_container_width=True, hide_index=True)

def main():
    """Main application"""
    
    # Check if user is logged in
    if not st.session_state['user']:
        login_page()
        return
    
    # Sidebar
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #1E88E5 0%, #0D47A1 100%); border-radius: 10px; margin-bottom: 1rem;">
            <h1 style="color: white; margin: 0; font-size: 1.8rem;">♻️ Bank Sampah Wani Luru</h1>
            <p style="color: #E3F2FD; margin: 0.5rem 0 0 0; font-size: 0.9rem;">Sistem Manajemen Digital</p>
        </div>
        """, unsafe_allow_html=True)
        
        # User info
        user = st.session_state['user']
        role_colors = {
            'superuser': 'role-superuser',
            'panitia': 'role-panitia',
            'warga': 'role-warga'
        }
        role_icons = {
            'superuser': '⚡',
            'panitia': '📊',
            'warga': '👤'
        }
        
        # Show superuser banner if applicable
        if check_superuser_session():
            st.markdown("""
            <div class="info-card" style="background: #FFF3E0; border-color: #FF9800;">
                <h4 style="color: #FF9800; margin: 0;">🔐 Mode Super User</h4>
                <p style="margin: 0.5rem 0 0 0;">Login sebagai: <strong>{}</strong></p>
                <p style="margin: 0.3rem 0 0 0; font-size: 0.85rem;">Akun asli: {}</p>
            </div>
            """.format(user['full_name'], st.session_state['superuser_original_name']), unsafe_allow_html=True)
            if st.button("🔙 Kembali ke Super User", use_container_width=True):
                end_superuser_session()
        else:
            st.markdown(f"""
            <div class="info-card">
                <div style="text-align: center;">
                    <h2 style="margin: 0; color: #0D47A1; font-size: 1.3rem;">{role_icons.get(user['role'], '👤')} {user['full_name']}</h2>
                    <span class="role-badge {role_colors.get(user['role'], 'role-warga')}" style="margin-top: 0.5rem;">
                        {user['role'].upper()}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Quick stats for warga
        if user['role'] == 'warga':
            balance = get_user_balance(user['id'])
            st.markdown(f"""
            <div class="metric-card">
                <p style="margin: 0; font-size: 0.9rem;">💰 Saldo Anda</p>
                <h2 style="margin: 0.5rem 0 0 0;">Rp {balance:,.0f}</h2>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation help
        with st.expander("📖 Panduan Cepat"):
            if user['role'] == 'superuser':
                st.markdown("""
                **Super User dapat:**
                - ✅ Kelola semua pengguna
                - ✅ Login sebagai user lain
                - ✅ Lihat audit log
                - ✅ Monitoring sistem
                """)
            elif user['role'] == 'panitia':
                st.markdown("""
                **Panitia dapat:**
                - ✅ Input transaksi sampah
                - ✅ Kelola keuangan warga
                - ✅ Buat laporan
                - ✅ Monitor performa
                """)
            else:  # warga
                st.markdown("""
                **Warga dapat:**
                - ✅ Cek saldo
                - ✅ Lihat performa
                - ✅ Riwayat transaksi
                - ✅ Riwayat keuangan
                """)
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Keluar dari Sistem", use_container_width=True, type="primary"):
            log_audit(user['id'], 'LOGOUT', f"User logged out")
            st.session_state['user'] = None
            if 'superuser_original_id' in st.session_state:
                del st.session_state['superuser_original_id']
                del st.session_state['superuser_original_name']
            st.rerun()
        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center;">
            <p style="font-size: 0.75rem; color: #1E88E5; margin: 0;">💙 Bank Sampah Wani Luru</p>
            <p style="font-size: 0.7rem; color: #90CAF9; margin: 0.3rem 0 0 0;">© 2026 v1.0</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show appropriate dashboard based on role
    role = st.session_state['user']['role']
    
    if role == 'superuser':
        dashboard_superuser()
    elif role == 'pengepul':
        st.info("Role pengepul telah digabung ke panitia. Mengarahkan ke dashboard panitia.")
        dashboard_panitia()
    elif role == 'panitia':
        dashboard_panitia()
    elif role == 'warga':
        dashboard_warga()
    else:
        st.error("Role tidak dikenali!")

if __name__ == '__main__':
    main()
