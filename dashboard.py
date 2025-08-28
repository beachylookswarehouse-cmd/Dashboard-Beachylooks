# dashboard_cerdas_fix.py
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

# ---------------- HELPERS: External data (optional) ----------------
@lru_cache(maxsize=16)
def fetch_exchange_rate(base="USD", symbols="IDR"):
    """
    Fetch latest exchange rate from exchangerate.host (no API key required).
    Returns dict or None.
    """
    try:
        url = f"https://api.exchangerate.host/latest?base={base}&symbols={symbols}"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        rate = data.get("rates", {}).get(symbols)
        return {"base": base, "symbol": symbols, "rate": rate, "date": data.get("date")}
    except Exception:
        return None

@lru_cache(maxsize=8)
def fetch_inflation_dummy():
    """
    Placeholder: in production, replace with official source (Bank Indonesia / World Bank).
    Here return dummy last-month inflation %
    """
    return {"inflation_yoy_pct": 3.5, "as_of": datetime.utcnow().date().isoformat()}

def fetch_google_trends(keywords_list, months=6):
    """
    Try to fetch Google Trends via pytrends if available.
    Returns dict: {keyword: avg_interest}
    If fails, return None.
    """
    try:
        from pytrends.request import TrendReq
    except Exception:
        return None

    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        kw_list = keywords_list
        timeframe = f"today {max(1, months)}-m"
        pytrends.build_payload(kw_list, cat=0, timeframe=timeframe, geo="", gprop="")
        df = pytrends.interest_over_time()
        if df.empty:
            return None
        result = {}
        for kw in kw_list:
            if kw in df.columns:
                result[kw] = float(df[kw].mean())
        return result
    except Exception:
        return None

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("📂 Upload file Excel (format: baris 1-2 header tambahan, data mulai baris ke-3)", type=["xlsx"])
if not uploaded_file:
    st.info("Upload file Excel terlebih dahulu. Kolom yang diperlukan: NAMA BARANG, KODE WARNA, VARIAN, PENJUALAN, HARGA SATUAN, TOTAL")
    st.stop()

# ---------------- READ & VALIDATE ----------------
try:
    df = pd.read_excel(uploaded_file, skiprows=2)
except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

expected_cols = ["NAMA BARANG", "KODE WARNA", "VARIAN", "PENJUALAN", "HARGA SATUAN", "TOTAL"]
missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.error(f"Kolom yang hilang: {missing}. Pastikan file Excel memiliki kolom sesuai ketentuan.")
    st.stop()

df = df[expected_cols].copy()

# Basic cleaning
df["PENJUALAN"] = pd.to_numeric(df["PENJUALAN"], errors="coerce").fillna(0).astype(int)
df["HARGA SATUAN"] = pd.to_numeric(df["HARGA SATUAN"], errors="coerce").fillna(0)
df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce").fillna(0)

# ---------------- DATA DISPLAY ----------------
st.subheader("📑 Data Awal")
st.dataframe(df, use_container_width=True)

# ---------------- FILTER ----------------
st.sidebar.header("🔍 Filter Data Internal")
filters = {}
for col in expected_cols:
    opts = df[col].dropna().unique().tolist()
    sel = st.sidebar.multiselect(f"Filter {col}", opts)
    if sel:
        filters[col] = sel

df_filtered = df.copy()
for col, sel in filters.items():
    df_filtered = df_filtered[df_filtered[col].isin(sel)]

st.subheader("📑 Data Setelah Filter")
st.dataframe(df_filtered, use_container_width=True)

# ---------------- SUMMARY METRICS ----------------
st.subheader("📈 Ringkasan Penjualan")
col1, col2, col3, col4 = st.columns(4)
total_sales = int(df_filtered["PENJUALAN"].sum())
total_revenue = float(df_filtered["TOTAL"].sum())
avg_price = float(df_filtered["HARGA SATUAN"].mean()) if not df_filtered.empty else 0.0
unique_products = df_filtered["NAMA BARANG"].nunique()

col1.metric("Total Unit Terjual", f"{total_sales:,}")
col2.metric("Total Revenue (estimasi)", f"Rp {total_revenue:,.0f}")
col3.metric("Rata2 Harga Satuan", f"Rp {avg_price:,.0f}")
col4.metric("Produk Unik", f"{unique_products}")

