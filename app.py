import streamlit as st
from database import initialize_system, get_connection, get_setting, set_setting
from auth import authenticate_user, log_audit, check_superuser_session, end_superuser_session, get_all_users, start_superuser_session, get_user_by_id, create_user, update_user, update_user_password, delete_user
from utils import *
from svg_icons import get_svg
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import io
import uuid
import random
import os
import tempfile
import re
from fpdf import FPDF
import matplotlib.pyplot as plt

DUMMY_TAG = "[DUMMY DATA]"


def _pdf_output_bytes(pdf):
    output = pdf.output(dest="S")
    if isinstance(output, bytes):
        return output
    if isinstance(output, bytearray):
        return bytes(output)
    if isinstance(output, memoryview):
        return output.tobytes()
    return output.encode("latin-1")


def _render_trend_chart(df_trend, x_col='Tanggal', y_col='Total', y_title='Nilai Transaksi (Rp)'):
    chart_df = df_trend.copy()
    chart_df[x_col] = pd.to_datetime(chart_df[x_col])
    chart_df = chart_df.sort_values(x_col)

    base = alt.Chart(chart_df).encode(
        x=alt.X(
            f'{x_col}:T',
            title='Tanggal',
            axis=alt.Axis(format='%d %b', labelAngle=-20, grid=False),
        )
    )

    area = base.mark_area(color='#1E88E5', opacity=0.12).encode(
        y=alt.Y(f'{y_col}:Q', title=y_title, axis=alt.Axis(format='~s')),
        tooltip=[
            alt.Tooltip(f'{x_col}:T', title='Tanggal', format='%d %B %Y'),
            alt.Tooltip(f'{y_col}:Q', title='Total', format=',.0f'),
        ],
    )

    line = base.mark_line(color='#1E88E5', strokeWidth=3).encode(
        y=alt.Y(f'{y_col}:Q', title=y_title)
    )

    points = base.mark_circle(color='#0D47A1', size=55).encode(
        y=alt.Y(f'{y_col}:Q', title=y_title),
        tooltip=[
            alt.Tooltip(f'{x_col}:T', title='Tanggal', format='%d %B %Y'),
            alt.Tooltip(f'{y_col}:Q', title='Total', format=',.0f'),
        ],
    )

    chart = (area + line + points).properties(height=320).interactive()
    st.altair_chart(chart, use_container_width=True)


def _render_category_bar_chart(df_cat, category_col='Kategori', value_col='Total Berat (Kg)', value_title='Total Berat (Kg)'):
    chart_df = df_cat.copy()
    chart_df = chart_df.sort_values(value_col, ascending=False)

    base = alt.Chart(chart_df)

    bars = base.mark_bar(color='#4CAF50', cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
        y=alt.Y(f'{category_col}:N', sort='-x', title='Kategori'),
        x=alt.X(f'{value_col}:Q', title=value_title, axis=alt.Axis(grid=True)),
        tooltip=[
            alt.Tooltip(f'{category_col}:N', title='Kategori'),
            alt.Tooltip(f'{value_col}:Q', title=value_title, format=',.2f'),
        ],
    )

    labels = base.mark_text(align='left', baseline='middle', dx=6, color='#1B5E20').encode(
        y=alt.Y(f'{category_col}:N', sort='-x'),
        x=alt.X(f'{value_col}:Q'),
        text=alt.Text(f'{value_col}:Q', format=',.2f'),
    )

    chart = (bars + labels).properties(height=360)
    st.altair_chart(chart, use_container_width=True)


def _render_top_warga_table(df_top, count_col='Jumlah Transaksi'):
    table_df = df_top.copy().sort_values(count_col, ascending=False).reset_index(drop=True)
    table_df.insert(0, 'Peringkat', [f"#{i}" for i in range(1, len(table_df) + 1)])

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=260,
        column_config={
            'Peringkat': st.column_config.TextColumn('Rank', width='small'),
            count_col: st.column_config.NumberColumn(count_col, format='%d'),
        },
    )


def _build_category_excel_template():
    categories = get_all_categories()
    template_rows = [
        {
            'Nama Kategori': c['name'],
            'Harga/Kg': float(c['price_per_kg']),
        }
        for c in categories
    ]
    template_df = pd.DataFrame(template_rows, columns=['Nama Kategori', 'Harga/Kg'])
    notes_df = pd.DataFrame(
        {
            'Petunjuk': [
                'Gunakan sheet Kategori untuk replace daftar kategori.',
                'Kolom wajib: Nama Kategori dan Harga/Kg.',
                'Nama kategori yang sudah ada akan di-update harganya.',
                'Kategori baru akan ditambahkan otomatis.',
                'Kategori yang tidak ada di file akan dihapus jika belum pernah dipakai transaksi.',
                'Tidak boleh ada duplikat nama kategori dalam file (tanpa membedakan huruf besar/kecil).',
            ]
        }
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        template_df.to_excel(writer, sheet_name='Kategori', index=False)
        notes_df.to_excel(writer, sheet_name='Petunjuk', index=False)
    buffer.seek(0)
    return buffer.getvalue()


def _normalize_excel_header(value):
    return re.sub(r'[^a-z0-9]', '', str(value).strip().lower())


def _parse_price_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    cleaned = re.sub(r'[^0-9,.-]', '', text)
    if not cleaned:
        return None

    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned and '.' not in cleaned:
        parts = cleaned.split(',')
        if len(parts) > 1 and len(parts[-1]) in (1, 2):
            cleaned = '.'.join(parts)
        else:
            cleaned = ''.join(parts)

    try:
        return float(cleaned)
    except ValueError:
        return None


def _bulk_replace_categories_from_excel(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Kategori')
    except ValueError:
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as exc:
            return False, {'error': f'File tidak bisa dibaca: {exc}'}
    except Exception as exc:
        return False, {'error': f'File tidak bisa dibaca: {exc}'}

    if df.empty:
        return False, {'error': 'File Excel kosong.'}

    col_lookup = {_normalize_excel_header(col): col for col in df.columns}
    name_col = None
    price_col = None

    for candidate in ['namakategori', 'kategori', 'category', 'name']:
        if candidate in col_lookup:
            name_col = col_lookup[candidate]
            break

    for candidate in ['hargakg', 'hargaperkg', 'harga', 'priceperkg', 'price']:
        if candidate in col_lookup:
            price_col = col_lookup[candidate]
            break

    if not name_col or not price_col:
        return False, {'error': 'Kolom wajib tidak ditemukan. Gunakan template resmi (Nama Kategori, Harga/Kg).'}

    entries = {}
    errors = []
    duplicate_lines = []

    for idx, row in df.iterrows():
        line_no = idx + 2
        raw_name = row.get(name_col)
        raw_price = row.get(price_col)

        if (pd.isna(raw_name) or str(raw_name).strip() == '') and pd.isna(raw_price):
            continue

        category_name = '' if pd.isna(raw_name) else str(raw_name).strip()
        if not category_name:
            errors.append({'Baris': line_no, 'Error': 'Nama Kategori kosong'})
            continue

        parsed_price = _parse_price_value(raw_price)
        if parsed_price is None or parsed_price <= 0:
            errors.append({'Baris': line_no, 'Error': 'Harga/Kg tidak valid (harus > 0)'})
            continue

        key = category_name.casefold()
        if key in entries:
            duplicate_lines.append(line_no)
        entries[key] = {'name': category_name, 'price': parsed_price}

    if duplicate_lines:
        return False, {
            'error': 'Terdapat nama kategori duplikat di file. Perbaiki dulu lalu upload ulang.',
            'errors': [
                {'Baris': ln, 'Error': 'Duplikat nama kategori (case-insensitive)'} for ln in duplicate_lines
            ],
        }

    if not entries:
        return False, {'error': 'Tidak ada data valid untuk diproses.', 'errors': errors}

    categories = get_all_categories()
    existing = {c['name'].strip().casefold(): c for c in categories}

    created = 0
    updated = 0
    skipped = 0
    deleted = 0
    blocked_delete = []

    for key, payload in entries.items():
        name = payload['name']
        price = payload['price']

        if key in existing:
            current = existing[key]
            if abs(float(current['price_per_kg']) - float(price)) < 1e-9:
                skipped += 1
                continue
            update_category_price(current['id'], price)
            updated += 1
        else:
            success, message = create_category(name, price)
            if success:
                created += 1
            else:
                errors.append({'Baris': '-', 'Error': f'{name}: {message}'})

    conn = get_connection()
    cursor = conn.cursor()
    for key, category in existing.items():
        if key in entries:
            continue

        cursor.execute('SELECT COUNT(*) FROM transactions WHERE category_id = ?', (category['id'],))
        usage_count = cursor.fetchone()[0]
        if usage_count and usage_count > 0:
            blocked_delete.append(
                {
                    'Kategori': category['name'],
                    'Alasan': f'Sudah dipakai {usage_count} transaksi',
                }
            )
            continue

        success, message = delete_category(category['id'])
        if success:
            deleted += 1
        else:
            errors.append({'Baris': '-', 'Error': f"Gagal hapus {category['name']}: {message}"})
    conn.close()

    return True, {
        'created': created,
        'updated': updated,
        'skipped': skipped,
        'deleted': deleted,
        'blocked_delete': blocked_delete,
        'errors': errors,
    }


def _render_category_excel_uploader(section_key):
    st.markdown('### 📥 Update Daftar Kategori via Excel')
    st.caption('Upload file .xlsx untuk replace daftar kategori dan harga.')

    result_key = f'category_upload_result_{section_key}'
    saved_result = st.session_state.pop(result_key, None)
    if saved_result:
        st.success(
            f"✅ Sinkron selesai. Ditambah: {saved_result['created']}, Diupdate: {saved_result['updated']}, "
            f"Dihapus: {saved_result['deleted']}, Tidak berubah: {saved_result['skipped']}"
        )
        if saved_result['blocked_delete']:
            st.warning(f"⚠️ {len(saved_result['blocked_delete'])} kategori tidak bisa dihapus karena sudah dipakai transaksi.")
            st.dataframe(pd.DataFrame(saved_result['blocked_delete']), use_container_width=True, hide_index=True)
        if saved_result['errors']:
            st.warning(f"⚠️ Ada {len(saved_result['errors'])} baris gagal diproses.")
            st.dataframe(pd.DataFrame(saved_result['errors']), use_container_width=True, hide_index=True)

    template_bytes = _build_category_excel_template()
    st.download_button(
        '⬇️ Download Template Excel',
        data=template_bytes,
        file_name='template_update_kategori.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        use_container_width=True,
        key=f'download_template_{section_key}',
    )

    uploaded_file = st.file_uploader(
        'Upload file kategori (.xlsx)',
        type=['xlsx'],
        key=f'upload_category_excel_{section_key}',
        help='Gunakan template terbaru agar data saat ini terisi otomatis.',
    )

    if st.button('🔄 Proses Replace dari Excel', type='primary', use_container_width=True, key=f'process_excel_{section_key}'):
        if uploaded_file is None:
            st.warning('Silakan upload file Excel terlebih dahulu.')
            return

        success, result = _bulk_replace_categories_from_excel(uploaded_file)
        if not success:
            st.error(result.get('error', 'Gagal memproses file Excel.'))
            if result.get('errors'):
                st.dataframe(pd.DataFrame(result['errors']), use_container_width=True, hide_index=True)
            return

        user_id = st.session_state.get('user', {}).get('id')
        if user_id:
            log_audit(
                user_id,
                'BULK_REPLACE_CATEGORY_EXCEL',
                f"created={result['created']}, updated={result['updated']}, deleted={result['deleted']}, skipped={result['skipped']}",
            )

        st.session_state[result_key] = result
        st.rerun()


def _render_audit_log_tab(section_key, default_limit=200):
    st.subheader("📜 Audit Log Aktivitas User")
    st.caption("Menampilkan seluruh aktivitas user secara transparan dengan filter user dan rentang tanggal.")

    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1])

    all_users = get_all_users()
    user_filter_options = {"Semua User": None}
    user_filter_options.update({f"{u['full_name']} ({u['username']})": u['id'] for u in all_users})

    with filter_col1:
        selected_user_filter = st.selectbox(
            "Filter User",
            list(user_filter_options.keys()),
            key=f"audit_user_{section_key}",
        )

    with filter_col2:
        start_date_filter = st.date_input(
            "Dari Tanggal",
            value=datetime.now() - timedelta(days=30),
            key=f"audit_start_{section_key}",
        )

    with filter_col3:
        end_date_filter = st.date_input(
            "Sampai Tanggal",
            value=datetime.now(),
            key=f"audit_end_{section_key}",
        )

    with filter_col4:
        limit = st.number_input(
            "Jumlah Record",
            min_value=10,
            max_value=5000,
            value=default_limit,
            step=10,
            key=f"audit_limit_{section_key}",
        )

    if start_date_filter > end_date_filter:
        st.warning("Rentang tanggal tidak valid. Pastikan tanggal mulai <= tanggal akhir.")
        return

    logs = get_audit_logs(
        user_id=user_filter_options[selected_user_filter],
        limit=int(limit),
        start_date=start_date_filter,
        end_date=end_date_filter,
    )

    if not logs:
        st.info("Tidak ada log pada filter yang dipilih.")
        return

    df_logs = pd.DataFrame(
        [
            (
                log['timestamp'],
                log['username'],
                log['full_name'],
                _display_role_label(log['role']),
                log['action'],
                log['details'] or '-',
            )
            for log in logs
        ],
        columns=['Timestamp', 'Username', 'Nama', 'Role', 'Action', 'Details'],
    )
    st.dataframe(df_logs, use_container_width=True, hide_index=True)


