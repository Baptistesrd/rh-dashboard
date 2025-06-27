import streamlit as st
import pandas as pd
import plotly.express as px

# === LIENS CSV GOOGLE SHEETS ===
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=1581748608"
SHEET_SORTIES_CSV_URL = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=789133425"

# === CHARGEMENT DES DONNÉES ===
@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_CSV_URL, skiprows=4)
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    df["Date d'arrivée"] = pd.to_datetime(df["Date d'arrivée"], dayfirst=True, errors="coerce")
    df["Date de fin (si applicable)"] = pd.to_datetime(df["Date de fin (si applicable)"], dayfirst=True, errors="coerce")
    return df

@st.cache_data
def load_sorties():
    df_sorties = pd.read_csv(SHEET_SORTIES_CSV_URL, skiprows=3)
    df_sorties.columns = df_sorties.columns.str.strip()
    df_sorties = df_sorties.loc[:, ~df_sorties.columns.duplicated()]
    df_sorties["Date de départ prévue"] = pd.to_datetime(df_sorties["Date de départ prévue"], dayfirst=True, errors="coerce")
    return df_sorties

# === LOGIQUE METIER ===
def regroup_pole(pole):
    if pd.isna(pole):
        return "Autres"
    pole = pole.lower()
    if "tech" in pole:
        return "Tech"
    elif "ops" in pole:
        return "Ops"
    elif "g&a" in pole or "finance" in pole or "admin" in pole:
        return "G&A"
    elif "sales" in pole:
        return "Sales"
    elif "marketing" in pole:
        return "Marketing"
    elif "codir" in pole or "comité" in pole:
        return "CODIR"
    elif "uk" in pole:
        return "UK"
    else:
        return "Autres"

def plot_bar(data, x, y, color=None, barmode='group', title=""):
    fig = px.bar(data, x=x, y=y, color=color, barmode=barmode, title=title)
    st.plotly_chart(fig, use_container_width=True)

# === MAIN ===
df = load_data()
df_sorties = load_sorties()

df["Pôle regroupé"] = df["Pôle associé"].apply(regroup_pole)
df["Année arrivée"] = df["Date d'arrivée"].dt.year
df["Année fin"] = df["Date de fin (si applicable)"].dt.year
df["Mois arrivée"] = df["Date d'arrivée"].dt.to_period("M").astype(str)

# === ENTRÉES / SORTIES ===
entrees = df[~df["Date d'arrivée"].isna()].copy()
entrees["Année"] = entrees["Année arrivée"]
entrees["Mouvement"] = "Entrée"

sorties = df[~df["Date de fin (si applicable)"].isna()].copy()
sorties["Année"] = sorties["Année fin"]
sorties["Mouvement"] = "Sortie"

entrees_sorties = pd.concat([
    entrees[["Année", "Mouvement"]],
    sorties[["Année", "Mouvement"]]
])
entrees_sorties = entrees_sorties.value_counts().reset_index(name="Nombre")

# === KPI TURNOVER (onglet "Sorties") ===
df_sorties["Année départ"] = df_sorties["Date de départ prévue"].dt.year
turnover_type = df_sorties.groupby(["Année départ", "Type de départ"]).size().reset_index(name="Nombre")

# === DASHBOARD ===
tab1, tab2 = st.tabs(["Vue annuelle", "Vue mensuelle"])

with tab1:
    st.subheader("📊 Effectifs par contrat et par an")
    effectifs_contrat = df.groupby(["Année arrivée", "Type de contrat"]).size().reset_index(name="Effectif")
    plot_bar(effectifs_contrat, x="Année arrivée", y="Effectif", color="Type de contrat")

    st.subheader("📈 Entrées / Sorties par an")
    plot_bar(entrees_sorties, x="Année", y="Nombre", color="Mouvement")

    st.subheader("📉 Turnover par type de départ (onglet Sorties)")
    plot_bar(turnover_type, x="Année départ", y="Nombre", color="Type de départ")

with tab2:
    st.subheader("📆 Effectifs par contrat et par mois")
    effectifs_mois = df.groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Effectif")
    plot_bar(effectifs_mois, x="Mois arrivée", y="Effectif", color="Type de contrat", barmode="stack", title="Effectifs mensuels")


