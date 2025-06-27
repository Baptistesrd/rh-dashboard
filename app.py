import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dashboard RH")

# URLs CSV publiques
SHEET_CSV_URL_ARRIVEES = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=0"
SHEET_CSV_URL_SORTIES = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=859310692"

# Fonction pour charger les données
@st.cache_data
def load_data():
    df_arrivees = pd.read_csv(SHEET_CSV_URL_ARRIVEES, skiprows=4)
    df_sorties = pd.read_csv(SHEET_CSV_URL_SORTIES, skiprows=3)
    return df_arrivees, df_sorties

df, df_sorties = load_data()

# Nettoyage des colonnes
df.columns = df.columns.str.strip()
df_sorties.columns = df_sorties.columns.str.strip()

# Transformation des dates
df["Date d'arrivée"] = pd.to_datetime(df["Date d'arrivée"], dayfirst=True, errors="coerce")
df["Date de fin (si applicable)"] = pd.to_datetime(df["Date de fin (si applicable)"], dayfirst=True, errors="coerce")
df_sorties["Date de départ prévue"] = pd.to_datetime(df_sorties["Date de départ prévue"], dayfirst=True, errors="coerce")

# Fonction pour regrouper les pôles
def regroup_pole(pole):
    if isinstance(pole, str):
        pole = pole.lower()
        if "tech" in pole: return "Tech"
        elif "ops" in pole: return "Ops"
        elif "g&a" in pole or "ga" in pole: return "G&A"
        elif "sales" in pole: return "Sales"
        elif "market" in pole: return "Marketing"
        elif "codir" in pole: return "CODIR"
        elif "uk" in pole: return "UK"
    return "Autre"

df["Pôle regroupé"] = df["Pôle associé"].apply(regroup_pole)
df["Année arrivée"] = df["Date d'arrivée"].dt.year
df["Mois arrivée"] = df["Date d'arrivée"].dt.to_period("M")
df["Année fin"] = df["Date de fin (si applicable)"].dt.year
df["Mois fin"] = df["Date de fin (si applicable)"].dt.to_period("M")
df_sorties["Année fin"] = df_sorties["Date de départ prévue"].dt.year
df_sorties["Mois fin"] = df_sorties["Date de départ prévue"].dt.to_period("M")

# Fonction d'affichage
def plot_bar(data, x, y, color=None, barmode='group', title=""):
    fig = px.bar(data, x=x, y=y, color=color, barmode=barmode, title=title)
    st.plotly_chart(fig, use_container_width=True)

# ========== INTERFACE ==========
st.title("📊 Dashboard RH — Arrivées & Sorties")

tab1, tab2 = st.tabs(["📈 KPIs annuels", "📉 KPIs mensuels"])

with tab1:
    col1, col2 = st.columns(2)

    # Effectifs par type de contrat / an
    with col1:
        kpi = df.groupby(["Année arrivée", "Type de contrat"]).size().reset_index(name="Effectif")
        plot_bar(kpi, x="Année arrivée", y="Effectif", color="Type de contrat", title="Effectifs par contrat et par an")

    # Entrées et sorties par an
    with col2:
        entrees = df[df["Année arrivée"].notna()].groupby(["Année arrivée", "Type de contrat"]).size().reset_index(name="Nombre")
        entrees["Mouvement"] = "Entrée"
        entrees = entrees.rename(columns={"Année arrivée": "Année"})

        sorties = df[df["Année fin"].notna()].groupby(["Année fin", "Type de contrat"]).size().reset_index(name="Nombre")
        sorties["Mouvement"] = "Sortie"
        sorties = sorties.rename(columns={"Année fin": "Année"})

        entrees_sorties = pd.concat([entrees, sorties])
        plot_bar(entrees_sorties, x="Année", y="Nombre", color="Mouvement", title="Entrées / Sorties par contrat et par an")

    # Turnover par pôle
    with col1:
        base = df[df["Type de contrat"] == "CDI"]
        effectifs_pole = base.groupby(["Année arrivée", "Pôle regroupé"]).size().reset_index(name="Effectif")
        sorties_pole = base[base["Année fin"].notna()].groupby(["Année fin", "Pôle regroupé"]).size().reset_index(name="Départs")
        turnover = pd.merge(effectifs_pole, sorties_pole, left_on=["Année arrivée", "Pôle regroupé"], right_on=["Année fin", "Pôle regroupé"], how="outer").fillna(0)
        turnover["Turnover"] = (turnover["Départs"] / turnover["Effectif"]).round(2)
        plot_bar(turnover, x="Année arrivée", y="Turnover", color="Pôle regroupé", title="Turnover CDI par pôle")

with tab2:
    col1, col2 = st.columns(2)

    # Effectifs par type de contrat / mois
    with col1:
        kpi = df.groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Effectif")
        kpi["Mois arrivée"] = kpi["Mois arrivée"].astype(str)
        plot_bar(kpi, x="Mois arrivée", y="Effectif", color="Type de contrat", title="Effectifs par contrat et par mois")

    # Entrées et sorties par mois
    with col2:
        entrees = df[df["Mois arrivée"].notna()].groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Nombre")
        entrees["Mouvement"] = "Entrée"
        entrees = entrees.rename(columns={"Mois arrivée": "Mois"})

        sorties = df[df["Mois fin"].notna()].groupby(["Mois fin", "Type de contrat"]).size().reset_index(name="Nombre")
        sorties["Mouvement"] = "Sortie"
        sorties = sorties.rename(columns={"Mois fin": "Mois"})

        entrees_sorties = pd.concat([entrees, sorties])
        entrees_sorties["Mois"] = entrees_sorties["Mois"].astype(str)
        plot_bar(entrees_sorties, x="Mois", y="Nombre", color="Mouvement", title="Entrées / Sorties par contrat et par mois")