# ---------------- OPTIONAL EXTERNAL DATA ----------------
external_info = {}
if use_external:
    with st.spinner("Mengambil data eksternal (kurs, inflasi, tren)..."):
        ex = fetch_exchange_rate(base="USD", symbols="IDR")
        infl = fetch_inflation_dummy()
        kw_list = [k.strip() for k in trend_keywords.split(",") if k.strip()]
        trends = fetch_google_trends(kw_list, months=int(trend_lookback_months))

        external_info["exchange"] = ex
        external_info["inflation"] = infl
        external_info["trends"] = trends

    st.subheader("🌐 Indikator Eksternal (opsional)")
    col_a, col_b, col_c = st.columns(3)

    # Kurs (safe display)
    ex = external_info.get("exchange")
    if ex and isinstance(ex, dict):
        rate = ex.get("rate")
        date_text = ex.get("date") or "N/A"
        try:
            if rate is not None:
                rate_num = float(rate)
                col_a.metric(f"Kurs {ex.get('base','?')}/{ex.get('symbol','?')}", f"{rate_num:,.2f}", help=f"tanggal {date_text}")
            else:
                col_a.info("Kurs: N/A (data tidak lengkap)")
        except Exception:
            col_a.info("Kurs: N/A (format rate invalid)")
    else:
        col_a.info("Kurs: tidak tersedia")

    # Inflasi (safe)
    infl_obj = external_info.get("inflation")
    if infl_obj and isinstance(infl_obj, dict):
        infl_v = infl_obj.get("inflation_yoy_pct")
        if infl_v is not None:
            try:
                col_b.metric("Inflasi YoY (estimasi)", f"{float(infl_v):.2f}%")
            except Exception:
                col_b.info("Inflasi: N/A")
        else:
            col_b.info("Inflasi: N/A")
    else:
        col_b.info("Inflasi: tidak tersedia")

    # Trends
    tr = external_info.get("trends")
    if tr is None:
        col_c.info("Tren: pytrends tidak tersedia / gagal ambil")
    elif isinstance(tr, dict) and len(tr) > 0:
        # show average interest per keyword
        for k, v in tr.items():
            try:
                col_c.write(f"- {k}: {float(v):.1f}")
            except Exception:
                col_c.write(f"- {k}: N/A")
    else:
        col_c.info("Tren: tidak ada data")

# ---------------- REKAP PER PRODUK ----------------
st.subheader("📦 Rekap Penjualan per Produk")
rekap = df_filtered.groupby("NAMA BARANG")["PENJUALAN"].sum().reset_index().sort_values("PENJUALAN", ascending=False)
st.dataframe(rekap, use_container_width=True)

# chart
st.subheader("📊 Grafik Penjualan per Produk")
fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(rekap))))
sns.barplot(data=rekap, x="PENJUALAN", y="NAMA BARANG", ax=ax, palette="Blues_d")
ax.set_facecolor("#f5f7fa")
fig.patch.set_facecolor("#f5f7fa")
plt.tight_layout()
st.pyplot(fig)

# ---------------- INSIGHT & REKOMENDASI (SMART) ----------------
st.subheader("💡 Insight Pintar & Rekomendasi")

if not rekap.empty:
    top = rekap.iloc[0]
    bottom = rekap.iloc[-1]
    avg_sales = rekap["PENJUALAN"].mean()

    st.markdown(f"- ✅ **Produk terlaris:** **{top['NAMA BARANG']}** — {top['PENJUALAN']:,} unit")
    st.markdown(f"- ⚠️ **Produk kurang laku:** **{bottom['NAMA BARANG']}** — {bottom['PENJUALAN']:,} unit")

    recommendations = []

    # Rule: low sales => suggest promo/bundling
    if bottom["PENJUALAN"] < max(5, avg_sales * 0.3):
        recommendations.append({
            "reason": f"Produk {bottom['NAMA BARANG']} memiliki penjualan rendah ({bottom['PENJUALAN']:,}).",
            "action": "Pertimbangkan diskon, bundling, atau promosi di kanal sosial."
        })

    # Rule: high sales => ensure stock
    if top["PENJUALAN"] > avg_sales * 1.8:
        recommendations.append({
            "reason": f"Produk {top['NAMA BARANG']} jauh di atas rata-rata.",
            "action": "Pastikan stok/materai cukup, pertimbangkan menaikkan produksi."
        })

    # Macro effect: kurs
    rate_val = None
    try:
        rate_val = external_info.get("exchange", {}).get("rate") if external_info.get("exchange") else None
        if rate_val is not None:
            rate_val = float(rate_val)
    except Exception:
        rate_val = None

    if rate_val is not None:
        if rate_val > 15000:
            recommendations.append({
                "reason": f"Kurs USD/IDR ~ {rate_val:,.0f} (pelemahan), bahan impor akan lebih mahal.",
                "action": "Pertimbangkan substitusi bahan lokal / sesuaikan harga jual."
            })
    # Trends-based recommendation
    if external_info.get("trends"):
        trends = external_info["trends"]
        if isinstance(trends, dict) and len(trends) > 0:
            try:
                avg_interest = sum([float(v) for v in trends.values()]) / len(trends)
                if avg_interest > 40:
                    recommendations.append({
                        "reason": f"Tren pencarian untuk keyword terkait kebaya tinggi (avg interest {avg_interest:.1f}).",
                        "action": "Fokus promosi koleksi kebaya modern; buat konten short-form (TikTok/Instagram)."
                    })
                elif avg_interest < 10:
                    recommendations.append({
                        "reason": f"Tren pencarian relatif rendah (avg interest {avg_interest:.1f}).",
                        "action": "Pertimbangkan diversifikasi koleksi / testing produk baru."
                    })
            except Exception:
                # ignore if trend numbers not usable
                pass

    # Show recommendations
    if recommendations:
        for rec in recommendations:
            st.info(f"• {rec['reason']}  \n➡️ Rekomendasi: **{rec['action']}**")
    else:
        st.success("Tidak ada rekomendasi kritikal saat ini. Data internal stabil.")
