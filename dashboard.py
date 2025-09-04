# dashboard_gabungan.py
import os
import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt
import seaborn as sns
import requests
from datetime import datetime
from functools import lru_cache

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="📊 Smart Dashboard", layout="wide")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa, #e6ecf3); color: #2c3e50; font-family: 'Segoe UI', sans-serif; }
    h1 { color: #1a3d7c; text-align: center; font-size: 2.0rem !important; margin-bottom: 14px; }
    h2, h3, h4 { color: #2c3e50; border-left: 4px solid #1a73e8; padding-left: 10px; }
    .dataframe { border: 1px solid #d1d9e6; border-radius: 10px; background-color: #ffffff; }
    section[data-testid="stSidebar"] { background: #f0f4fa; color: #2c3e50; }
    button { background: #1a73e8 !important; color: white !important; border-radius: 8px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Smart Dashboard")

# ---------------- SIDEBAR OPTIONS ----------------
st.sidebar.header("⚙️ Pengaturan Dashboard")
use_external = st.sidebar.checkbox("Ambil data eksternal (makro + tren)", value=False)
trend_keywords = st.sidebar.text_input("Keyword Tren (pisah koma)", value="kebaya,kebaya modern,kebaya modern indonesia")
trend_lookback_months = st.sidebar.number_input("Periode tren (bulan)", min_value=1, max_value=36, value=6)
forecast_periods = st.sidebar.number_input("Forecast horizon (bulan)", min_value=1, max_value=12, value=3)
st.sidebar.markdown("---")
st.sidebar.markdown("⚠️ Data eksternal bersifat opsional. Jika tidak tersedia, dashboard tetap berfungsi memakai data internal.")

# ---------------- HELPERS ----------------
@lru_cache(maxsize=16)
def fetch_exchange_rate(base="USD", symbols="IDR"):
    try:
        url = f"https://api.exchangerate.host/latest?base={base}&symbols={symbols}"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        return {"base": base, "symbol": symbols, "rate": data.get("rates", {}).get(symbols), "date": data.get("date")}
    except Exception:
        return None

@lru_cache(maxsize=8)
def fetch_inflation_dummy():
    return {"inflation_yoy_pct": 3.5, "as_of": datetime.utcnow().date().isoformat()}

def fetch_google_trends(keywords_list, months=6):
    try:
        from pytrends.request import TrendReq
    except Exception:
        return None
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        timeframe = f"today {max(1, months)}-m"
        pytrends.build_payload(keywords_list, timeframe=timeframe)
        df = pytrends.interest_over_time()
        if df.empty: return None
        return {kw: float(df[kw].mean()) for kw in keywords_list if kw in df.columns}
    except Exception:
        return None

def read_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    else:
        return pd.read_excel(uploaded_file, sheet_name=0)

# ---------------- FILE UPLOAD ----------------
st.subheader("📂 Upload Data")
sales_file = st.file_uploader("Upload file **Penjualan** (XLSX/CSV)", type=["xlsx", "csv"])
stock_file = st.file_uploader("Upload file **Stok Produk** (XLSX/CSV)", type=["xlsx", "csv"])

if not sales_file or not stock_file:
    st.info("Upload kedua file (Penjualan & Stok) terlebih dahulu.")
    st.stop()

# ---------------- READ SALES ----------------
try:
    df = pd.read_excel(sales_file, skiprows=2) if sales_file.name.endswith("xlsx") else pd.read_csv(sales_file, skiprows=2)
except Exception as e:
    st.error(f"Gagal membaca file penjualan: {e}")
    st.stop()

expected_sales = ["NAMA BARANG", "KODE WARNA", "VARIAN", "PENJUALAN", "HARGA SATUAN", "TOTAL"]
missing_sales = [c for c in expected_sales if c not in df.columns]
if missing_sales:
    st.error(f"Kolom yang hilang di file penjualan: {missing_sales}")
    st.stop()

df = df[expected_sales].copy()
df["PENJUALAN"] = pd.to_numeric(df["PENJUALAN"], errors="coerce").fillna(0).astype(int)
df["HARGA SATUAN"] = pd.to_numeric(df["HARGA SATUAN"], errors="coerce").fillna(0)
df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce").fillna(0)

# ---------------- READ STOCK ----------------
try:
    stock_df = read_file(stock_file)
except Exception as e:
    st.error(f"Gagal membaca file stok: {e}")
    st.stop()

# mapping alias → standar
col_map_stock = {
    "et_title_product_name": "Nama Produk",
    "et_title_variation_name": "Nama Variasi",
    "et_title_variation_stock": "Stok",
    "Product Name": "Nama Produk",
    "Variation Name": "Nama Variasi",
    "Stock": "Stok"
}
stock_df.rename(columns=lambda x: col_map_stock.get(x.strip(), x.strip()), inplace=True)

expected_stock = ["Nama Produk", "Nama Variasi", "Stok"]
missing_stock = [c for c in expected_stock if c not in stock_df.columns]
if missing_stock:
    st.error(f"Kolom yang hilang di file stok: {missing_stock}")
    st.stop()

stock_df = stock_df[expected_stock].copy()
stock_df["Stok"] = pd.to_numeric(stock_df["Stok"], errors="coerce").fillna(0).astype(int)

# ---------------- DISPLAY SALES ----------------
st.subheader("📑 Data Penjualan")
st.dataframe(df, use_container_width=True)

# ---------------- DISPLAY STOCK ----------------
st.subheader("📑 Data Stok Produk")
st.dataframe(stock_df, use_container_width=True)

# ---------------- FILTER SALES ----------------
st.sidebar.header("🔍 Filter Data Penjualan")
filters = {}
for col in expected_sales:
    opts = df[col].dropna().unique().tolist()
    sel = st.sidebar.multiselect(f"Filter {col}", opts)
    if sel:
        filters[col] = sel
df_filtered = df.copy()
for col, sel in filters.items():
    df_filtered = df_filtered[df_filtered[col].isin(sel)]

# ---------------- SUMMARY SALES ----------------
st.subheader("📈 Ringkasan Penjualan")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Unit Terjual", f"{df_filtered['PENJUALAN'].sum():,}")
col2.metric("Total Revenue", f"Rp {df_filtered['TOTAL'].sum():,.0f}")
col3.metric("Rata2 Harga", f"Rp {df_filtered['HARGA SATUAN'].mean():,.0f}")
col4.metric("Produk Unik", f"{df_filtered['NAMA BARANG'].nunique()}")

# ---------------- MONITOR STOCK ----------------
st.subheader("📉 Monitoring Stok Menipis")
batas_stok = st.number_input("Tampilkan produk dengan stok ≤", min_value=0, value=5, step=1)
produk_list = sorted(stock_df["Nama Produk"].dropna().astype(str).str.strip().unique().tolist())
selected_produk = st.multiselect("Cari Nama Produk (bisa pilih sampai 6)", options=produk_list, default=[], max_selections=6)

df_view = stock_df.copy()
if selected_produk:
    df_view = df_view[df_view["Nama Produk"].isin(selected_produk)]

df_stok_menipis = df_view[df_view["Stok"] <= batas_stok].sort_values("Stok", ascending=True)
if df_stok_menipis.empty:
    st.success("🎉 Tidak ada produk dengan stok menipis sesuai filter.")
else:
    st.dataframe(df_stok_menipis, use_container_width=True)

# ---------------- REKAP PENJUALAN PER PRODUK ----------------
st.subheader("📦 Rekap Penjualan per Produk")
rekap = df_filtered.groupby("NAMA BARANG")["PENJUALAN"].sum().reset_index().sort_values("PENJUALAN", ascending=False)
st.dataframe(rekap, use_container_width=True)

st.subheader("📊 Grafik Penjualan")
fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(rekap))))
sns.barplot(data=rekap, x="PENJUALAN", y="NAMA BARANG", ax=ax, palette="Blues_d")
ax.set_facecolor("#f5f7fa")
fig.patch.set_facecolor("#f5f7fa")
plt.tight_layout()
st.pyplot(fig)

# ---------------- FORECASTING ----------------
st.subheader("🔮 Forecasting Penjualan per Produk")

produk_for_forecast = st.selectbox("Pilih Produk untuk Forecasting", df_filtered["NAMA BARANG"].unique())
periode = forecast_periods

if produk_for_forecast:
    # Dummy: generate data tanggal harian
    df_forecast_base = df_filtered[df_filtered["NAMA BARANG"] == produk_for_forecast]
    df_time = pd.DataFrame({
        "ds": pd.date_range(start="2024-01-01", periods=len(df_forecast_base), freq="D"),
        "y": df_forecast_base["PENJUALAN"].values
    })

    if len(df_time) > 2:
        m = Prophet()
        m.fit(df_time)
        future = m.make_future_dataframe(periods=periode * 30, freq="D")
        forecast = m.predict(future)

        st.write(f"📌 Forecasting {produk_for_forecast} {periode} bulan ke depan")
        fig1 = m.plot(forecast)
        st.pyplot(fig1)

        # tampilkan tabel ringkas
        st.dataframe(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(15))
    else:
        st.warning("Data produk terlalu sedikit untuk dilakukan forecasting.")

# ---------------- REKOMENDASI RESTOCK ----------------
st.subheader("📦 Rekomendasi Produk untuk Restock")

# hitung rata-rata penjualan per produk
avg_sales = df_filtered.groupby("NAMA BARANG")["PENJUALAN"].mean().reset_index()
avg_sales.rename(columns={"PENJUALAN": "Rata2 Penjualan"}, inplace=True)

# gabung dengan stok
df_restock = pd.merge(avg_sales, stock_df.groupby("Nama Produk")["Stok"].sum().reset_index(),
                      left_on="NAMA BARANG", right_on="Nama Produk", how="left")

# rekomendasi: stok < rata-rata penjualan
df_restock["Perlu Restock?"] = df_restock["Stok"] < df_restock["Rata2 Penjualan"]
restock_needed = df_restock[df_restock["Perlu Restock?"] == True].sort_values("Stok")

if restock_needed.empty:
    st.success("🎉 Semua stok masih aman, belum ada produk yang perlu direstock segera.")
else:
    st.warning("⚠️ Produk berikut direkomendasikan untuk restock:")
    st.dataframe(restock_needed[["NAMA BARANG", "Stok", "Rata2 Penjualan"]], use_container_width=True)
