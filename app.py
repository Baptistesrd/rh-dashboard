import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# === CONFIG ===
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/12xFNjihxA6EY0yfLpevIrFgqvWY9AwNtsRDJ3608hVI/export?format=csv&gid=0"

# === LOAD & CLEAN DATA ===
@st.cache_data
def load_data():
    df = pd.read_csv(SHEET_CSV_URL, skiprows=4)
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    df['Date d\'arrivée'] = pd.to_datetime(df['Date d\'arrivée'], dayfirst=True, errors='coerce')
    df['Date de fin (si applicable)'] = pd.to_datetime(df['Date de fin (si applicable)'], dayfirst=True, errors='coerce')
    df = df[df['Date d\'arrivée'].notna()]
    df['Année arrivée'] = df['Date d\'arrivée'].dt.year
    df['Mois arrivée'] = df['Date d\'arrivée'].dt.to_period('M')
    df['Année fin'] = df['Date de fin (si applicable)'].dt.year
    df['Mois fin'] = df['Date de fin (si applicable)'].dt.to_period('M')
    df['En poste'] = df['Date de fin (si applicable)'].isna() | (df['Date de fin (si applicable)'] > datetime.today())
    df['Type de sortie'] = df['Date de fin (si applicable)'].notna().map({True: 'Sortie', False: 'Présent'})
    df['Ancienneté'] = ((pd.to_datetime('today') - df['Date d\'arrivée']).dt.days / 365).round(1)
    return df

df = load_data()

def regroup_pole(p):
    if pd.isna(p): return "Autre"
    p = p.lower()
    if "tech" in p: return "Tech"
    if "ops" in p: return "Ops"
    if "codir" in p or "ceo" in p: return "CODIR"
    if "marketing" in p: return "Marketing"
    if "sales" in p or "business" in p: return "Sales"
    if "uk" in p: return "UK"
    if "finance" in p or "rh" in p or "legal" in p or "admin" in p: return "G&A"
    return "Autre"

df["Pôle regroupé"] = df["Pôle associé"].apply(regroup_pole)

# === KPI HELPERS ===
def plot_bar(data, x, y, color=None, barmode='group', title=""):
    fig = px.bar(data, x=x, y=y, color=color, barmode=barmode, title=title)
    st.plotly_chart(fig, use_container_width=True)

def plot_line(data, x, y, color=None, title=""):
    fig = px.line(data, x=x, y=y, color=color, title=title)
    st.plotly_chart(fig, use_container_width=True)

# === DASHBOARD ===
st.set_page_config(page_title="Dashboard RH", layout="wide")

st.title("📊 Dashboard RH")

onglet1, onglet2 = st.tabs(["📅 KPIs par année", "📆 KPIs par mois"])

