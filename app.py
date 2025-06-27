import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Dashboard RH")

# URLs CSV publiques
SHEET_CSV_URL_ARRIVEES = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=0"
SHEET_CSV_URL_SORTIES = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=859310692"

@st.cache_data
def load_data():
    df_arrivees = pd.read_csv(SHEET_CSV_URL_ARRIVEES, skiprows=4)
    df_sorties = pd.read_csv(SHEET_CSV_URL_SORTIES, skiprows=3)
    return df_arrivees, df_sorties

df, df_sorties = load_data()

df.columns = df.columns.str.strip()
df_sorties.columns = df_sorties.columns.str.strip()

df["Date d'arrivée"] = pd.to_datetime(df["Date d'arrivée"], dayfirst=True, errors="coerce")
df["Date de fin (si applicable)"] = pd.to_datetime(df["Date de fin (si applicable)"], dayfirst=True, errors="coerce")
df_sorties["Date de départ prévue"] = pd.to_datetime(df_sorties["Date de départ prévue"], dayfirst=True, errors="coerce")

df["Année arrivée"] = df["Date d'arrivée"].dt.year
df["Année fin"] = df["Date de fin (si applicable)"].dt.year
df["Mois arrivée"] = df["Date d'arrivée"].dt.to_period("M").astype(str)
df["Mois fin"] = df["Date de fin (si applicable)"].dt.to_period("M").astype(str)
df_sorties["Année fin"] = df_sorties["Date de départ prévue"].dt.year
df_sorties["Mois fin"] = df_sorties["Date de départ prévue"].dt.to_period("M").astype(str)

# Regrouper les pôles
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

# Durée en mois pour détection rupture période d’essai
df["Durée (mois)"] = (df["Date de fin (si applicable)"] - df["Date d'arrivée"]).dt.days / 30

st.title("📊 Dashboard RH — Arrivées & Sorties")

tab1, tab2 = st.tabs(["📈 KPIs annuels", "📆 KPIs mensuels"])

with tab1:
    col1, col2 = st.columns(2)

    # 1. Effectif restant par an (par contrat)
    with col1:
        all_years = sorted(set(df["Année arrivée"].dropna().tolist() + df["Année fin"].dropna().tolist()))
        contrats = df["Type de contrat"].dropna().unique()
        records = []
        for year in all_years:
            for contrat in contrats:
                count = df[
                    (df["Année arrivée"] <= year) &
                    ((df["Année fin"].isna()) | (df["Année fin"] > year)) &
                    (df["Type de contrat"] == contrat)
                ]["Nom"].nunique()
                records.append({"Année": year, "Type de contrat": contrat, "Effectif en poste": count})
        df_effectif = pd.DataFrame(records)
        fig = px.bar(df_effectif, x="Année", y="Effectif en poste", color="Type de contrat", barmode="group", title="Effectif total encore en poste")
        fig.update_traces(marker_line_width=0, width=0.8)
        st.plotly_chart(fig, use_container_width=True)

    # 2. Turnover CDI global par an
    with col2:
        sorties_cdi = df_sorties[
            (df_sorties["Type de contrat"] == "CDI") &
            (df_sorties["Type de départ"].str.lower().str.strip() != "fin de contrat")
        ]
        data = []
        for an in sorted(df["Année arrivée"].dropna().unique()):
            base = df[(df["Type de contrat"] == "CDI") & (df["Année arrivée"] <= an) & ((df["Année fin"].isna()) | (df["Année fin"] > an))]
            sorties = sorties_cdi[sorties_cdi["Année fin"] == an]
            effectif = base["Nom"].nunique()
            nb_sorties = sorties["Nom"].nunique()
            if effectif > 0:
                taux = round(nb_sorties / effectif * 100, 1)
                data.append({"Année": an, "Sorties": nb_sorties, "Effectif CDI": effectif, "Turnover %": taux})
        st.dataframe(pd.DataFrame(data), use_container_width=True)

    # 3. % de ruptures période d’essai
    with col1:
        df_rup = df[(df["Durée (mois)"] < 8) & (df["Durée (mois)"].notna())]
        rupture = df_rup.groupby("Année arrivée")["Nom"].nunique().reset_index(name="Nb ruptures")
        total = df.groupby("Année arrivée")["Nom"].nunique().reset_index(name="Nb entrants")
        merge = pd.merge(rupture, total, on="Année arrivée", how="left")
        merge["% Rupture"] = round(merge["Nb ruptures"] / merge["Nb entrants"] * 100, 1)
        st.dataframe(merge, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)

    # 4. Effectifs par contrat / mois (barres épaisses)
    with col1:
        kpi = df.groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Effectif")
        fig = px.bar(kpi, x="Mois arrivée", y="Effectif", color="Type de contrat", barmode="group", title="Effectifs par contrat et par mois")
        fig.update_traces(marker_line_width=0, width=0.9)
        st.plotly_chart(fig, use_container_width=True)

    # 5. Tableau entrées / sorties par contrat et mois
    with col2:
        entrees = df.groupby(["Mois arrivée", "Type de contrat"]).size().reset_index(name="Entrées")
        sorties = df.groupby(["Mois fin", "Type de contrat"]).size().reset_index(name="Sorties")

        entrees.rename(columns={"Mois arrivée": "Mois"}, inplace=True)
        sorties.rename(columns={"Mois fin": "Mois"}, inplace=True)

        table = pd.merge(entrees, sorties, on=["Mois", "Type de contrat"], how="outer").fillna(0)
        table = table.sort_values("Mois")
        table["Entrées"] = table["Entrées"].astype(int)
        table["Sorties"] = table["Sorties"].astype(int)

        st.dataframe(table, use_container_width=True)
