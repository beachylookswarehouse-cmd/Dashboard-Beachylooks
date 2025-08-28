import streamlit as st
import pandas as pd

st.title("📊 Dashboard Penjualan")

# Upload file
uploaded_file = st.file_uploader("Upload file Excel", type=["xlsx"])

if uploaded_file:
    # skiprows=3 agar baris ke-4 jadi header
    df = pd.read_excel(uploaded_file, skiprows=2)

    # Bersihkan kolom kosong
    df = df.dropna(axis=1, how='all')

    # Tampilkan Data Awal
    st.subheader("📋 Data Awal")
    st.dataframe(df)

    # Pilih kolom untuk filter
    st.sidebar.header("🔎 Filter Data")
    filter_col = st.sidebar.selectbox("Pilih Kolom untuk Filter", df.columns)

    if filter_col:
        unique_vals = df[filter_col].dropna().unique()
        selected_vals = st.sidebar.multiselect("Pilih nilai", unique_vals)

        if selected_vals:
            filtered_df = df[df[filter_col].isin(selected_vals)]
        else:
            filtered_df = df

        st.subheader("📋 Data Setelah Filter")
        st.dataframe(filtered_df)

        # Rekap total penjualan per produk
        if "PENJUALAN" in df.columns and "NAMA BARANG" in df.columns:
            st.subheader("📈 Rekap Penjualan per Produk")
            summary = (
                filtered_df.groupby("NAMA BARANG")["PENJUALAN"]
                .sum()
                .reset_index()
                .sort_values(by="PENJUALAN", ascending=False)
            )
            st.bar_chart(summary.set_index("NAMA BARANG"))