def _get_transaction_participant_users():
    """Users eligible as transaction sellers: warga + admin/panitia + inputer."""
    allowed_roles = {'warga', 'panitia', 'admin', 'inputer'}
    return [u for u in get_all_users() if u.get('role') in allowed_roles and u.get('active', 1) == 1]

# Page configuration
st.set_page_config(
    page_title="Bank Sampah Wani Luru RW 1 - Sistem Manajemen",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="collapsed"
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
    
    /* Premium Metric Card */
    .metric-card-container {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border: 1px solid #E3F2FD;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
    }
    
    .metric-card-container:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(30,136,229,0.15);
        border-color: #BBDEFB;
    }

    .metric-card-container::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, rgba(30,136,229,0.1) 0%, rgba(255,255,255,0) 100%);
        border-radius: 0 0 0 100%;
        z-index: 0;
    }
    
    .metric-title {
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        z-index: 1;
        position: relative;
    }
    
    .metric-value {
        color: #1E293B;
        font-size: 1.8rem;
        font-weight: 700;
        z-index: 1;
        position: relative;
        line-height: 1.2;
    }

    .metric-icon {
        position: absolute;
        right: 15px;
        top: 15px;
        font-size: 2.5rem;
        opacity: 0.2;
        z-index: 0;
        filter: grayscale(100%);
        transition: all 0.3s ease;
    }
    
    .metric-card-container:hover .metric-icon {
        opacity: 0.8;
        filter: grayscale(0%);
        transform: scale(1.1) rotate(5deg);
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
    
    .role-inputer {
        background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
        color: white;
    }

    .role-admin, .role-panitia {
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

def dashboard_admin_home():
    """New specialized dashboard for Admin Home"""
    st.subheader("📊 Dashboard Utama")
    
    # --- Top Cards ---
    col1, col2, col3, col4 = st.columns(4)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total Transactions (All time)
    cursor.execute('SELECT COUNT(*) FROM transactions')
    total_trans = cursor.fetchone()[0]
    
    # 2. Total Weight
    cursor.execute('SELECT SUM(weight_kg) FROM transactions')
    total_weight = cursor.fetchone()[0] or 0
    
    # 3. Total Revenue
    cursor.execute('SELECT SUM(total_amount) FROM transactions')
    total_rev = cursor.fetchone()[0] or 0
    
    # 4. Active Warga
    cursor.execute('SELECT COUNT(DISTINCT warga_id) FROM transactions')
    active_warga = cursor.fetchone()[0]
    
    conn.close()
    
    with col1:
        ui_metric_card("Total Transaksi", total_trans, icon="🧾")
    with col2:
        ui_metric_card("Total Berat", f"{total_weight:,.2f} Kg", icon="⚖️")
    with col3:
        ui_metric_card("Total Omzet", f"Rp {total_rev:,.0f}", icon="💰")
    with col4:
        ui_metric_card("Warga Aktif", active_warga, icon="👥")
        
    st.markdown("---")
    
    # --- Charts ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("### 📈 Tren Transaksi Harian (30 Hari Terakhir)")
        # Get daily transaction value
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date(transaction_date) as d, SUM(total_amount) as total
            FROM transactions 
            WHERE date(transaction_date) BETWEEN ? AND ?
            GROUP BY date(transaction_date)
            ORDER BY d
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        daily_data = cursor.fetchall()
        conn.close()
        
        if daily_data:
            df_trend = pd.DataFrame(daily_data, columns=['Tanggal', 'Total'])
            df_trend['Tanggal'] = pd.to_datetime(df_trend['Tanggal'])
            _render_trend_chart(df_trend)
        else:
            st.info("Belum ada data transaksi 30 hari terakhir")

    with c2:
        st.markdown("### 🏆 Top 5 Warga Teraktif")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.full_name, COUNT(*) as cnt
            FROM transactions t
            JOIN users u ON t.warga_id = u.id
            GROUP BY t.warga_id
            ORDER BY cnt DESC
            LIMIT 5
        ''')
        top_warga = cursor.fetchall()
        conn.close()
        
        if top_warga:
            # Horizontal bar chart ref
            df_top = pd.DataFrame(top_warga, columns=['Nama', 'Jumlah Transaksi'])
            _render_top_warga_table(df_top, count_col='Jumlah Transaksi')
        else:
            st.info("Belum ada data")

    # Categories Pie/Bar
    st.markdown("### ♻️ Komposisi Kategori Sampah (Berat)")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.name, SUM(t.weight_kg) as total_w
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        GROUP BY t.category_id
        ORDER BY total_w DESC
        LIMIT 10
    ''')
    cat_stats = cursor.fetchall()
    conn.close()
    
    if cat_stats:
        df_cat = pd.DataFrame(cat_stats, columns=['Kategori', 'Total Berat (Kg)'])
        _render_category_bar_chart(df_cat)


def ui_metric_card(title, value, icon="📊", color="#1E88E5", help_text=None):
    """Render a premium metric card using HTML/CSS."""
    help_html = f'<div title="{help_text}" style="cursor:help; display:inline-block; margin-left:5px;">ℹ️</div>' if help_text else ""
    st.markdown(f"""
    <div class="metric-card-container" style="border-left: 4px solid {color};">
        <div class="metric-icon">{icon}</div>
        <div class="metric-title">{title} {help_html}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state['user'] = None


def _display_role_label(role: str, uppercase: bool = False) -> str:
    """Return human-friendly role label while keeping stored values stable."""
    label_map = {
        'superuser': 'Super User',
        'inputer': 'Panitia',
        'panitia': 'Admin',  # legacy stored value
        'admin': 'Admin',
        'warga': 'Warga',
    }
    label = label_map.get(role, role.title())
    return label.upper() if uppercase else label


def _role_badge_class(role: str) -> str:
    """Map role to CSS badge class with admin alias for panitia."""
    return {
        'superuser': 'role-superuser',
        'inputer': 'role-inputer',
        'panitia': 'role-admin',
        'admin': 'role-admin',
        'warga': 'role-warga',
    }.get(role, 'role-warga')


def _role_icon(role: str) -> str:
    """Return role emoji icon with admin alias for panitia."""
    return {
        'superuser': '⚡',
        'inputer': '📝',
        'panitia': '📊',
        'admin': '📊',
        'warga': '👤',
    }.get(role, '👤')


def _ensure_user(username, password, full_name, nickname, address, rt, rw, whatsapp, role):
    """Get or create a user and return (success, user_id or message)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return True, row['id']
    conn.close()
    success, result = create_user(username, password, full_name, role, nickname, address, rt, rw, whatsapp)
    return success, result if success else result


def seed_dummy_data(superuser_id):
    """Populate richer demo data: 50 warga, 100 transaksi (2025-2026), plus an admin handler."""

    random.seed(42)

    # Build dummy users
    dummy_users = [
        {
            'username': 'demo_admin',
            'password': 'demo123',
            'full_name': 'Admin Demo',
            'nickname': 'Pak Demo',
            'address': 'Jl. Contoh Admin No. 8',
            'rt': '01',
            'rw': '02',
            'whatsapp': '081234560001',
            'role': 'panitia',
        }
    ]

    # Generate 50 warga accounts
    for i in range(1, 51):
        dummy_users.append({
            'username': f'demo_warga{i}',
            'password': 'demo123',
            'full_name': f'Warga Demo {i:02d}',
            'nickname': f'Demo {i:02d}',
            'address': f'Jl. Contoh Warga No. {i}',
            'rt': f"{(i % 10) + 1:02d}",
            'rw': f"{(i % 15) + 1:02d}",
            'whatsapp': f"08123456{1000 + i:03d}",
            'role': 'warga',
        })

    # Ensure users exist
    user_ids = {}
    for du in dummy_users:
        success, res = _ensure_user(
            du['username'], du['password'], du['full_name'],
            du['nickname'], du['address'], du['rt'], du['rw'], du['whatsapp'], du['role']
        )
        if not success:
            return False, f"Gagal menambahkan user {du['username']}: {res}"
        user_ids[du['username']] = res

    panitia_id = user_ids['demo_admin']
    warga_ids = [user_ids[k] for k in user_ids if k.startswith('demo_warga')]

    # Ensure categories exist and have variety
    categories = {c['name']: c['id'] for c in get_all_categories()}
    needed_categories = {
        'Plastik Botol': 3200,
        'Kardus': 1700,
        'Kaleng Aluminium': 5200,
        'Elektronik Kecil': 8500,
        'Kertas Campur': 1200,
        'Minyak Jelantah': 6000,
    }
    for name, price in needed_categories.items():
        if name not in categories:
            created, _ = create_category(name, price)
            if not created:
                return False, f"Gagal menambah kategori {name}"
    categories = {c['name']: c['id'] for c in get_all_categories()}
    category_ids = list(categories.values())

    # Prepare date range 2025-01-01 to 2026-12-31
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)
    total_days = (end_date - start_date).days

    # Create 100 transactions with random warga/category/weight/date
    for idx in range(100):
        warga_id = random.choice(warga_ids)
        category_id = random.choice(category_ids)
        weight = round(random.uniform(1.0, 20.0), 2)
        t_date = start_date + timedelta(days=random.randint(0, total_days))
        note = f"{DUMMY_TAG} Transaksi demo ke-{idx + 1}"
        create_transaction(
            warga_id,
            category_id,
            weight,
            panitia_id,
            notes=note,
            batch_id=str(uuid.uuid4()),
            transaction_date=t_date,
        )

    # Seed a few deposits/withdrawals for the first few warga to show movement history
    for warga_id in warga_ids[:5]:
        process_deposit(
            warga_id,
            random.randint(50_000, 200_000),
            panitia_id,
            notes=f"{DUMMY_TAG} Setoran saldo awal",
        )
        process_withdrawal(
            warga_id,
            random.randint(20_000, 80_000),
            panitia_id,
            notes=f"{DUMMY_TAG} Penarikan demo",
        )

    set_setting('dummy_data_active', '1')
    log_audit(superuser_id, 'DUMMY_DATA_ON', 'Superuser menyalakan data dummy demo (50 warga, 100 transaksi)')
    return True, "Data dummy detail (50 warga, 100 transaksi) berhasil dibuat"


def clear_dummy_data(superuser_id):
    """Remove all demo data without touching real records."""
    conn = get_connection()
    cursor = conn.cursor()

    # Delete committee earnings tied to dummy transactions first
    cursor.execute(
        "DELETE FROM committee_earnings WHERE transaction_id IN (SELECT id FROM transactions WHERE notes LIKE ?)",
        (f"%{DUMMY_TAG}%",),
    )

    # Delete dummy transactions
    cursor.execute("DELETE FROM transactions WHERE notes LIKE ?", (f"%{DUMMY_TAG}%",))

    # Delete dummy financial movements
    cursor.execute("DELETE FROM financial_movements WHERE notes LIKE ?", (f"%{DUMMY_TAG}%",))

    # Remove dummy users last to avoid FK issues
    cursor.execute(
        "DELETE FROM users WHERE username = ? OR username LIKE ?",
        ('demo_admin', 'demo_warga%'),
    )

    conn.commit()
    conn.close()

    set_setting('dummy_data_active', '0')
    log_audit(superuser_id, 'DUMMY_DATA_OFF', 'Superuser mematikan data dummy demo')
    return True, "Data dummy berhasil dihapus"

def sidebar_login():
    """Display login form in sidebar"""
    st.sidebar.markdown("### 🔐 Login Akses")
    
    with st.sidebar.form("login_form"):
        username = st.text_input("👤 Username", placeholder="Username")
        password = st.text_input("🔒 Password", type="password", placeholder="Password")
        
        st.markdown("")
        submitted = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
        
        if submitted:
            if username and password:
                user = authenticate_user(username, password)
                if user:
                    st.session_state['user'] = user
                    log_audit(user['id'], 'LOGIN', f"User {username} logged in")
                    st.success(f"✅ Login sukses!")
                    st.rerun()
                else:
                    st.error("❌ Akun tidak ditemukan")
            else:
                st.warning("⚠️ Isi username & password")

    # Help section in sidebar
    with st.sidebar.expander("ℹ️ Bantuan"):
        st.markdown("""
        Hubungi Admin jika belum memiliki akun.
        """)
            

    
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #1E88E5; font-size: 0.9rem;">
            <p>💙 Bank Sampah Wani Luru RW 1 - Untuk Lingkungan yang Lebih Bersih dan Sejahtera</p>
            <p style="font-size: 0.8rem; color: #90CAF9;">© 2026 <a href="https://www.linkedin.com/in/galihprime/" target="_blank" style="color: #90CAF9; text-decoration: none;">Galih Primananda</a></p>
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

            st.markdown("---")
            _render_category_excel_uploader('pengepul')
    
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
                ui_metric_card("Total Transaksi", total_trans, icon="🧾")
            
            with metric_col2:
                ui_metric_card("Total Berat Dibeli", f"{total_weight:.2f} Kg", icon="⚖️")
            
            with metric_col3:
                ui_metric_card("Total Revenue", f"Rp {total_rev:,.0f}", icon="💰")
            
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
        st.subheader("Riwayat Transaksi dari Admin")
        
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
                ui_metric_card("Jumlah Transaksi", total_transactions, icon="🧾")
            
            with metric_col2:
                ui_metric_card("Total Berat", f"{total_weight_trans:.2f} Kg", icon="⚖️")
            
            with metric_col3:
                ui_metric_card("Total Revenue", f"Rp {total_revenue_trans:,.0f}", icon="💰")
            
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

# Helpers for PDF laporan with charts
# Helpers for PDF laporan with charts
def _create_bar_chart(data, title, xlabel, color='#1E88E5', top_n=10, ascending=False):
    """Create a horizontal bar chart."""
    if not data:
        return None

    # Sort and slice
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=not ascending)[:top_n]
    if not sorted_items:
        return None
    
    # Reverse for plotting (bottom-to-top)
    labels = [k for k, v in sorted_items][::-1]
    values = [v for k, v in sorted_items][::-1]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(labels, values, color=color, alpha=0.8)
    
    # Value labels
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + (max(values) * 0.01) if values else 0
        ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                va='center', fontsize=8)

    ax.set_title(title, fontsize=10, pad=10)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=8)
    
    # Remove borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _create_dual_line_chart(dates, sales, fees):
    """Create a dual line chart for sales and committee revenue."""
    if not dates:
        return None

    fig, ax1 = plt.subplots(figsize=(7, 4))

    # Plot Sales (Total Transaction Value)
    color = '#1E88E5'
    ax1.set_xlabel('Tanggal', fontsize=8)
    ax1.set_ylabel('Transaksi Penjualan (Rp)', color=color, fontsize=8)
    line1 = ax1.plot(dates, sales, marker='o', color=color, linewidth=2, label='Transaksi')
    ax1.tick_params(axis='y', labelcolor=color, labelsize=8)
    ax1.tick_params(axis='x', labelsize=8, rotation=30)
    ax1.grid(True, linestyle='--', alpha=0.3)

    # Instantiate a second axes that shares the same x-axis
    ax2 = ax1.twinx()
    color = '#4CAF50'
    ax2.set_ylabel('Pendapatan Panitia (Rp)', color=color, fontsize=8)
    line2 = ax2.plot(dates, fees, marker='s', color=color, linewidth=2, linestyle='--', label='Pendapatan Panitia')
    ax2.tick_params(axis='y', labelcolor=color, labelsize=8)

    # Added title and legend
    plt.title("Tren Transaksi Penjualan vs Pendapatan Panitia", fontsize=10, pad=10)
    
    # Legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', fontsize=8)

    plt.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _buffer_to_tempfile(buffer, suffix=".png"):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(buffer.getvalue())
    tmp.close()
    return tmp.name


