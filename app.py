import streamlit as st
import pandas as pd
import plotly.express as px

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="Dashboard PO vs Penerimaan", layout="wide", page_icon="📊")

# 2. FITUR LOGIN PASSWORD
def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    # Tampilan Form Login
    st.markdown("<h2 style='text-align: center;'>🔐 Restricted Access</h2>", unsafe_allow_html=True)
    cols = st.columns([1, 2, 1])
    with cols[1]:
        password = st.text_input("Masukkan Password Akses", type="password")
        if st.button("Login"):
            if password == "mbg212":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Password salah, Brody!")
    return False

# Jalankan pengecekan password
if check_password():

    # --- KODE DASHBOARD KAMU MULAI DARI SINI ---
    
    st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: #ffffff;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        [data-testid="column"]:nth-of-type(1) div[data-testid="stMetric"] { border-left: 5px solid #0d6efd; }
        [data-testid="column"]:nth-of-type(2) div[data-testid="stMetric"] { border-left: 5px solid #6f42c1; }
        [data-testid="column"]:nth-of-type(3) div[data-testid="stMetric"] { border-left: 5px solid #dc3545; }
        [data-testid="column"]:nth-of-type(4) div[data-testid="stMetric"] { border-left: 5px solid #198754; }
        </style>
        """, unsafe_allow_html=True)

    @st.cache_data(ttl=600)
    def load_data_sheets():
        sheet_id = "1a9yOidIrjGe1Hfm9ILz1URAQ4KJWo_JO0wvEBMNdD1U"
        sheet_name = "Sheet2"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        try:
            df = pd.read_csv(url)
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
            if 'FORM_DATE' in df.columns:
                df['FORM_DATE'] = pd.to_datetime(df['FORM_DATE'], errors='coerce')
            num_cols = ['NET_AMOUNT', 'NET_AMOUNT_RCVD', 'QTY', 'QTY RCVD']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df
        except: return pd.DataFrame()

    df_raw = load_data_sheets()

    if not df_raw.empty:
        # --- SIDEBAR ---
        st.sidebar.header("Filter dan Pengurutan")
        search_query = st.sidebar.text_input("Cari No. PO, Vendor, Item")
        
        list_vendor = ["Semua Vendor"] + sorted(df_raw['VENDOR_NAME'].unique().tolist())
        sel_vendor = st.sidebar.selectbox("Filter Vendor", list_vendor)
        
        list_tipe = ["Semua Tipe"] + sorted(df_raw['PO_TYPE'].unique().tolist())
        sel_tipe = st.sidebar.selectbox("Tipe PO", list_tipe)

        if st.sidebar.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        if st.sidebar.button("🚪 Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

        # --- FILTER LOGIC ---
        df_f = df_raw.copy()
        if search_query:
            df_f = df_f[df_f.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)]
        if sel_vendor != "Semua Vendor":
            df_f = df_f[df_f['VENDOR_NAME'] == sel_vendor]
        if sel_tipe != "Semua Tipe":
            df_f = df_f[df_f['PO_TYPE'] == sel_tipe]

        # --- DASHBOARD UI ---
        st.title("📊 Dashboard PO vs Penerimaan")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TOTAL PO", f"{df_f['FORM_NO'].nunique():,}")
        c2.metric("ITEM LINE", f"{len(df_f):,}")
        c3.metric("NET AMOUNT", f"Rp {df_f['NET_AMOUNT'].sum():,.0f}")
        c4.metric("NET RECEIVED", f"Rp {df_f['NET_AMOUNT_RCVD'].sum():,.0f}")

        st.divider()

        # TIMELINE
        st.subheader("📈 Tren Bulanan")
        df_t = df_f.copy()
        df_t['BULAN'] = df_t['FORM_DATE'].dt.to_period('M').astype(str)
        df_m = df_t.groupby('BULAN')[['NET_AMOUNT', 'NET_AMOUNT_RCVD']].sum().reset_index()
        st.plotly_chart(px.line(df_m, x='BULAN', y=['NET_AMOUNT', 'NET_AMOUNT_RCVD'], markers=True), use_container_width=True)

        # TABEL UTAMA (DRILLDOWN)
        st.subheader("📋 Daftar Purchase Order")
        df_sum = df_f.groupby('FORM_NO').agg({'FORM_DATE':'first','VENDOR_NAME':'first','NET_AMOUNT':'sum','NET_AMOUNT_RCVD':'sum'}).reset_index()
        event = st.dataframe(df_sum, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

        if len(event.selection.rows) > 0:
            idx = event.selection.rows[0]
            po_selected = df_sum.iloc[idx]['FORM_NO']
            st.success(f"### Detail Items: {po_selected}")
            df_d = df_raw[df_raw['FORM_NO'] == po_selected]
            st.dataframe(df_d, use_container_width=True)

    else:
        st.error("Data tidak ditemukan atau koneksi bermasalah.")
