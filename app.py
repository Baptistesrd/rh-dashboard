import streamlit as st
import pandas as pd
import plotly.express as px

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/19cHR5fz_TT7j20v8Siq9QAWEd7EDZukvrd7ufZat750/export?format=csv&gid=0"  # ← Remplace TON_ID

@st.cache_data
def load_data():
    return pd.read_csv(SHEET_CSV_URL)

df = load_data()
df["Date d'arrivée"] = pd.to_datetime(df["Date d'arrivée"], dayfirst=True, errors="coerce")
df["Date de fin (si applicable)"] = pd.to_datetime(df["Date de fin (si applicable)"], dayfirst=True, errors="coerce")
df["Ancienneté"] = ((pd.Timestamp.today() - df["Date d'arrivée"]).dt.days / 365).round(1)

st.title("📊 Dashboard RH – Onboarding IT Admin")

col1, col2, col3 = st.columns(3)
col1.metric("Effectif actuel", df["Date de fin (si applicable)"].isna().sum())
col2.metric("CDI", (df["Type de contrat"] == "CDI").sum())
hf_count = df["H/F"].value_counts()
col3.metric("Ratio H/F", f"{hf_count.get('F', 0)} F / {hf_count.get('H', 0)} H")

st.subheader("📆 Ancienneté des CDI")
st.plotly_chart(px.histogram(df[df["Type de contrat"] == "CDI"], x="Ancienneté", nbins=10))

st.subheader("📊 Répartition par Pôle et Contrat")
st.plotly_chart(px.histogram(df, x="Pôle associé", color="Type de contrat", barmode="stack"))

st.subheader("📋 Données brutes")
st.dataframe(df)
