# -*- coding: utf-8 -*-
"""
app.py – Générateur CPN  (DFRXHYBCPNA / AFRXHYBCPNA)
• Déposez :
    1. Un fichier principal (Réf. interne + Réf. client).
    2. Une liste clients (une seule colonne).
• Choisissez les colonnes au moyen de menus déroulants (1 = première colonne …).
• Génère :
    – DFRXHYBCPNAyyMMdd0000  (TSV, sans en-tête)
    – AFRXHYBCPNAyyMMdd0000  (acknowledgement TXT)
"""

from __future__ import annotations
from datetime import datetime
from itertools import product
from io import BytesIO, StringIO
import io

import pandas as pd
import streamlit as st

# ───────────────────────── PAGE CONFIG ─────────────────────────
st.set_page_config(page_title="CPN", page_icon="📑", layout="wide")
st.title("📑 Générateur CPN (DFRXHYBCPNA / AFRXHYBCPNA)")

# ───────────────────────── UTILS ─────────────────────────
def read_any(file):
    name = file.name.lower()
    if name.endswith(".csv"):
        for enc in ("utf-8", "latin1", "cp1252"):
            try:
                file.seek(0)
                return pd.read_csv(file, encoding=enc)
            except UnicodeDecodeError:
                file.seek(0)
        raise ValueError("Encodage CSV non reconnu.")
    return pd.read_excel(file, engine="openpyxl")

def to_tsv_bytes(df: pd.DataFrame) -> bytes:
    buf = StringIO()
    df.to_csv(buf, sep="\t", index=False, header=False)
    return buf.getvalue().encode("utf-8")

def cpn_logic(df_principal: pd.DataFrame, col_cli: int, col_int: int,
              series_cli: pd.Series):
    """Retourne le PF et les métadonnées des fichiers."""
    # 1-based → 0-based
    col_cli -= 1
    col_int -= 1

    lst_int = (
        df_principal.iloc[:, col_int]
        .dropna().astype(str).str.strip()
        .tolist()
    )
    lst_cli = series_cli.dropna().astype(str).str.strip().tolist()

    pf = pd.DataFrame(
        (
            (ref_int, ref_cli, ref_int)           # 3ᵉ col = valeur interne
            for ref_int, ref_cli in product(lst_int, lst_cli)
        ),
        columns=["1", "2", "3"],
    )

    today = datetime.today().strftime("%y%m%d")
    dfrx_name = f"DFRXHYBCPNA{today}0000"
    afrx_name = f"AFRXHYBCPNA{today}0000"
    afrx_txt  = (
        f"DFRXHYBCPNA{today}000148250201IT"
        f"DFRXHYBCPNA{today}CPNAHYBFRX                    OK000000"
    )
    return pf, dfrx_name, afrx_name, afrx_txt

# ───────────────────────── INTERFACE ─────────────────────────
colA, colB = st.columns(2)

with colA:
    st.markdown("### 📂 Fichier principal")
    main_file = st.file_uploader("Drag-&-drop", type=("csv", "xlsx", "xls"), key="main")

with colB:
    st.markdown("### 📂 Liste clients")
    cli_file = st.file_uploader("Drag-&-drop", type=("csv", "xlsx", "xls"), key="cli")

if main_file:
    df_main = read_any(main_file)
    max_cols = len(df_main.columns)
    st.markdown("#### Sélection des colonnes (1 = première)")
    col_int = st.selectbox("Colonne Réf. interne", range(1, max_cols + 1), index=0)
    col_cli = st.selectbox("Colonne Réf. client", range(1, max_cols + 1),
                           index=1 if max_cols > 1 else 0)
else:
    col_int = col_cli = None

# ───────────────────────── ACTION ─────────────────────────
if st.button("🚀 Générer CPN", disabled=not (main_file and cli_file and col_int and col_cli)):
    try:
        df_main = read_any(main_file)
        df_cli  = read_any(cli_file)
        series_cli = df_cli.iloc[:, 0]            # 1ʳᵉ colonne de la liste clients

        pf, dfrx_name, afrx_name, afrx_txt = cpn_logic(
            df_main, col_cli, col_int, series_cli
        )
    except Exception as e:
        st.error(f"❌ {e}")
        st.stop()

    # Téléchargements
    st.download_button("⬇️ DFRX (TSV)", data=to_tsv_bytes(pf),
                       file_name=dfrx_name, mime="text/tab-separated-values")
    st.download_button("⬇️ AFRX (TXT)", data=afrx_txt,
                       file_name=afrx_name, mime="text/plain")

    st.success("✅ Fichiers générés ! Aperçu du PF :")
    st.dataframe(pf.head(), use_container_width=True)
