# -*- coding: utf-8 -*-
"""
app.py – Générateur CPN  (DFRXHYBCPNA / AFRXHYBCPNA)
• Déposez :
    1. Un fichier appairage client (Réf. interne + Réf. client).
    2. Un périmètre (comptes client concernés) – une seule colonne.
• Choisissez les colonnes au moyen de menus déroulants (1 = première colonne …).
• Génère :
    – DFRXHYBCPNAyyMMdd0000  (TSV, sans en-tête)
    – AFRXHYBCPNAyyMMdd0000  (acknowledgement TXT)

Sanity‑check ajouté :
    • La colonne « Réf. interne » doit contenir **exclusivement** 8 chiffres (string).
    • Les lignes non conformes sont listées et l'exécution s'arrête.
"""

from __future__ import annotations
from datetime import datetime
from itertools import product
from io import StringIO
import re

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

def validate_internal_codes(series: pd.Series) -> pd.Series:
    """Retourne un masque booléen True si la valeur est invalide (≠ 8 chiffres)."""
    return ~series.str.fullmatch(r"\d{8}")

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
    st.markdown("### 📂 Fichier appairage client")  # libellé renommé
    main_file = st.file_uploader("Drag-&-drop", type=("csv", "xlsx", "xls"), key="main")

with colB:
    st.markdown("### 📂 Périmètre (comptes client concernés)")
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

        # ------- Sanity‑check Réf. interne -------
        series_int = df_main.iloc[:, col_int - 1].astype(str).str.strip()
        invalid_mask = validate_internal_codes(series_int)
        if invalid_mask.any():
            st.error(f"❌ {invalid_mask.sum()} Réf. interne invalide(s) (doivent contenir exactement 8 chiffres).")
            st.dataframe(
                pd.DataFrame({
                    "Ligne": series_int.index[invalid_mask] + 1,
                    "Réf. interne": series_int[invalid_mask]
                }),
                use_container_width=True
            )
            st.stop()

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
