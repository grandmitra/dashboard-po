import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Dashboard PO vs Penerimaan", layout="wide", page_icon="📊")

# --- FITUR KEAMANAN PASSWORD ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Tampilan Halaman Login
    st.markdown("""
        <div style='text-align: center; padding-top: 50px;'>
            <h1>🔐 Akses Terbatas</h1>
            <p>Silakan masukkan password untuk mengakses Dashboard PO</p>
        </div>
    """, unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1, 1])
    with col_login:
        password = st.text_input("Password", type="password")
        if st.button("Masuk"):
            if password == "mbg212":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Password Salah!")
    return False

# Jalankan pengecekan password, jika benar baru tampilkan konten dashboard
if check_password():
    # Custom CSS untuk kartu metrik berwarna
    st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        /* Warna border kiri untuk tiap kolom metrik */
        [data-testid="column"]:nth-of-type(1) div[data-testid="stMetric"] { border-left: 5px solid #0d6efd; }
        [data-testid="column"]:nth-of-type(2) div[data-testid="stMetric"] { border-left: 5px solid #6f42c1; }
        [data-testid="column"]:nth-of-type(3) div[data-testid="stMetric"] { border-left: 5px solid #dc3545; }
        [data-testid="column"]:nth-of-type(4) div[data-testid="stMetric"] { border-left: 5px solid #198754; }
        </style>
        """, unsafe_allow_html=True)

    # 2. FUNGSI LOAD DATA
    @st.cache_data(ttl=600)
    def load_data_sheets():
        sheet_id = "1a9yOidIrjGe1Hfm9ILz1URAQ4KJWo_JO0wvEBMNdD1U"
        sheet_name = "Sheet2"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        
        df = pd.read_csv(url)
        # Bersihkan spasi pada teks
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                
        # Konversi Tanggal
        for col in ['FORM_DATE', 'TGL_RCVD']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        # Konversi Angka
        cols_num = ['NET_AMOUNT', 'NET_AMOUNT_RCVD', 'QTY', 'QTY RCVD']
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df

    try:
        df_raw = load_data_sheets()

        # --- 3. SIDEBAR (FILTER DAN PENGURUTAN) ---
        st.sidebar.header("Filter dan Pengurutan")
        
        # Pencarian
        search_query = st.sidebar.text_input("Cari (No. PO, Vendor, Item, Kode)", placeholder="Masukkan kata kunci...")

        # Filter Vendor
        list_vendor = ["Semua Vendor"] + sorted(df_raw['VENDOR_NAME'].dropna().unique().tolist())
        sel_vendor = st.sidebar.selectbox("Filter Vendor", list_vendor)

        # Filter Tipe PO
        list_tipe = ["Semua Tipe"] + sorted(df_raw['PO_TYPE'].dropna().unique().tolist()) if 'PO_TYPE' in df_raw.columns else ["Semua Tipe"]
        sel_tipe = st.sidebar.selectbox("Tipe PO", list_tipe)

        # Filter On Consignment
        sel_consig = st.sidebar.selectbox("On Consignment", ["Semua", "Yes", "No"])

        # Filter Tanggal
        if 'FORM_DATE' in df_raw.columns:
            min_date = df_raw['FORM_DATE'].min().date()
            max_date = df_raw['FORM_DATE'].max().date()
            date_range = st.sidebar.date_input("Filter Tanggal PO", [min_date, max_date])

        # Urutkan Berdasarkan
        sort_by = st.sidebar.selectbox("Urutkan Berdasarkan", ["Nomor PO", "Tanggal", "Nilai Amount"])
        sort_order = st.sidebar.selectbox("Arah Urutan", ["Terbaru/Terbesar", "Terlama/Terkecil"])

        st.sidebar.divider()
        if st.sidebar.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        if st.sidebar.button("🚪 Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

        # --- 4. LOGIKA FILTERING ---
        df_filtered = df_raw.copy()

        if search_query:
            mask = df_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            df_filtered = df_filtered[mask]
        
        if sel_vendor != "Semua Vendor":
            df_filtered = df_filtered[df_filtered['VENDOR_NAME'] == sel_vendor]
        
        if sel_tipe != "Semua Tipe":
            df_filtered = df_filtered[df_filtered['PO_TYPE'] == sel_tipe]
            
        if sel_consig != "Semua":
            df_filtered = df_filtered[df_filtered['ON_CONSIGNMENT'] == sel_consig]

        if 'FORM_DATE' in df_raw.columns and len(date_range) == 2:
            df_filtered = df_filtered[(df_filtered['FORM_DATE'].dt.date >= date_range[0]) & 
                                      (df_filtered['FORM_DATE'].dt.date <= date_range[1])]

        # Logika Sorting
        sort_map = {"Nomor PO": "FORM_NO", "Tanggal": "FORM_DATE", "Nilai Amount": "NET_AMOUNT"}
        is_ascending = True if sort_order == "Terlama/Terkecil" else False
        df_filtered = df_filtered.sort_values(by=sort_map[sort_by], ascending=is_ascending)

        # --- 5. TAMPILAN MATRIK UTAMA ---
        st.title("Dashboard PO vs Penerimaan")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL PO", f"{df_filtered['FORM_NO'].nunique():,}")
        m2.metric("TOTAL ITEM LINE", f"{len(df_filtered):,}")
        m3.metric("NET AMOUNT", f"Rp {df_filtered['NET_AMOUNT'].sum():,.0f}")
        m4.metric("NET RECEIVED", f"Rp {df_filtered['NET_AMOUNT_RCVD'].sum():,.0f}")

        st.divider()

        # --- 6. GRAFIK TIMELINE BULANAN ---
        st.subheader("📈 Tren PO vs Received per Bulan")
        if 'FORM_DATE' in df_filtered.columns:
            df_trend = df_filtered.copy()
            df_trend['BULAN'] = df_trend['FORM_DATE'].dt.to_period('M').astype(str)
            df_monthly = df_trend.groupby('BULAN')[['NET_AMOUNT', 'NET_AMOUNT_RCVD']].sum().reset_index()
            
            fig_trend = px.line(df_monthly, x='BULAN', y=['NET_AMOUNT', 'NET_AMOUNT_RCVD'],
                                labels={'value': 'Total Nilai (Rp)', 'BULAN': 'Periode Bulan'},
                                markers=True, line_shape="spline",
                                color_discrete_map={"NET_AMOUNT": "#0d6efd", "NET_AMOUNT_RCVD": "#198754"})
            st.plotly_chart(fig_trend, use_container_width=True)

        # --- 7. TABEL DRILLDOWN ---
        st.subheader("📋 Data Purchase Order (Klik untuk Detail)")
        df_summary = df_filtered.groupby('FORM_NO').agg({
            'FORM_DATE': 'first',
            'VENDOR_NAME': 'first',
            'NET_AMOUNT': 'sum',
            'NET_AMOUNT_RCVD': 'sum'
        }).reset_index()

        selected_event = st.dataframe(
            df_summary,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Detail Item jika baris dipilih
        if len(selected_event.selection.rows) > 0:
            idx = selected_event.selection.rows[0]
            po_id = df_summary.iloc[idx]['FORM_NO']
            
            st.success(f"### Detail Item untuk PO: {po_id}")
            df_detail = df_raw[df_raw['FORM_NO'] == po_id]
            cols_drilldown = [
                'ITEM_NO', 'ITEM_NAME', 'QTY', 'ITEM_UNIT', 'QTY_PCS', 
                'UNIT_PRICE', 'DISC_REMARK', 'NET_AMOUNT', 'NO RCVD', 
                'TGL_RCVD', 'QTY RCVD', 'NET_AMOUNT_RCVD', 'INVOICE_NO'
            ]
            available = [c for c in cols_drilldown if c in df_detail.columns]
            st.dataframe(df_detail[available], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Gagal memuat dashboard: {e}")

# Footer
st.markdown("<br><hr><center><small>Grand Mitra Bangunan &copy; 2026</small></center>", unsafe_allow_html=True)
