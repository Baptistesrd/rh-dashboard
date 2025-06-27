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

# Nettoyage
df.columns = df.columns.str.strip()
df_sorties.columns = df_sorties.columns.str.strip()

df["Date d'arrivée"] = pd.to_datetime(df["Date d'arrivée"], dayfirst=True, errors="coerce")
df["Date de fin (si applicable)"] = pd.to_datetime(df["Date de fin (si applicable)"], dayfirst=True, errors="coerce")
df_sorties["Date de départ prévue"] = pd.to_datetime(df_sorties["Date de départ prévue"], dayfirst=True, errors="coerce")

# Regroupement des pôles
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

    # Turnover CDI global basé sur l'onglet 'Sorties'
    with col1:
        base_cdi = df[df["Type de contrat"] == "CDI"]
        total_cdi = base_cdi["Nom"].nunique()

        sorties_cdi_reelles = df_sorties[
            (df_sorties["Type de contrat"] == "CDI") &
            (df_sorties["Type de départ"].str.strip().str.lower() != "fin de contrat") &
            (df_sorties["Nom"].notna())
        ]
        nb_sorties_cdi = sorties_cdi_reelles["Nom"].nunique()
        turnover_cdi = round(nb_sorties_cdi / total_cdi, 2)

        st.metric("Turnover CDI global", f"{turnover_cdi * 100:.0f}% ({nb_sorties_cdi} départs / {total_cdi} CDI)")

with tab2:
    col1, col2 = st.columns(2)

    # Effectifs par type de contrat / mois
    with col1:
        kpi = df.groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Effectif")
        kpi["Mois arrivée"] = kpi["Mois arrivée"].astype(str)
        plot_bar(kpi, x="Mois arrivée", y="Effectif", color="Type de contrat", title="Effectifs par contrat et par mois")

    # Entrées et sorties mensuelles — tableau
    with col2:
        entrees = df[df["Mois arrivée"].notna()].groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Entrées")
        sorties = df[df["Mois fin"].notna()].groupby(["Mois fin", "Type de contrat"]).size().reset_index(name="Sorties")

        entrees["Mois"] = entrees["Mois arrivée"].astype(str)
        sorties["Mois"] = sorties["Mois fin"].astype(str)

        table = pd.merge(entrees[["Mois", "Type de contrat", "Entrées"]],
                         sorties[["Mois", "Type de contrat", "Sorties"]],
                         on=["Mois", "Type de contrat"],
                         how="outer").fillna(0)

        table = table.sort_values("Mois")
        table["Entrées"] = table["Entrées"].astype(int)
        table["Sorties"] = table["Sorties"].astype(int)

        st.dataframe(table, use_container_width=True)