with onglet1:
    st.header("Effectifs par contrat et par an")
    effectif_annee = df[df['En poste']].groupby(['Année arrivée', 'Type de contrat']).size().reset_index(name="Effectif")
    plot_bar(effectif_annee, x="Année arrivée", y="Effectif", color="Type de contrat")

    st.header("Entrées et sorties par an - par contrat")
    entrees_sorties = pd.concat([
        df.groupby(['Année arrivée', 'Type de contrat']).size().reset_index(name="Nombre").assign(Mouvement="Entrée"),
        df[df['Année fin'].notna()].groupby(['Année fin', 'Type de contrat']).size().reset_index(name="Nombre").assign(Mouvement="Sortie")
    ])
    entrees_sorties = entrees_sorties.rename(columns={"Année arrivée": "Année", "Année fin": "Année"})
    plot_bar(entrees_sorties, x="Année", y="Nombre", color="Mouvement")

    st.header("Turnover par grand pôle par an")
    turnover_data = df[df['Année fin'].notna()].groupby(['Année fin', 'Pôle regroupé']).size().reset_index(name="Départs")
    effectif_moyen = df.groupby(['Année arrivée', 'Pôle regroupé']).size().reset_index(name="Effectif").rename(columns={"Année arrivée": "Année"})
    turnover = pd.merge(turnover_data, effectif_moyen, on=["Année", "Pôle regroupé"], how="left")
    turnover["Turnover %"] = (turnover["Départs"] / turnover["Effectif"] * 100).round(2)
    plot_bar(turnover, x="Année", y="Turnover %", color="Pôle regroupé")

    st.header("Taux de départ CDI par pôle par an")
    taux_cdi = df[(df['Type de contrat'] == 'CDI') & df['Année fin'].notna()]
    taux_cdi = taux_cdi.groupby(['Année fin', 'Pôle regroupé']).size().reset_index(name="Départs CDI")
    plot_bar(taux_cdi, x="Année fin", y="Départs CDI", color="Pôle regroupé")

    st.header("Effectifs CDI moyens par an (hors stagiaires)")
    cdi_actifs = df[(df['Type de contrat'] == 'CDI') & df['En poste']]
    cdi_moyen = cdi_actifs.groupby('Année arrivée').size().reset_index(name="Effectif moyen")
    plot_line(cdi_moyen, x="Année arrivée", y="Effectif moyen")

    st.header("Effectif moyen par an (tous contrats)")
    all_moyen = df[df['En poste']].groupby('Année arrivée').size().reset_index(name="Effectif moyen")
    plot_line(all_moyen, x="Année arrivée", y="Effectif moyen")

    st.header("Turnover total par an")
    total_turnover = df[df['Année fin'].notna()].groupby('Année fin').size().reset_index(name="Départs")
    total_turnover = pd.merge(total_turnover, all_moyen.rename(columns={"Année arrivée": "Année fin"}), on="Année fin", how="left")
    total_turnover["Turnover %"] = (total_turnover["Départs"] / total_turnover["Effectif moyen"] * 100).round(2)
    plot_bar(total_turnover, x="Année fin", y="Turnover %")

    st.header("Taux de départ CDI par type de sortie")
    # TODO: Tu peux rajouter une colonne manuelle dans ton GSheet pour préciser "Volontaire" / "Non volontaire" si tu veux affiner

    st.header("% de ruptures de période d'essai par an")
    ruptures = df[(df['Type de contrat'] == 'CDI') & (df['Ancienneté'] < (8/12)) & df['Année fin'].notna()]
    ruptures = ruptures.groupby('Année fin').size().reset_index(name="Ruptures PE (<8mois)")
    plot_bar(ruptures, x="Année fin", y="Ruptures PE (<8mois)")

with onglet2:
    st.header("Effectifs par contrat et par mois")
    effectif_mois = df[df['En poste']].groupby(['Mois arrivée', 'Type de contrat']).size().reset_index(name="Effectif")
    effectif_mois['Mois arrivée'] = effectif_mois['Mois arrivée'].astype(str)
    plot_line(effectif_mois, x="Mois arrivée", y="Effectif", color="Type de contrat")

    st.header("Entrées et sorties par mois - par contrat")
    entrees_mois = df.groupby(['Mois arrivée', 'Type de contrat']).size().reset_index(name="Nombre").assign(Mouvement="Entrée")
    sorties_mois = df[df['Mois fin'].notna()].groupby(['Mois fin', 'Type de contrat']).size().reset_index(name="Nombre").assign(Mouvement="Sortie")
    entrees_mois = entrees_mois.rename(columns={"Mois arrivée": "Mois"})
    sorties_mois = sorties_mois.rename(columns={"Mois fin": "Mois"})
    mouv_mois = pd.concat([entrees_mois, sorties_mois])
    mouv_mois['Mois'] = mouv_mois['Mois'].astype(str)
    plot_bar(mouv_mois, x="Mois", y="Nombre", color="Mouvement")

    st.header("Suivi mensuel des effectifs par type de contrat")
    suivi = df[df['En poste']].groupby(['Mois arrivée', 'Type de contrat']).size().reset_index(name="Effectif")
    suivi['Mois arrivée'] = suivi['Mois arrivée'].astype(str)
    plot_line(suivi, x="Mois arrivée", y="Effectif", color="Type de contrat")

