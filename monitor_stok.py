import streamlit as st
import pandas as pd

st.title("📊 Dashboard Monitoring Stok Produk")

# === Helper: normalisasi & pemetaan kolom ===
def normalize(s: str) -> str:
    return str(s).replace("\ufeff", "").strip().lower()

# Alias kolom -> standar
ALIAS_TO_STANDARD = {
    # Nama Produk
    "nama produk": "Nama Produk",
    "product name": "Nama Produk",
    "product_name": "Nama Produk",
    "et_title_product_name": "Nama Produk",

    # Nama Variasi
    "nama variasi": "Nama Variasi",
    "variation name": "Nama Variasi",
    "variation_name": "Nama Variasi",
    "et_title_variation_name": "Nama Variasi",

    # Stok
    "stok": "Stok",
    "stock": "Stok",
    "qty": "Stok",
    "quantity": "Stok",
    "et_title_variation_stock": "Stok",
}

REQUIRED = {"Nama Produk", "Nama Variasi", "Stok"}

uploaded_file = st.file_uploader("Upload file data produk (CSV/XLSX)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Baca file
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, sheet_name=0)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        st.stop()

    # --- Rename kolom otomatis sesuai alias ---
    orig_cols = list(df.columns)
    rename_map = {}
    for c in df.columns:
        key = normalize(c)
        if key in ALIAS_TO_STANDARD:
            rename_map[c] = ALIAS_TO_STANDARD[key]
    df = df.rename(columns=rename_map)

    # Info kolom hasil deteksi
    st.caption(f"Kolom terdeteksi (setelah pemetaan): {list(df.columns)}")

    # --- Validasi kolom wajib ---
    if not REQUIRED.issubset(df.columns):
        st.error(
            "File belum memiliki kolom wajib.\n\n"
            f"Diharuskan ada: {', '.join(REQUIRED)}\n"
            f"Kolom yang ditemukan: {list(orig_cols)}"
        )
        st.stop()

    # --- Bersihkan & tipe data ---
    for col in ["Nama Produk", "Nama Variasi"]:
        df[col] = df[col].astype(str).fillna("").str.strip()

    # Stok -> angka
    df["Stok"] = (
        df["Stok"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)  # ambil angka dari teks
        .fillna("0")
        .astype(int)
    )

    # --- Kontrol & filter ---
    colA, colB = st.columns(2)
    batas_stok = colA.number_input("Tampilkan produk dengan stok ≤", min_value=0, value=5, step=1)

    # Multiselect untuk cari banyak produk sekaligus
    produk_list = sorted(df["Nama Produk"].unique().tolist())
    selected_produk = colB.multiselect(
        "Cari Nama Produk (bisa pilih sampai 6)", 
        options=produk_list,
        default=[],
        max_selections=6
    )

    df_view = df.copy()
    if selected_produk:
        df_view = df_view[df_view["Nama Produk"].isin(selected_produk)]

    df_stok_menipis = df_view[df_view["Stok"] <= batas_stok].sort_values("Stok", ascending=True)

    # --- Tampilkan hasil ---
    st.subheader("📉 Produk dengan Stok Menipis")
    if df_stok_menipis.empty:
        st.success("🎉 Tidak ada produk dengan stok menipis sesuai filter.")
    else:
        st.dataframe(df_stok_menipis[["Nama Produk", "Nama Variasi", "Stok"]], use_container_width=True)

    # --- Ringkasan ---
    st.subheader("📦 Ringkasan Stok (setelah filter pencarian)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Jumlah Baris", len(df_view))
    col2.metric("Total Stok", int(df_view["Stok"].sum()))
    col3.metric("Produk Menipis", len(df_stok_menipis))

    # --- Export hasil filter ---
    st.subheader("⬇️ Export Data")
    csv_all = df_view[["Nama Produk", "Nama Variasi", "Stok"]].to_csv(index=False).encode("utf-8")
    csv_low = df_stok_menipis[["Nama Produk", "Nama Variasi", "Stok"]].to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV (Semua Data Tersaring)", csv_all, "stok_all_filtered.csv", "text/csv")
    st.download_button("Download CSV (Stok Menipis)", csv_low, "stok_menipis.csv", "text/csv")

else:
    st.info(
        "Silakan upload CSV/XLSX. Header yang didukung otomatis: "
        "`et_title_product_name`, `et_title_variation_name`, `et_title_variation_stock` "
        "→ akan dipetakan menjadi `Nama Produk`, `Nama Variasi`, `Stok`."
    )