def generate_pdf_laporan(transactions, start_date, end_date):
    start_label = start_date.strftime("%d %B %Y") if start_date else "-"
    end_label = end_date.strftime("%d %B %Y") if end_date else "-"

    # --- Data Processing ---
    total_transactions = len(transactions)
    total_weight = sum((t["weight_kg"] or 0) for t in transactions)
    total_revenue = sum((t["total_amount"] or 0) for t in transactions)
    total_fee = sum((t["committee_fee"] or 0) for t in transactions)
    warga_unique = len({t["warga_id"] for t in transactions})

    # Aggregations
    category_sales = {} # name -> total_amount
    category_weights = {} # name -> total_weight
    warga_activity = {} # name -> count
    daily_sales = {} # date_str -> amount
    daily_fees = {} # date_str -> amount
    
    for t in transactions:
        # Category stats
        cat_name = t["category_name"]
        amount = t["total_amount"] or 0
        weight = t["weight_kg"] or 0
        category_sales[cat_name] = category_sales.get(cat_name, 0) + amount
        category_weights[cat_name] = category_weights.get(cat_name, 0) + weight

        # Warga stats
        w_name = t["warga_name"]
        warga_activity[w_name] = warga_activity.get(w_name, 0) + 1

        # Daily stats
        d_key = str(t["transaction_date"])[:10]
        daily_sales[d_key] = daily_sales.get(d_key, 0) + amount
        daily_fees[d_key] = daily_fees.get(d_key, 0) + (t["committee_fee"] or 0)

    # Prepare chart data
    sorted_dates = sorted(list(set(daily_sales.keys()) | set(daily_fees.keys())))
    date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in sorted_dates]
    sales_values = [daily_sales.get(d, 0) for d in sorted_dates]
    fee_values = [daily_fees.get(d, 0) for d in sorted_dates]

    # Generate Charts
    chart_best_cat = _create_bar_chart(category_sales, "Top 10 Kategori Terlaku (Berdasarkan Nilai Rp)", "Total Penjualan (Rp)", top_n=10, ascending=False)
    chart_worst_cat = _create_bar_chart(category_sales, "Top 10 Kategori Tidak Laku (Berdasarkan Nilai Rp)", "Total Penjualan (Rp)", color='#FF5722', top_n=10, ascending=True)
    chart_active_warga = _create_bar_chart(warga_activity, "Top 10 Warga Teraktif", "Jumlah Transaksi", color='#4CAF50', top_n=10, ascending=False)
    chart_trend = _create_dual_line_chart(date_objs, sales_values, fee_values)

    # --- PDF Generation ---
    class LaporanPDF(FPDF):
        def header(self):
            # No header on cover page (page 1)
            if self.page_no() > 1:
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(128)
                self.cell(0, 10, 'Bank Sampah Wani Luru RW 1 - Laporan Kinerja Operasional', 0, 0, 'R')
                self.ln(10)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')

    pdf = LaporanPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # 1. Halaman Judul (Cover)
    pdf.add_page()
    pdf.set_draw_color(30, 136, 229) # Blue border
    pdf.set_line_width(1)
    pdf.rect(10, 10, 190, 277)
    
    pdf.ln(60)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(13, 71, 161) # Dark Blue
    pdf.multi_cell(0, 15, "LAPORAN KINERJA\nBANK SAMPAH WANI LURU", align='C')
    
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(0)
    pdf.cell(0, 10, f"Periode: {start_label} s.d. {end_label}", ln=True, align='C')
    
    pdf.ln(80)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Disusun Oleh:", ln=True, align='C')
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Tim Pengelola Bank Sampah Wani Luru RW 1", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Waniluru, {datetime.now().strftime('%d %B %Y')}", ln=True, align='C')

    # 2. Kata Pengantar
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "KATA PENGANTAR", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "", 11)
    intro_text = (
        "Puji syukur kami panjatkan ke hadirat Tuhan Yang Maha Esa atas rahmat dan karunia-Nya, "
        "sehingga kami dapat menyelesaikan Laporan Kinerja Operasional Bank Sampah Wani Luru RW 1 ini dengan baik. "
        "Laporan ini disusun sebagai bentuk pertanggungjawaban dan transparansi pengelolaan bank sampah kepada "
        "seluruh warga dan pemangku kepentingan.\n\n"
        "Melalui laporan ini, kami menyajikan data dan analisis mengenai aktivitas pengelolaan sampah, "
        "termasuk volume sampah yang tereduksi, nilai ekonomi yang dihasilkan, serta partisipasi warga "
        "selama periode pelaporan. Kami berharap laporan ini dapat menjadi bahan evaluasi untuk meningkatkan "
        "kinerja dan layanan Bank Sampah Wani Luru RW 1 ke depannya.\n\n"
        "Terima kasih kami sampaikan kepada seluruh warga yang telah aktif berpartisipasi, serta semua pihak "
        "yang telah mendukung operasional bank sampah ini."
    )
    pdf.multi_cell(0, 7, intro_text)
    
    pdf.ln(20)
    pdf.cell(0, 7, f"Waniluru, {datetime.now().strftime('%d %B %Y')}", ln=True, align='R')
    pdf.ln(15)
    pdf.cell(0, 7, "Pengelola", ln=True, align='R')

    # 3. Daftar Isi (Simulated)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "DAFTAR ISI", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "", 11)
    toc = [
        ("BAB I PENDAHULUAN", "4"),
        ("BAB II LAPORAN UTAMA & DATA", "5"),
        ("BAB III ANALISIS VISUAL", "6"),
        ("BAB IV PENUTUP", "7"),
        ("LAMPIRAN", "8"),
    ]
    for title, page in toc:
        pdf.cell(170, 8, title, 0, 0)
        pdf.cell(20, 8, page, 0, 1, 'R')
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y()) # Dotted line simulation logic skipped for simplicity

    # 4. Pendahuluan
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BAB I", ln=True, align='C')
    pdf.cell(0, 10, "PENDAHULUAN", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1.1 Latar Belakang", ln=True)
    pdf.set_font("Helvetica", "", 11)
    latar_belakang = (
        "Permasalahan sampah merupakan isu lingkungan yang memerlukan perhatian serius dan penanganan "
        "yang berkelanjutan. Bank Sampah Wani Luru RW 1 hadir sebagai solusi berbasis masyarakat untuk "
        "mengelola sampah secara mandiri, mengubah sampah menjadi sumber daya ekonomi, dan membangun "
        "kesadaran lingkungan di tengah masyarakat."
    )
    pdf.multi_cell(0, 7, latar_belakang)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1.2 Tujuan", ln=True)
    pdf.set_font("Helvetica", "", 11)
    tujuan = (
        "Laporan ini disusun dengan tujuan:\n"
        "1. Memberikan gambaran kinerja operasional Bank Sampah Wani Luru RW 1.\n"
        "2. Melaporkan data kuantitatif volume sampah dan nilai transaksi.\n"
        "3. Mengevaluasi tingkat partisipasi warga dalam program bank sampah.\n"
        "4. Sebagai bahan pertimbangan dalam pengambilan keputusan strategis."
    )
    pdf.multi_cell(0, 7, tujuan)

    # 5. Isi/Laporan Utama
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BAB II", ln=True, align='C')
    pdf.cell(0, 10, "LAPORAN UTAMA & DATA", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2.1 Ringkasan Kinerja", ln=True)
    pdf.ln(2)
    
    # Metric Grid Layout
    pdf.set_font("Helvetica", "", 11)
    col_width = 95
    line_height = 10
    
    pdf.cell(col_width, line_height, f"Total Transaksi: {total_transactions}", border=1)
    pdf.cell(col_width, line_height, f"Nasabah Aktif: {warga_unique} Orang", border=1, ln=True)
    pdf.cell(col_width, line_height, f"Total Berat Terkumpul: {total_weight:,.2f} Kg", border=1)
    pdf.cell(col_width, line_height, f"Volume Rata-rata/Hari: {total_weight/max(1, (end_date-start_date).days):,.2f} Kg", border=1, ln=True)
    pdf.cell(col_width, line_height, f"Total Omzet Penjualan: Rp {total_revenue:,.0f}", border=1)
    pdf.cell(col_width, line_height, f"Pendapatan Bersih Panitia: Rp {total_fee:,.0f}", border=1, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2.2 Narasi Operasional", ln=True)
    pdf.set_font("Helvetica", "", 11)
    narasi_ops = (
        f"Pada periode pelaporan ini, Bank Sampah Wani Luru RW 1 telah berhasil memfasilitasi {total_transactions} transaksi "
        f"penyetoran sampah. Hal ini menunjukkan antusiasme warga yang positif. Total nilai ekonomi yang berputar "
        f"mencapai Rp {total_revenue:,.0f}, dengan kontribusi pendapatan untuk operasional (fee) sebesar Rp {total_fee:,.0f}. "
        f"Sampah jenis {sorted(category_sales.items(), key=lambda x: x[1], reverse=True)[0][0] if category_sales else 'Umum'} "
        f"menjadi komoditas dengan nilai transaksi tertinggi."
    )
    pdf.multi_cell(0, 7, narasi_ops)

    # 6. Analisis Visual (Charts)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BAB III", ln=True, align='C')
    pdf.cell(0, 10, "ANALISIS VISUAL", ln=True, align='C')
    pdf.ln(5)

    if chart_trend:
        img_path = _buffer_to_tempfile(chart_trend)
        pdf.image(img_path, x=15, w=180)
        os.remove(img_path)
        pdf.ln(5)
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 5, "Gambar 1. Grafik tren transaksi harian menunjukkan fluktuasi aktivitas penyetoran.", ln=True, align='C')
        pdf.ln(10)

    # Grid of charts
    y_start = pdf.get_y()
    
    if chart_best_cat:
        img_path = _buffer_to_tempfile(chart_best_cat)
        pdf.image(img_path, x=10, y=y_start, w=90)
        os.remove(img_path)

    if chart_worst_cat:
        img_path = _buffer_to_tempfile(chart_worst_cat)
        pdf.image(img_path, x=110, y=y_start, w=90)
        os.remove(img_path)

    pdf.set_y(y_start + 70) 
    
    pdf.ln(5)
    pdf.cell(0, 5, "Gambar 2. Perbandingan kategori sampah berdasarkan nilai ekonomi (Tertinggi vs Terendah).", ln=True, align='C')
    
    pdf.add_page()
    if chart_active_warga:
        img_path = _buffer_to_tempfile(chart_active_warga)
        pdf.image(img_path, x=55, w=100)
        os.remove(img_path)
        pdf.ln(5)
        pdf.cell(0, 5, "Gambar 3. Sepuluh warga dengan frekuensi penyetoran teraktif.", ln=True, align='C')

    # 7. Penutup
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "BAB IV", ln=True, align='C')
    pdf.cell(0, 10, "PENUTUP", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "4.1 Kesimpulan", ln=True)
    pdf.set_font("Helvetica", "", 11)
    
    top_cat_name = sorted(category_sales.items(), key=lambda x: x[1], reverse=True)[0][0] if category_sales else "-"
    kesimpulan = (
        "Berdasarkan data yang telah dipaparkan, dapat disimpulkan bahwa:\n"
        f"1. Kinerja bank sampah berjalan baik dengan partisipasi {warga_unique} nasabah aktif.\n"
        f"2. Jenis sampah '{top_cat_name}' memiliki nilai ekonomi paling signifikan.\n"
        "3. Sistem administrasi dan pencatatan transaksi telah berjalan transparan."
    )
    pdf.multi_cell(0, 7, kesimpulan)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "4.2 Saran", ln=True)
    pdf.set_font("Helvetica", "", 11)
    saran = (
        "1. Perlu dilakukan sosialisasi kembali untuk kategori sampah yang masih rendah penyetorannya.\n"
        "2. Meningkatkan apresiasi kepada warga yang aktif untuk memotivasi warga lainnya.\n"
        "3. Mempertahankan konsistensi jadwal pelayanan dan akurasi penimbangan."
    )
    pdf.multi_cell(0, 7, saran)

    # 8. Lampiran (Table)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "LAMPIRAN", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Rincian Data Penjualan per Kategori", ln=True)
    pdf.ln(2)

    # Table Header
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(10, 8, "No", border=1, align='C', fill=True)
    pdf.cell(80, 8, "Nama Kategori", border=1, fill=True)
    pdf.cell(40, 8, "Total Berat", border=1, align='R', fill=True)
    pdf.cell(60, 8, "Total Penjualan", border=1, align='R', fill=True, ln=True)

    # Table Content
    pdf.set_font("Helvetica", "", 10)
    sorted_cats = sorted(category_sales.items(), key=lambda x: x[1], reverse=True)
    
    for idx, (cat_name, rev) in enumerate(sorted_cats, 1):
        weight = category_weights.get(cat_name, 0)
        pdf.cell(10, 7, str(idx), border=1, align='C')
        pdf.cell(80, 7, cat_name[:35], border=1)
        pdf.cell(40, 7, f"{weight:,.2f} Kg", border=1, align='R')
        pdf.cell(60, 7, f"Rp {rev:,.0f}", border=1, align='R', ln=True)

    pdf_buffer = io.BytesIO(_pdf_output_bytes(pdf))
    pdf_buffer.seek(0)
    return pdf_buffer