else:
    st.info("Data kosong setelah filter — tidak ada insight yang dapat dihasilkan.")

# ---------------- FORECASTING ----------------
st.subheader("📈 Forecasting Penjualan per Produk (Prophet)")

if len(df_filtered) < 2:
    st.warning("Tidak cukup data untuk forecasting (butuh minimal 2 baris).")
else:
    df_filtered = df_filtered.reset_index(drop=True)
    df_filtered["TANGGAL"] = pd.date_range(start="2024-01-01", periods=len(df_filtered), freq="M")

    produkt_list = df_filtered["NAMA BARANG"].unique().tolist()
    sel_prod = st.selectbox("Pilih Produk untuk Forecasting", produkt_list)

    dfp = df_filtered[df_filtered["NAMA BARANG"] == sel_prod]
    if dfp.empty or dfp["PENJUALAN"].sum() == 0:
        st.warning("Produk terpilih tidak memiliki data penjualan yang memadai.")
    else:
        dp = dfp.groupby("TANGGAL")["PENJUALAN"].sum().reset_index().rename(columns={"TANGGAL":"ds","PENJUALAN":"y"})
        try:
            m = Prophet()
            m.fit(dp)
            future = m.make_future_dataframe(periods=int(forecast_periods), freq="M")
            forecast = m.predict(future)
            fig1 = m.plot(forecast)
            fig1.patch.set_facecolor("#f5f7fa")
            st.pyplot(fig1)

            st.subheader("🔮 Prediksi Penjualan")
            display_df = forecast[["ds","yhat","yhat_lower","yhat_upper"]].tail(int(forecast_periods))
            display_df = display_df.rename(columns={"ds":"Tanggal","yhat":"Prediksi","yhat_lower":"Lower","yhat_upper":"Upper"})
            st.dataframe(display_df, use_container_width=True)

            avg_future = display_df["Prediksi"].mean()
            avg_past = dp["y"].mean()
            if avg_future > avg_past:
                st.success("Prediksi menunjukkan tren peningkatan penjualan untuk produk ini.")
            else:
                st.warning("Prediksi menunjukkan tren stagnan/penurunan untuk produk ini.")
        except Exception as e:
            st.error(f"Gagal menjalankan forecasting Prophet: {e}")

# ---------------- EXPORT / SAVE ----------------
st.subheader("💾 Ekspor / Simpan Hasil")
colx1, colx2 = st.columns(2)
with colx1:
    if st.button("Download Rekap CSV"):
        tmp = rekap.copy()
        tmp.to_csv("rekap_penjualan.csv", index=False)
        with open("rekap_penjualan.csv", "rb") as f:
            st.download_button("Klik untuk download rekap", data=f, file_name="rekap_penjualan.csv")

with colx2:
    if st.button("Download Filtered Data"):
        buf = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("Download data hasil filter", data=buf, file_name="data_filtered.csv", mime="text/csv")

st.markdown("---")
st.caption("Catatan: integrasi data eksternal bersifat opsional. Atur di sidebar. Kamu bisa mengganti sumber data eksternal dan logika rekomendasi sesuai strategi bisnis.")


