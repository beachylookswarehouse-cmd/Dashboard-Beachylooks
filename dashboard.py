import streamlit as st
import pandas as pd
from prophet import Prophet
import matplotlib.pyplot as plt

st.title("📊 Dashboard Penjualan + Forecasting")

# Upload file Excel
uploaded_file = st.file_uploader("Upload file Excel", type=["xlsx"])

if uploaded_file:
    # Baca data mulai baris ke-3 (karena baris 1-2 header tambahan di file kamu)
    df = pd.read_excel(uploaded_file, skiprows=2)

    # Pastikan hanya ambil kolom sesuai
    expected_cols = ["NAMA BARANG", "KODE WARNA", "VARIAN", "PENJUALAN", "HARGA SATUAN", "TOTAL"]
    df = df[expected_cols]

    # Tampilkan data asli
    st.subheader("📑 Data Awal")
    st.dataframe(df)

    # ---------------- FILTER ----------------
    st.sidebar.header("🔍 Filter Data")
    filters = {}
    for col in expected_cols:
        options = df[col].dropna().unique().tolist()
        selected = st.sidebar.multiselect(f"Filter {col}", options)
        if selected:
            filters[col] = selected

    # Terapkan filter
    df_filtered = df.copy()
    for col, selected in filters.items():
        df_filtered = df_filtered[df_filtered[col].isin(selected)]

    st.subheader("📑 Data Setelah Filter")
    st.dataframe(df_filtered)

    # ---------------- REKAP PENJUALAN ----------------
    st.subheader("📦 Rekap Penjualan per Produk")
    rekap = df_filtered.groupby("NAMA BARANG")["PENJUALAN"].sum().reset_index()
    st.dataframe(rekap)

    # ---------------- FORECASTING ----------------
    st.subheader("📈 Forecasting Penjualan per Produk")

    # Simulasi: tambah kolom "TANGGAL" (misalnya data bulanan Jan, Feb, dst)
    # NOTE: Kalau file kamu ada kolom tanggal asli, ganti bagian ini
    df_filtered["TANGGAL"] = pd.date_range(start="2024-01-01", periods=len(df_filtered), freq="M")

    produk_list = df_filtered["NAMA BARANG"].unique().tolist()
    selected_produk = st.selectbox("Pilih Produk untuk Forecasting", produk_list)

    df_produk = df_filtered[df_filtered["NAMA BARANG"] == selected_produk]

    if not df_produk.empty:
        # Siapkan data untuk Prophet
        data_prophet = df_produk.groupby("TANGGAL")["PENJUALAN"].sum().reset_index()
        data_prophet.rename(columns={"TANGGAL": "ds", "PENJUALAN": "y"}, inplace=True)

        # Jalankan model Prophet
        model = Prophet()
        model.fit(data_prophet)

        future = model.make_future_dataframe(periods=3, freq="M")  # Prediksi 3 bulan ke depan
        forecast = model.predict(future)

        # Plot hasil forecasting
        fig1 = model.plot(forecast)
        st.pyplot(fig1)

        # Tabel hasil prediksi
        st.subheader("🔮 Prediksi Penjualan 3 Bulan ke Depan")
        prediksi = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(3)
        st.dataframe(prediksi)