def _render_transaction_input_form():
    """Helper to render the transaction input form."""
    st.subheader("➕ Input Transaksi Penjualan Sampah")

    st.markdown("""
    <div class="help-text">
        <strong>📝 Cara Input Transaksi:</strong><br>
        1. Pilih user penjual (Warga/Admin/Panitia/Inputer)<br>
        2. Pilih kategori sampah (harga otomatis muncul)<br>
        3. Timbang dan masukkan berat dalam Kg<br>
        4. Sistem akan otomatis hitung: Total, Fee Admin (10%), dan Saldo Warga
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        if 'item_count' not in st.session_state:
            st.session_state['item_count'] = 1

        st.markdown("#### Jumlah Jenis Sampah")
        count_cols = st.columns([1, 2, 1])
        with count_cols[0]:
            if st.button("➖", key="item_minus", use_container_width=True, disabled=st.session_state['item_count'] <= 1):
                st.session_state['item_count'] = max(1, st.session_state['item_count'] - 1)
                st.rerun()
        with count_cols[1]:
            st.markdown(
                f"<div style='text-align:center; font-size:1.3rem; font-weight:700;'>{st.session_state['item_count']}</div>",
                unsafe_allow_html=True,
            )
        with count_cols[2]:
            if st.button("➕", key="item_plus", use_container_width=True, disabled=st.session_state['item_count'] >= 10):
                st.session_state['item_count'] = min(10, st.session_state['item_count'] + 1)
                st.rerun()

        item_count = st.session_state['item_count']

        pdf_placeholder = st.empty()

        with st.form("transaction_form"):
            st.markdown("### 📝 Form Input Transaksi")

            warga_list = _get_transaction_participant_users()
            warga_options = {f"👤 {w['full_name']} ({w['username']}) - {_display_role_label(w['role'])}": w['id'] for w in warga_list}

            if not warga_options:
                st.warning("⚠️ Belum ada user aktif yang bisa dijadikan penjual transaksi.")
                return

            selected_warga = st.selectbox(
                "👤 Pilih Penjual",
                list(warga_options.keys()),
                help="Pilih user yang menyetor/menjual sampah (Warga/Admin/Panitia/Inputer).",
            )

            categories = get_all_categories()
            category_options = {f"♻️ {c['name']} - Rp {c['price_per_kg']:,.0f}/Kg": c for c in categories}

            batch_id = f"batch-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"
            items = []
            total_preview = 0
            total_fee_preview = 0
            for idx in range(int(item_count)):
                st.markdown(f"**Item {idx+1}**")
                col_i1, col_i2 = st.columns([3, 1])

                with col_i1:
                    cat_label = st.selectbox(
                        "Pilih Kategori",
                        list(category_options.keys()),
                        key=f"cat_{idx}",
                        help="Pilih kategori sampah",
                    )
                    cat_data = category_options[cat_label]

                with col_i2:
                    weight = st.number_input(
                        "Berat (Kg)", min_value=0.0, step=0.1, format="%.2f",
                        key=f"weight_{idx}",
                        help="Masukkan berat untuk kategori ini"
                    )

                if weight > 0:
                    item_total = weight * cat_data['price_per_kg']
                    fee = item_total * 0.10
                    total_preview += item_total
                    total_fee_preview += fee
                items.append({
                    'category_id': cat_data['id'],
                    'category_name': cat_data['name'],
                    'weight': weight,
                    'price': cat_data['price_per_kg'],
                })

            total_net_preview = total_preview - total_fee_preview
            if total_preview > 0:
                st.markdown(f"""
                <div style="background: #E3F2FD; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                    <p style="margin: 0; color: #0D47A1; font-weight: 600;">💡 Preview Multi-Item:</p>
                    <p style="margin: 0.3rem 0; color: #1E88E5;">Total Kotor: <strong>Rp {total_preview:,.0f}</strong></p>
                    <p style="margin: 0.3rem 0; color: #1E88E5;">Fee Admin (10%): <strong>Rp {total_fee_preview:,.0f}</strong></p>
                    <p style="margin: 0.3rem 0; color: #0D47A1; font-size: 1.1rem;">Warga Terima: <strong>Rp {total_net_preview:,.0f}</strong></p>
                </div>
                """, unsafe_allow_html=True)

            notes = st.text_area("📌 Catatan (Opsional)", 
                                help="Tambahkan catatan jika diperlukan, misal: kondisi sampah, dll")

            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 Proses Transaksi Sekarang", use_container_width=True, type="primary")

            if submitted:
                invalid = [item for item in items if item['weight'] <= 0]
                if invalid:
                    st.warning("⚠️ Semua berat harus lebih dari 0!")
                else:
                    warga_id = warga_options[selected_warga]
                    processed_by = st.session_state['user']['id']
                    summary_rows = []
                    total_amount = 0
                    total_fee = 0
                    total_net = 0
                    with st.spinner("⏳ Memproses transaksi multi-item..."):
                        for item in items:
                            success, transaction_id, details = create_transaction(
                                warga_id, item['category_id'], item['weight'], processed_by, notes, batch_id=batch_id
                            )
                            if success:
                                summary_rows.append({
                                    'id': transaction_id,
                                    'kategori': item['category_name'],
                                    'berat': item['weight'],
                                    'harga': item['price'],
                                    'total': details['total_amount'],
                                    'fee': details['committee_fee'],
                                    'net': details['net_amount'],
                                })
                                total_amount += details['total_amount']
                                total_fee += details['committee_fee']
                                total_net += details['net_amount']

                    log_audit(processed_by, 'CREATE_TRANSACTION',
                              f"Multi-item transaction ({len(items)} items) for warga {warga_id}")

                    st.success("✅ Transaksi multi-item berhasil diproses!")
                    st.balloons()

                    st.markdown(
                        "<div class=\"info-card\" style=\"background: #E8F5E9; border-color: #4CAF50;\">",
                        unsafe_allow_html=True,
                    )
                    st.markdown("<h3 style='color: #2E7D32; margin-top: 0;'>💰 Ringkasan Transaksi</h3>", unsafe_allow_html=True)
                    item_df = pd.DataFrame(
                        [
                            (
                                row['id'], row['kategori'], f"{row['berat']:.2f} Kg",
                                f"Rp {row['harga']:,.0f}", f"Rp {row['total']:,.0f}",
                                f"Rp {row['fee']:,.0f}", f"Rp {row['net']:,.0f}",
                            )
                            for row in summary_rows
                        ],
                        columns=['ID', 'Kategori', 'Berat', 'Harga/Kg', 'Total', 'Fee', 'Diterima'],
                    )
                    st.dataframe(item_df, use_container_width=True, hide_index=True)

                    st.markdown(f"""
                    <table style="width: 100%; color: #1B5E20;">
                        <tr><td><strong>Total Kotor:</strong></td><td style="text-align: right;"><strong>Rp {total_amount:,.0f}</strong></td></tr>
                        <tr><td>Fee Admin (10%):</td><td style="text-align: right;">Rp {total_fee:,.0f}</td></tr>
                        <tr style="border-top: 2px solid #4CAF50;"><td><strong>Diterima Warga:</strong></td><td style="text-align: right; font-size: 1.2rem;"><strong>Rp {total_net:,.0f}</strong></td></tr>
                    </table>
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    warga_detail = get_user_by_id(warga_id)
                    warga_name = warga_detail['full_name'] if warga_detail else "-"
                    processor = st.session_state['user']['full_name']
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    class ReceiptPDF(FPDF):
                        def header(self):
                            self.set_fill_color(76, 175, 80)
                            self.rect(10, 8, 190, 18, 'F')
                            self.set_text_color(255, 255, 255)
                            self.set_font('Helvetica', 'B', 14)
                            self.cell(0, 10, 'Nota Transaksi Bank Sampah', ln=True, align='C')
                            self.set_font('Helvetica', '', 10)
                            self.cell(0, 6, 'Bank Sampah Wani Luru RW 1', ln=True, align='C')
                            self.ln(5)
                            self.set_text_color(0, 0, 0)

                    pdf = ReceiptPDF()
                    pdf.add_page()
                    pdf.set_auto_page_break(auto=True, margin=15)

                    pdf.set_font('Helvetica', '', 11)
                    pdf.cell(0, 8, f"Warga: {warga_name}", ln=True)
                    pdf.cell(0, 8, f"Diproses oleh: {processor}", ln=True)
                    pdf.cell(0, 8, f"Tanggal: {timestamp}", ln=True)
                    if notes:
                        pdf.multi_cell(0, 8, f"Catatan: {notes}")
                    pdf.ln(4)

                    w_id, w_cat, w_weight, w_price, w_total, w_fee, w_net = 12, 55, 22, 28, 28, 22, 23
                    pdf.set_fill_color(76, 175, 80)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(w_id, 8, 'ID', border=1, align='C', fill=True)
                    pdf.cell(w_cat, 8, 'Kategori', border=1, fill=True)
                    pdf.cell(w_weight, 8, 'Berat', border=1, align='R', fill=True)
                    pdf.cell(w_price, 8, 'Harga/Kg', border=1, align='R', fill=True)
                    pdf.cell(w_total, 8, 'Total', border=1, align='R', fill=True)
                    pdf.cell(w_fee, 8, 'Fee', border=1, align='R', fill=True)
                    pdf.cell(w_net, 8, 'Diterima', border=1, ln=True, align='R', fill=True)

                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font('Helvetica', '', 10)
                    for row in summary_rows:
                        pdf.cell(w_id, 8, str(row['id']), border=1, align='C')
                        pdf.cell(w_cat, 8, row['kategori'][:24], border=1)
                        pdf.cell(w_weight, 8, f"{row['berat']:.2f} Kg", border=1, align='R')
                        pdf.cell(w_price, 8, f"Rp {row['harga']:,.0f}", border=1, align='R')
                        pdf.cell(w_total, 8, f"Rp {row['total']:,.0f}", border=1, align='R')
                        pdf.cell(w_fee, 8, f"Rp {row['fee']:,.0f}", border=1, align='R')
                        pdf.cell(w_net, 8, f"Rp {row['net']:,.0f}", border=1, ln=True, align='R')

                    pdf.set_fill_color(232, 245, 233)
                    pdf.set_font('Helvetica', 'B', 10)
                    pdf.cell(w_id + w_cat + w_weight + w_price, 8, 'Total Kotor', border=1, fill=True)
                    pdf.cell(w_total + w_fee + w_net, 8, f"Rp {total_amount:,.0f}", border=1, ln=True, align='R', fill=True)
                    pdf.cell(w_id + w_cat + w_weight + w_price, 8, 'Fee Admin (10%)', border=1, fill=True)
                    pdf.cell(w_total + w_fee + w_net, 8, f"Rp {total_fee:,.0f}", border=1, ln=True, align='R', fill=True)
                    pdf.cell(w_id + w_cat + w_weight + w_price, 8, 'Diterima Warga', border=1, fill=True)
                    pdf.cell(w_total + w_fee + w_net, 8, f"Rp {total_net:,.0f}", border=1, ln=True, align='R', fill=True)

                    pdf.ln(6)
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(76, 175, 80)
                    pdf.cell(0, 8, 'Go Green', ln=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font('Helvetica', '', 9)
                    pdf.multi_cell(0, 6, "Kurangi penggunaan kertas, simpan nota ini secara digital.")

                    pdf_data = _pdf_output_bytes(pdf)
                    st.session_state['last_pdf_data'] = pdf_data
                    st.session_state['last_pdf_name'] = f"nota_{summary_rows[0]['id']}.pdf"

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

    if st.session_state.get('last_pdf_data'):
        pdf_placeholder.download_button(
            label="⬇️ Download Nota (PDF)",
            data=st.session_state['last_pdf_data'],
            file_name=st.session_state.get('last_pdf_name', 'nota.pdf'),
            mime="application/pdf",
            type="primary",
            help="Unduh nota transaksi dalam bentuk PDF",
        )

def _render_input_schedule_settings():
    """Shared helper to render the input schedule settings UI."""
    st.subheader("⚙️ Pengaturan Jadwal Input")
    st.info("Atur kapan role 'Panitia (Inputer)' diperbolehkan menginput transaksi.")
    
    import json
    
    # Current settings
    current_mode = get_setting('input_availability_mode', 'manual')
    
    mode = st.radio("Mode Ketersediaan", ["Manual", "Terjadwal (Otomatis)"], 
                   index=0 if current_mode == 'manual' else 1,
                   horizontal=True,
                   key="input_mode_radio")
                   
    if mode == "Manual":
        st.markdown("#### Mode Manual")
        current_status = get_setting('input_manual_status', '1')
        is_on = st.toggle("Aktifkan Input Transaksi", value=(current_status == '1'))
        
        if st.button("Simpan Pengaturan Manual"):
            set_setting('input_availability_mode', 'manual')
            set_setting('input_manual_status', '1' if is_on else '0')
            log_audit(st.session_state['user']['id'], 'UPDATE_SETTINGS', f"Set input mode to Manual: {'ON' if is_on else 'OFF'}")
            st.success("✅ Pengaturan berhasil disimpan")
            
    else: # Scheduled
        st.markdown("#### Mode Terjadwal")
        
        # Load existing config
        config_json = get_setting('input_schedule_config', '{}')
        try:
            config = json.loads(config_json)
        except:
            config = {}
            
        with st.form("schedule_form"):
            st.markdown("**1. Hari dalam Seminggu**")
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            days_indo = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            
            selected_days = config.get('weekly', [])
            
            # Create checkboxes for days
            cols = st.columns(4)
            new_selected_days = []
            for i, day in enumerate(days):
                with cols[i % 4]:
                    if st.checkbox(days_indo[i], value=(day in selected_days)):
                        new_selected_days.append(day)
                        
            st.markdown("---")
            st.markdown("**2. Jam Operasional**")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                default_start = datetime.strptime(config.get('time_start', '08:00'), '%H:%M').time()
                t_start = st.time_input("Jam Mulai", value=default_start)
            with col_t2:
                default_end = datetime.strptime(config.get('time_end', '16:00'), '%H:%M').time()
                t_end = st.time_input("Jam Selesai", value=default_end)
                
            st.markdown("---")
            st.markdown("**3. Tanggal Khusus (Opsional)**")
            st.caption("Jika dipilih, input hanya aktif pada tanggal-tanggal ini setiap bulannya.")
            
            selected_dates = config.get('monthly', [])
            selected_dates_str = [str(d) for d in selected_dates]
            
            monthly_dates = st.multiselect("Pilih Tanggal", [str(i) for i in range(1, 32)], default=selected_dates_str)
            
            submitted = st.form_submit_button("Simpan Jadwal")
            
            if submitted:
                new_config = {
                    'weekly': new_selected_days,
                    'time_start': t_start.strftime('%H:%M'),
                    'time_end': t_end.strftime('%H:%M'),
                    'monthly': [int(d) for d in monthly_dates] if monthly_dates else []
                }
                
                set_setting('input_availability_mode', 'scheduled')
                set_setting('input_schedule_config', json.dumps(new_config))
                log_audit(st.session_state['user']['id'], 'UPDATE_SETTINGS', "Updated input schedule configuration")
                st.success("✅ Jadwal berhasil disimpan")

def _render_admin_tab_transaksi(tab_transaksi):
    """Shared transaksi tab for admin-like roles (admin, panitia)."""
    with tab_transaksi:
        trans_tab_input, trans_tab_history = st.tabs(["➕ Input Transaksi", "📜 History Transaksi"])

        with trans_tab_input:
            # CHECK INPUT AVAILABILITY FOR INPUTER ROLE
            is_inputer = st.session_state['user']['role'] == 'inputer'
            if is_inputer and not is_input_period_active():
                 st.markdown("""
                <div class="empty-state" style="border-color: #F44336; background: #FFEBEE;">
                    <div style="font-size: 3rem;">⛔</div>
                    <h3 style="color: #D32F2F;">Akses Input Ditutup</h3>
                    <p style="color: #B71C1C;">Saat ini bukan jadwal operasional untuk input transaksi.</p>
                    <p style="font-size: 0.9rem; margin-top: 0.5rem;">Silakan hubungi Admin atau coba lagi nanti.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                _render_transaction_input_form()

        with trans_tab_history:
            st.subheader("📜 History Transaksi & Nota")
            st.markdown("Unduh nota PDF untuk transaksi yang sudah tercatat.")

            filter_col1, filter_col2 = st.columns([2, 2])

            with filter_col1:
                warga_filter_map = {"Semua Penjual": None}
                for w in _get_transaction_participant_users():
                    warga_filter_map[f"👤 {w['full_name']} ({w['username']}) - {_display_role_label(w['role'])}"] = w['id']
                selected_warga_label = st.selectbox("Filter Penjual", list(warga_filter_map.keys()))
                selected_warga_id = warga_filter_map[selected_warga_label]

            with filter_col2:
                start_default = datetime.now() - timedelta(days=30)
                end_default = datetime.now()
                date_range = st.date_input("Rentang Tanggal", value=(start_default, end_default))
                start_date = end_date = None
                if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                    start_date, end_date = date_range

            transactions = get_transactions(
                warga_id=selected_warga_id,
                limit=200,
                start_date=start_date.isoformat() if start_date else None,
                end_date=end_date.isoformat() if end_date else None,
            )

            if transactions:
                grouped = {}
                for t in transactions:
                    key = t['batch_id'] if t['batch_id'] else f"single-{t['id']}"
                    if key not in grouped:
                        grouped[key] = {
                            'batch_id': key,
                            'warga_name': t['warga_name'],
                            'processed_by_name': t['processed_by_name'],
                            'notes': t['notes'],
                            'transaction_date': t['transaction_date'],
                            'items': [],
                        }
                    grouped[key]['items'].append(t)

                for batch_key, data in grouped.items():
                    total_amount = sum(it['total_amount'] for it in data['items'])
                    total_fee = sum(it['committee_fee'] for it in data['items'])
                    total_net = sum(it['net_amount'] for it in data['items'])
                    total_weight = sum(it['weight_kg'] for it in data['items'])
                    with st.expander(f"#{batch_key} | {data['warga_name']} | {len(data['items'])} item | {total_weight:.2f} Kg | Rp {total_net:,.0f}"):
                        st.write(f"Tanggal: {data['transaction_date']}")
                        st.write(f"Diproses oleh: {data['processed_by_name']}")
                        st.write(f"Catatan: {data['notes'] or '-'}")

                        class SingleReceiptPDF(FPDF):
                            def header(self):
                                self.set_fill_color(76, 175, 80)
                                self.rect(10, 8, 190, 18, 'F')
                                self.set_text_color(255, 255, 255)
                                self.set_font('Helvetica', 'B', 14)
                                self.cell(0, 10, 'Nota Transaksi Bank Sampah', ln=True, align='C')
                                self.set_font('Helvetica', '', 10)
                                self.cell(0, 6, 'Bank Sampah Wani Luru RW 1', ln=True, align='C')
                                self.ln(5)
                                self.set_text_color(0, 0, 0)

                        pdf = SingleReceiptPDF()
                        pdf.add_page()
                        pdf.set_auto_page_break(auto=True, margin=15)

                        pdf.set_font('Helvetica', '', 11)
                        pdf.cell(0, 8, f"Batch/Transaksi: {batch_key}", ln=True)
                        pdf.cell(0, 8, f"Warga: {data['warga_name']}", ln=True)
                        pdf.cell(0, 8, f"Diproses oleh: {data['processed_by_name']}", ln=True)
                        pdf.cell(0, 8, f"Tanggal: {data['transaction_date']}", ln=True)
                        if data['notes']:
                            pdf.multi_cell(0, 8, f"Catatan: {data['notes']}")
                        pdf.ln(4)

                        w_id, w_cat, w_weight, w_price, w_total, w_fee, w_net = 12, 55, 22, 28, 28, 22, 23
                        pdf.set_fill_color(76, 175, 80)
                        pdf.set_text_color(255, 255, 255)
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.cell(w_id, 8, 'ID', border=1, align='C', fill=True)
                        pdf.cell(w_cat, 8, 'Kategori', border=1, fill=True)
                        pdf.cell(w_weight, 8, 'Berat', border=1, align='R', fill=True)
                        pdf.cell(w_price, 8, 'Harga/Kg', border=1, align='R', fill=True)
                        pdf.cell(w_total, 8, 'Total', border=1, align='R', fill=True)
                        pdf.cell(w_fee, 8, 'Fee', border=1, align='R', fill=True)
                        pdf.cell(w_net, 8, 'Diterima', border=1, ln=True, align='R', fill=True)

                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font('Helvetica', '', 10)
                        for it in data['items']:
                            pdf.cell(w_id, 8, str(it['id']), border=1, align='C')
                            pdf.cell(w_cat, 8, it['category_name'][:24], border=1)
                            pdf.cell(w_weight, 8, f"{it['weight_kg']:.2f} Kg", border=1, align='R')
                            pdf.cell(w_price, 8, f"Rp {it['price_per_kg']:,.0f}", border=1, align='R')
                            pdf.cell(w_total, 8, f"Rp {it['total_amount']:,.0f}", border=1, align='R')
                            pdf.cell(w_fee, 8, f"Rp {it['committee_fee']:,.0f}", border=1, align='R')
                            pdf.cell(w_net, 8, f"Rp {it['net_amount']:,.0f}", border=1, ln=True, align='R')

                        pdf.set_fill_color(232, 245, 233)
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.cell(w_id + w_cat + w_weight + w_price, 8, 'Total Kotor', border=1, fill=True)
                        pdf.cell(w_total + w_fee + w_net, 8, f"Rp {total_amount:,.0f}", border=1, ln=True, align='R', fill=True)
                        pdf.cell(w_id + w_cat + w_weight + w_price, 8, 'Fee Admin (10%)', border=1, fill=True)
                        pdf.cell(w_total + w_fee + w_net, 8, f"Rp {total_fee:,.0f}", border=1, ln=True, align='R', fill=True)
                        pdf.cell(w_id + w_cat + w_weight + w_price, 8, 'Diterima Warga', border=1, fill=True)
                        pdf.cell(w_total + w_fee + w_net, 8, f"Rp {total_net:,.0f}", border=1, ln=True, align='R', fill=True)

                        pdf.ln(6)
                        pdf.set_font('Helvetica', 'B', 11)
                        pdf.set_text_color(76, 175, 80)
                        pdf.cell(0, 8, 'Go Green', ln=True)
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font('Helvetica', '', 9)
                        pdf.multi_cell(0, 6, "Kurangi penggunaan kertas, simpan nota ini secara digital.")

                        pdf_data_hist = _pdf_output_bytes(pdf)

                        st.download_button(
                            label="⬇️ Download Nota (PDF)",
                            data=pdf_data_hist,
                            file_name=f"nota_{batch_key}.pdf",
                            mime="application/pdf",
                            type="primary",
                            help="Unduh nota transaksi ini",
                        )
            else:
                st.info("Belum ada data transaksi untuk ditampilkan.")


def _render_admin_tab_categories(tab_cat):
    """Shared kategori tab for admin-like roles (admin, panitia)."""
    with tab_cat:
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("### Daftar Kategori")
            categories = get_all_categories()

            if categories:
                df_categories = pd.DataFrame(
                    [
                        (c['id'], c['name'], f"Rp {c['price_per_kg']:,.0f}", c['updated_at'])
                        for c in categories
                    ],
                    columns=['ID', 'Nama Kategori', 'Harga/Kg', 'Update Terakhir'],
                )
                st.dataframe(df_categories, use_container_width=True, hide_index=True)

                st.markdown("### Update Harga")
                col_a, col_b, col_c = st.columns([2, 1, 1])

                with col_a:
                    category_options = {c['name']: c['id'] for c in categories}
                    selected_category = st.selectbox("Pilih Kategori", list(category_options.keys()))

                with col_b:
                    new_price = st.number_input(
                        "💰 Harga Baru (Rp/Kg)", min_value=0, step=100, help="Masukkan harga baru per kilogram"
                    )

                with col_c:
                    st.write("")
                    st.write("")
                    if st.button("💾 Update Harga", use_container_width=True, type="primary"):
                        if new_price > 0:
                            category_id = category_options[selected_category]
                            update_category_price(category_id, new_price)
                            log_audit(
                                st.session_state['user']['id'],
                                'UPDATE_PRICE',
                                f"Updated price for {selected_category} to Rp {new_price}",
                            )
                            st.success(
                                f"✅ Harga {selected_category} berhasil diupdate menjadi Rp {new_price:,.0f}/Kg!"
                            )
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("⚠️ Harga harus lebih dari 0!")

                st.markdown("### Hapus Kategori")
                del_col1, del_col2 = st.columns([2, 1])

                with del_col1:
                    delete_map = {f"{c['name']} (Rp {c['price_per_kg']:,.0f}/Kg)": c['id'] for c in categories}
                    selected_delete = st.selectbox("Pilih Kategori", list(delete_map.keys()))

                with del_col2:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Hapus Kategori", use_container_width=True):
                        del_id = delete_map[selected_delete]
                        success, message = delete_category(del_id)
                        if success:
                            log_audit(
                                st.session_state['user']['id'], 'DELETE_CATEGORY', f"Deleted category ID {del_id}"
                            )
                            st.success("✅ Kategori berhasil dihapus")
                            st.rerun()
                        else:
                            st.error(f"❌ Gagal hapus: {message}")
            else:
                st.info("📝 Belum ada kategori sampah. Silakan tambah kategori baru terlebih dahulu.")

        with col2:
            st.markdown("### Tambah Kategori Baru")

            with st.form("add_category_form_panitia"):
                new_category_name = st.text_input("Nama Kategori")
                new_category_price = st.number_input("Harga/Kg (Rp)", min_value=0, step=100)

                submitted = st.form_submit_button("Tambah Kategori", use_container_width=True)

                if submitted:
                    if new_category_name and new_category_price > 0:
                        success, message = create_category(new_category_name, new_category_price)
                        if success:
                            log_audit(
                                st.session_state['user']['id'], 'CREATE_CATEGORY', f"Created category {new_category_name}"
                            )
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(f"Gagal menambah kategori: {message}")
                    else:
                        st.warning("Silakan isi semua field!")

            st.markdown("---")
            _render_category_excel_uploader('admin_panitia')

        st.markdown("---")
        st.subheader("🕑 Riwayat Harga Berdasarkan Transaksi")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT DISTINCT c.name, t.price_per_kg, DATE(t.transaction_date) as date
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            ORDER BY t.transaction_date DESC
            LIMIT 50
        '''
        )
        price_history = cursor.fetchall()
        conn.close()

        if price_history:
            df_history = pd.DataFrame(
                [(h['name'], f"Rp {h['price_per_kg']:,.0f}", h['date']) for h in price_history],
                columns=['Kategori', 'Harga/Kg', 'Tanggal'],
            )
            st.dataframe(df_history, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat transaksi untuk menampilkan harga.")


def dashboard_panitia():
    """Dashboard for Admin (legacy panitia role)."""
    
    tab_dashboard, tab_transaksi, tab_cat, tab_keu, tab_users, tab_audit, tab_laporan, tab_jadwal = st.tabs([
        "🏠 Dashboard", "🔀 Transaksi", "♻️ Kategori & Harga", "💰 Keuangan", "👥 Manage User", "📜 Audit Log", "📑 Laporan", "⚙️ Pengaturan Jadwal"
    ])
    
    with tab_dashboard:
        dashboard_admin_home()
    
    _render_admin_tab_transaksi(tab_transaksi)
    _render_admin_tab_categories(tab_cat)
    
    with tab_keu:
        keu_tab_manage, keu_tab_income = st.tabs(["Kelola Keuangan", "Pendapatan Admin"])

        with keu_tab_manage:
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

        with keu_tab_income:
            st.subheader("Pendapatan Admin")
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Filter Periode")
                start_date_comm = st.date_input("Dari", value=datetime.now() - timedelta(days=30), key="comm_start")
                end_date_comm = st.date_input("Sampai", value=datetime.now(), key="comm_end")
                
                total_earnings = get_committee_total_earnings(start_date_comm, end_date_comm)
                
                ui_metric_card("Total Pendapatan Admin", f"Rp {total_earnings:,.0f}", icon="🏦")
            
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
    
    with tab_users:
        user_tab_manage, user_tab_settings = st.tabs(["👥 Kelola Warga", "⚙️ Pengaturan Akun Admin"])

        with user_tab_manage:
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
                        role_options = ["warga", "panitia", "inputer"]
                        new_role = st.selectbox(
                            "👔 Role",
                            role_options,
                            format_func=lambda r: "Admin" if r == "panitia" else "Panitia" if r == "inputer" else r.capitalize(),
                            help="Pilih role untuk user baru",
                        )
                    
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
                    [
                        (
                            w['id'],
                            w['username'],
                            w['full_name'],
                            w.get('nickname') or '-',
                            f"RT {w.get('rt') or '-'} / RW {w.get('rw') or '-'}",
                            w.get('whatsapp') or '-',
                            f"Rp {w['balance']:,.0f}",
                            'Aktif' if w['active'] else 'Non-Aktif',
                        )
                        for w in all_warga
                    ],
                    columns=['ID', 'Username', 'Nama Lengkap', 'Panggilan', 'RT/RW', 'WhatsApp', 'Saldo', 'Status'],
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

        with user_tab_settings:
            st.subheader("⚙️ Pengaturan Akun Admin")
            user_id = st.session_state['user']['id']
            user_info = get_user_by_id(user_id)

            col_profile, col_password = st.columns(2)

            with col_profile:
                st.markdown("### 🪪 Ubah Profil")
                with st.form("panitia_update_profile_form"):
                    full_name = st.text_input("Nama Lengkap", value=user_info['full_name'] or "")
                    nickname = st.text_input("Nama Panggilan", value=user_info['nickname'] or "")
                    address = st.text_area("Alamat", value=user_info['address'] or "", height=80)
                    rt = st.text_input("RT", value=user_info['rt'] or "")
                    rw = st.text_input("RW", value=user_info['rw'] or "")
                    whatsapp = st.text_input("No. WhatsApp", value=user_info['whatsapp'] or "")

                    submitted_profile = st.form_submit_button("Simpan Profil", use_container_width=True)

                    if submitted_profile:
                        if not full_name.strip():
                            st.error("❌ Nama lengkap tidak boleh kosong")
                        else:
                            success, msg = update_user(
                                user_id,
                                full_name.strip(),
                                nickname.strip(),
                                address.strip(),
                                rt.strip(),
                                rw.strip(),
                                whatsapp.strip(),
                            )
                            if success:
                                st.session_state['user']['full_name'] = full_name.strip()
                                log_audit(user_id, 'UPDATE_PROFILE', 'Admin memperbarui profil sendiri')
                                st.success("✅ Profil berhasil diperbarui")
                            else:
                                st.error(f"❌ Gagal memperbarui profil: {msg}")

            with col_password:
                st.markdown("### 🔒 Ubah Password")
                with st.form("panitia_change_password_form"):
                    current_password = st.text_input("Password Saat Ini", type="password")
                    new_password = st.text_input("Password Baru", type="password", help="Minimal 6 karakter")
                    confirm_password = st.text_input("Konfirmasi Password Baru", type="password")

                    submitted_password = st.form_submit_button("Simpan Password", use_container_width=True)

                    if submitted_password:
                        if not current_password or not new_password or not confirm_password:
                            st.warning("⚠️ Semua field password wajib diisi")
                        elif len(new_password) < 6:
                            st.error("❌ Password baru minimal 6 karakter")
                        elif new_password != confirm_password:
                            st.error("❌ Konfirmasi password tidak sesuai")
                        elif current_password == new_password:
                            st.warning("⚠️ Password baru tidak boleh sama dengan password lama")
                        else:
                            auth_check = authenticate_user(st.session_state['user']['username'], current_password)
                            if not auth_check:
                                st.error("❌ Password saat ini salah")
                            else:
                                update_user_password(user_id, new_password)
                                log_audit(user_id, 'CHANGE_PASSWORD', 'Admin mengganti password sendiri')
                                st.success("✅ Password berhasil diubah")
    
    with tab_audit:
        _render_audit_log_tab('admin_panitia', default_limit=300)

    with tab_laporan:
        st.markdown("### 📄 Generate Laporan PDF")
        pdf_col1, pdf_col2, pdf_col3 = st.columns([1, 1, 1])

        with pdf_col1:
            report_start_date = st.date_input("Dari Tanggal", value=datetime.now() - timedelta(days=30), key="report_start_pdf")

        with pdf_col2:
            report_end_date = st.date_input("Sampai Tanggal", value=datetime.now(), key="report_end_pdf")

        with pdf_col3:
            warga_filter_options = {"Semua Warga": None}
            warga_filter_options.update({w['full_name']: w['id'] for w in get_all_users('warga')})
            selected_warga_pdf = st.selectbox("Filter Warga (opsional)", list(warga_filter_options.keys()), key="report_warga_pdf")

        generate_col = st.columns([1, 2])[1]
        with generate_col:
            if st.button("Generate PDF Laporan", use_container_width=True):
                if report_end_date < report_start_date:
                    st.error("Tanggal akhir tidak boleh lebih awal dari tanggal mulai")
                else:
                    warga_filter = warga_filter_options[selected_warga_pdf]
                    pdf_transactions = get_transactions(warga_id=warga_filter, start_date=report_start_date, end_date=report_end_date)

                    if pdf_transactions:
                        pdf_buffer = generate_pdf_laporan(pdf_transactions, report_start_date, report_end_date)
                        st.download_button(
                            "Download Laporan PDF",
                            data=pdf_buffer,
                            file_name="laporan_bank_sampah.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    else:
                        st.info("Tidak ada transaksi pada rentang dan filter yang dipilih")

        st.markdown("---")

        laporan_tab_keu, laporan_tab_perf = st.tabs(["Laporan Keuangan", "Performa Warga"])

        with laporan_tab_keu:
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
                            ui_metric_card("Total Transaksi", stats['total_transactions'], icon="🧾")
                        
                        with metric_col2:
                            ui_metric_card("Total Berat", f"{stats['total_weight']:.2f} Kg", icon="⚖️")
                        
                        with metric_col3:
                            ui_metric_card("Total Revenue", f"Rp {stats['total_revenue']:,.0f}", icon="💰")
                        
                        with metric_col4:
                            ui_metric_card("Pendapatan Admin", f"Rp {committee_earnings:,.0f}", icon="🏦")
                
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
                            ui_metric_card("Total Transaksi", stats['total_transactions'], icon="🧾")
                        
                        with metric_col2:
                            ui_metric_card("Total Berat", f"{stats['total_weight']:.2f} Kg", icon="⚖️")
                        
                        with metric_col3:
                            ui_metric_card("Total Revenue", f"Rp {stats['total_revenue']:,.0f}", icon="💰")
                        
                        with metric_col4:
                            ui_metric_card("Pendapatan Admin", f"Rp {committee_earnings:,.0f}", icon="🏦")
            
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
                        columns=['Warga', 'Kategori', 'Berat (Kg)', 'Total', 'Fee Admin', 'Diterima Warga', 'Tanggal']
                    )
                    st.dataframe(df_trans, use_container_width=True, hide_index=True)
                    
                    # Summary
                    total_revenue = sum(t['total_amount'] for t in transactions)
                    total_fee = sum(t['committee_fee'] for t in transactions)
                    
                    st.info(f"**Total Revenue:** Rp {total_revenue:,.0f} | **Total Fee Admin:** Rp {total_fee:,.0f}")
                else:
                    st.info("Tidak ada transaksi pada periode ini")

        with laporan_tab_perf:
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
                ui_metric_card("Total Transaksi", performance['total_transactions'], icon="🧾")
            
            with metric_col2:
                ui_metric_card("Total Berat", f"{performance['total_weight']:.2f} Kg", icon="⚖️")
            
            with metric_col3:
                ui_metric_card("Total Pendapatan", f"Rp {performance['total_earned']:,.0f}", icon="💰")
            
            with metric_col4:
                current_balance = get_user_balance(warga_id)
                ui_metric_card("Saldo Saat Ini", f"Rp {current_balance:,.0f}", icon="💳")
            
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

    with tab_jadwal:
        _render_input_schedule_settings()




def dashboard_inputer():
    """Dashboard for Panitia role with limited admin access."""
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #FFB74D 0%, #FB8C00 100%);">
        <h1>📝 Dashboard Panitia</h1>
        <p>Input transaksi dan kelola kategori & harga</p>
    </div>
    """, unsafe_allow_html=True)

    tab_transaksi, tab_cat, tab_settings = st.tabs([
        "🔀 Transaksi", "♻️ Kategori & Harga", "⚙️ Pengaturan Akun"
    ])

    _render_admin_tab_transaksi(tab_transaksi)
    _render_admin_tab_categories(tab_cat)

    with tab_settings:
        st.subheader("⚙️ Pengaturan Akun Panitia")
        user_id = st.session_state['user']['id']
        user_info = get_user_by_id(user_id)

        col_profile, col_password = st.columns(2)

        with col_profile:
            st.markdown("### 🪪 Ubah Profil")
            with st.form("inputer_update_profile_form"):
                full_name = st.text_input("Nama Lengkap", value=user_info['full_name'] or "")
                nickname = st.text_input("Nama Panggilan", value=user_info['nickname'] or "")
                address = st.text_area("Alamat", value=user_info['address'] or "", height=80)
                rt = st.text_input("RT", value=user_info['rt'] or "")
                rw = st.text_input("RW", value=user_info['rw'] or "")
                whatsapp = st.text_input("No. WhatsApp", value=user_info['whatsapp'] or "")

                submitted_profile = st.form_submit_button("Simpan Profil", use_container_width=True)

                if submitted_profile:
                    if not full_name.strip():
                        st.error("❌ Nama lengkap tidak boleh kosong")
                    else:
                        success, msg = update_user(
                            user_id,
                            full_name.strip(),
                            nickname.strip(),
                            address.strip(),
                            rt.strip(),
                            rw.strip(),
                            whatsapp.strip(),
                        )
                        if success:
                            st.session_state['user']['full_name'] = full_name.strip()
                            log_audit(user_id, 'UPDATE_PROFILE', 'Panitia memperbarui profil sendiri')
                            st.success("✅ Profil berhasil diperbarui")
                        else:
                            st.error(f"❌ Gagal memperbarui profil: {msg}")

        with col_password:
            st.markdown("### 🔒 Ubah Password")
            with st.form("inputer_change_password_form"):
                current_password = st.text_input("Password Saat Ini", type="password")
                new_password = st.text_input("Password Baru", type="password", help="Minimal 6 karakter")
                confirm_password = st.text_input("Konfirmasi Password Baru", type="password")

                submitted_password = st.form_submit_button("Simpan Password", use_container_width=True)

                if submitted_password:
                    if not current_password or not new_password or not confirm_password:
                        st.warning("⚠️ Semua field password wajib diisi")
                    elif len(new_password) < 6:
                        st.error("❌ Password baru minimal 6 karakter")
                    elif new_password != confirm_password:
                        st.error("❌ Konfirmasi password tidak sesuai")
                    elif current_password == new_password:
                        st.warning("⚠️ Password baru tidak boleh sama dengan password lama")
                    else:
                        auth_check = authenticate_user(st.session_state['user']['username'], current_password)
                        if not auth_check:
                            st.error("❌ Password saat ini salah")
                        else:
                            update_user_password(user_id, new_password)
                            log_audit(user_id, 'CHANGE_PASSWORD', 'Panitia mengganti password sendiri')
                            st.success("✅ Password berhasil diubah")


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
            <p style="margin: 0; font-size: 0.9rem; color: #1E88E5;">✓ Dapat ditarik kapan saja melalui Admin</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Performa Saya", "📋 Riwayat Transaksi", "💳 Riwayat Keuangan", "⚙️ Pengaturan Akun"])
    
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

    with tab4:
        st.subheader("⚙️ Pengaturan Akun")
        user_info = get_user_by_id(user_id)

        col_profile, col_password = st.columns(2)

        with col_profile:
            st.markdown("### 🪪 Ubah Profil")
            with st.form("update_profile_form"):
                full_name = st.text_input("Nama Lengkap", value=user_info['full_name'] or "")
                nickname = st.text_input("Nama Panggilan", value=user_info['nickname'] or "")
                address = st.text_area("Alamat", value=user_info['address'] or "", height=80)
                rt = st.text_input("RT", value=user_info['rt'] or "")
                rw = st.text_input("RW", value=user_info['rw'] or "")
                whatsapp = st.text_input("No. WhatsApp", value=user_info['whatsapp'] or "")

                submitted_profile = st.form_submit_button("Simpan Profil", use_container_width=True)

                if submitted_profile:
                    if not full_name.strip():
                        st.error("❌ Nama lengkap tidak boleh kosong")
                    else:
                        success, msg = update_user(
                            user_id,
                            full_name.strip(),
                            nickname.strip(),
                            address.strip(),
                            rt.strip(),
                            rw.strip(),
                            whatsapp.strip(),
                        )
                        if success:
                            st.session_state['user']['full_name'] = full_name.strip()
                            log_audit(user_id, 'UPDATE_PROFILE', 'Warga memperbarui profil sendiri')
                            st.success("✅ Profil berhasil diperbarui")
                        else:
                            st.error(f"❌ Gagal memperbarui profil: {msg}")

        with col_password:
            st.markdown("### 🔒 Ubah Password")
            with st.form("change_password_form"):
                current_password = st.text_input("Password Saat Ini", type="password")
                new_password = st.text_input("Password Baru", type="password", help="Minimal 6 karakter")
                confirm_password = st.text_input("Konfirmasi Password Baru", type="password")

                submitted_password = st.form_submit_button("Simpan Password", use_container_width=True)

                if submitted_password:
                    if not current_password or not new_password or not confirm_password:
                        st.warning("⚠️ Semua field password wajib diisi")
                    elif len(new_password) < 6:
                        st.error("❌ Password baru minimal 6 karakter")
                    elif new_password != confirm_password:
                        st.error("❌ Konfirmasi password tidak sesuai")
                    elif current_password == new_password:
                        st.warning("⚠️ Password baru tidak boleh sama dengan password lama")
                    else:
                        auth_check = authenticate_user(st.session_state['user']['username'], current_password)
                        if not auth_check:
                            st.error("❌ Password saat ini salah")
                        else:
                            update_user_password(user_id, new_password)
                            log_audit(user_id, 'CHANGE_PASSWORD', 'Warga mengganti password sendiri')
                            st.success("✅ Password berhasil diubah")

def dashboard_superuser():
    """Dashboard for Super User role"""
    # Header
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg, #9C27B0 0%, #7B1FA2 100%);">
        <h1>⚡ Dashboard Super User</h1>
        <p>Kontrol penuh sistem - Kelola user, monitoring, dan akses semua fitur</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 Kelola User", "🔐 Login Sebagai User Lain", "🧪 Data Dummy", "📜 Audit Log", "📊 Statistik Global", "⚙️ Pengaturan Jadwal"])
    
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
                role_options = ["warga", "panitia", "inputer", "superuser"]
                new_role = st.selectbox(
                    "Role",
                    role_options,
                    format_func=lambda r: (
                        "Admin" if r == "panitia" else "Panitia" if r == "inputer" else "Super User" if r == "superuser" else r.capitalize()
                    ),
                )
                
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
        st.subheader("🧪 Data Dummy Demo")
        st.info(
            "Aktifkan data dummy untuk demo cepat: akan menambah user demo, beberapa transaksi, penarikan/deposit, dan kategori pelengkap. Nonaktifkan untuk menghapus data demo tanpa menyentuh data asli.")

        dummy_active = get_setting('dummy_data_active', '0') == '1'

        if dummy_active:
            st.success("Data dummy sedang AKTIF")
            if st.button("❌ Nonaktifkan & Hapus Data Dummy", use_container_width=True):
                ok, msg = clear_dummy_data(st.session_state['user']['id'])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.warning("Data dummy saat ini NONAKTIF")
            if st.button("▶️ Aktifkan Data Dummy", use_container_width=True):
                ok, msg = seed_dummy_data(st.session_state['user']['id'])
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab4:
        _render_audit_log_tab('superuser', default_limit=300)
    
    with tab5:
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
            ui_metric_card("Total Transaksi", total_transactions, icon="🧾")
        
        with col2:
            ui_metric_card("Total Berat", f"{total_weight:.2f} Kg", icon="⚖️")
        
        with col3:
            ui_metric_card("Total Revenue", f"Rp {total_revenue:,.0f}", icon="💰")
        
        with col4:
            ui_metric_card("Pendapatan Admin", f"Rp {total_committee:,.0f}", icon="🏦")
        
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

    with tab6:
        _render_input_schedule_settings()

def dashboard_public():
    """Public dashboard shown when not logged in"""
    # Header Hero
    st.markdown("""
    <div style="text-align: center; padding: 3rem 1rem; background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%); border-radius: 20px; margin-bottom: 2rem; box-shadow: 0 10px 20px rgba(0,0,0,0.05);">
        <h1 style="color: #0D47A1; font-size: 2.5rem; margin-bottom: 0.5rem;">♻️ Bank Sampah Wani Luru RW 1</h1>
        <p style="color: #1565C0; font-size: 1.2rem; margin: 0;">Bersama Membangun Lingkungan yang Bersih dan Bernilai</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Top Cards ---
    st.subheader("📊 Statistik Terkini")
    col1, col2, col3, col4 = st.columns(4)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM transactions')
    total_trans = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(weight_kg) FROM transactions')
    total_weight = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(total_amount) FROM transactions')
    total_rev = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(DISTINCT warga_id) FROM transactions')
    active_warga = cursor.fetchone()[0]
    
    conn.close()
    
    with col1:
        ui_metric_card("Total Transaksi", total_trans, icon="🧾")
    with col2:
        ui_metric_card("Sampah Terkumpul", f"{total_weight:,.2f} Kg", icon="⚖️")
    with col3:
        ui_metric_card("Perputaran Ekonomi", f"Rp {total_rev:,.0f}", icon="💰")
    with col4:
        ui_metric_card("Warga Berpartisipasi", active_warga, icon="👥")
        
    st.markdown("---")
    
    # --- Charts ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.markdown("### 📈 Tren Partisipasi (30 Hari)")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date(transaction_date) as d, SUM(total_amount) as total
            FROM transactions 
            WHERE date(transaction_date) BETWEEN ? AND ?
            GROUP BY date(transaction_date)
            ORDER BY d
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        daily_data = cursor.fetchall()
        conn.close()
        
        if daily_data:
            df_trend = pd.DataFrame(daily_data, columns=['Tanggal', 'Total'])
            df_trend['Tanggal'] = pd.to_datetime(df_trend['Tanggal'])
            _render_trend_chart(df_trend)
        else:
            st.info("Data sedang diperbarui...")

    with c2:
        st.markdown("### 🏆 Top Warga")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.full_name, COUNT(*) as cnt
            FROM transactions t
            JOIN users u ON t.warga_id = u.id
            GROUP BY t.warga_id
            ORDER BY cnt DESC
            LIMIT 5
        ''')
        top_warga = cursor.fetchall()
        conn.close()
        
        if top_warga:
            df_top = pd.DataFrame(top_warga, columns=['Nama', 'Transaksi'])
            _render_top_warga_table(df_top, count_col='Transaksi')
        else:
            st.info("Data sedang diperbarui...")

    # Categories
    st.markdown("### ♻️ Komposisi Sampah")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.name, SUM(t.weight_kg) as total_w
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        GROUP BY t.category_id
        ORDER BY total_w DESC
        LIMIT 10
    ''')
    cat_stats = cursor.fetchall()
    conn.close()
    
    if cat_stats:
        df_cat = pd.DataFrame(cat_stats, columns=['Kategori', 'Total Berat (Kg)'])
        _render_category_bar_chart(df_cat)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #1E88E5; font-size: 0.9rem;">
        <p>💙 Bank Sampah Wani Luru RW 1 - Untuk Lingkungan yang Lebih Bersih dan Sejahtera</p>
        <p style="font-size: 0.8rem; color: #90CAF9;">© 2026 <a href="https://www.linkedin.com/in/galihprime/" target="_blank" style="color: #90CAF9; text-decoration: none;">Galih Primananda</a></p>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application"""
    
    # Check if user is logged in
    if not st.session_state['user']:
        sidebar_login()
        dashboard_public()
        return
    
    # Sidebar
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #1E88E5 0%, #0D47A1 100%); border-radius: 10px; margin-bottom: 1rem;">
            <h1 style="color: white; margin: 0; font-size: 1.8rem;">♻️ Bank Sampah Wani Luru RW 1</h1>
            <p style="color: #E3F2FD; margin: 0.5rem 0 0 0; font-size: 0.9rem;">Sistem Manajemen Digital</p>
        </div>
        """, unsafe_allow_html=True)
        
        # User info
        user = st.session_state['user']
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
                    <h2 style="margin: 0; color: #0D47A1; font-size: 1.3rem;">{_role_icon(user['role'])} {user['full_name']}</h2>
                    <span class="role-badge {_role_badge_class(user['role'])}" style="margin-top: 0.5rem;">
                        {_display_role_label(user['role'], uppercase=True)}
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
            elif user['role'] == 'inputer':
                st.markdown("""
                **Panitia dapat:**
                - ✅ Input transaksi sampah
                - ✅ Kelola kategori & harga
                - ✅ Update akun sendiri
                """)
            elif user['role'] == 'panitia':
                st.markdown("""
                **Admin dapat:**
                - ✅ Input transaksi sampah
                - ✅ Kelola keuangan warga
                - ✅ Lihat audit log aktivitas
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
            <p style="font-size: 0.75rem; color: #1E88E5; margin: 0;">💙 Bank Sampah Wani Luru RW 1</p>
            <p style="font-size: 0.7rem; color: #90CAF9; margin: 0.3rem 0 0 0;">© 2026 v1.0</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show appropriate dashboard based on role
    role = st.session_state['user']['role']
    
    if role == 'superuser':
        dashboard_superuser()
    elif role == 'pengepul':
        st.info("Role pengepul telah digabung ke admin. Mengarahkan ke dashboard admin.")
        dashboard_panitia()
    elif role == 'inputer':
        dashboard_inputer()
    elif role == 'panitia':
        dashboard_panitia()
    elif role == 'warga':
        dashboard_warga()
    else:
        st.error("Role tidak dikenali!")

if __name__ == '__main__':
    main()
