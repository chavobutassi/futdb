"""
FUTDB — Dashboard de Análisis de Fútbol
========================================
Archivo principal de la aplicación Streamlit.
Estructura idéntica a ARGO — mismo patrón de imports y layout.

Ejecutar:
    streamlit run app.py
"""

import logging
import warnings
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)

# ─── Import conector ────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv
load_dotenv()

# ── Ligas Argentina ──────────────────────────────────────────────────────────
LIGAS = {
    "CLI": {"nombre": "Liga Profesional", "pais": "Argentina", "temporada": 2024},
    "CAR": {"nombre": "Copa Argentina",   "pais": "Argentina", "temporada": 2024},
    "PNA": {"nombre": "Primera Nacional", "pais": "Argentina", "temporada": 2024},
}

# ── Módulo Plantel ───────────────────────────────────────────────────────────
try:
    from pages.page_plantel import render_plantel
    _PLANTEL_OK = True
except ImportError as _ep:
    _PLANTEL_OK = False
    logging.warning(f"[FUTDB] page_plantel no disponible: {_ep}")

# ── Conector Argentina ───────────────────────────────────────────────────────
try:
    from data.connector_arg import ConectorArg, LIGAS_ARG
    _conector_arg = ConectorArg()
    CONECTOR_ARG_OK = True
    if not _conector_arg.disponible:
        logging.warning("[FUTDB] Sin APISPORTS_KEY — usando datos ejemplo")
except (ImportError, Exception) as _ea:
    CONECTOR_ARG_OK = False
    _conector_arg   = None
    logging.warning(f"[FUTDB] connector_arg no disponible: {_ea}")

# ─── Configuración de página ────────────────────────────────────────────────────

st.set_page_config(
    page_title="FUTDB · Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS deportivo ──────────────────────────────────────────────────────────────
# Paleta: fondo carbón, verde campo como acento, blanco puro para textos,
# dorado para highlights. Tipografía: DM Mono para stats, Barlow Condensed para títulos.

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;500;700;900&family=DM+Mono:wght@300;400;500&family=Barlow:wght@300;400;500&display=swap" rel="stylesheet">

<style>

/* ── Reset y base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

[data-testid="stAppViewContainer"] {
    background: #0d0f0e;
    font-family: 'Barlow', sans-serif;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] {
    background: #111412 !important;
    border-right: 1px solid #1e2420;
}
[data-testid="stSidebar"] > div { padding-top: 1rem; }
.block-container { padding: 1.5rem 2rem 3rem; }

/* ── Sidebar nav ── */
.sidebar-logo {
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 900;
    font-size: 1.6rem;
    color: #fff;
    letter-spacing: .04em;
    padding: .5rem 1rem 1.2rem;
    border-bottom: 1px solid #1e2420;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: .5rem;
}
.sidebar-logo span { color: #4ade80; }

.nav-item {
    display: flex;
    align-items: center;
    gap: .65rem;
    padding: .6rem 1rem;
    border-radius: 8px;
    font-family: 'Barlow', sans-serif;
    font-size: .88rem;
    font-weight: 500;
    color: #6b7a6d;
    cursor: pointer;
    transition: all .15s;
    margin: 2px 8px;
    letter-spacing: .02em;
}
.nav-item:hover { background: #1a1f1c; color: #ccc; }
.nav-item.active { background: #162119; color: #4ade80; border-left: 2px solid #4ade80; }

/* ── Radio buttons → menú ── */
[data-testid="stRadio"] > label { display: none; }
[data-testid="stRadio"] > div {
    gap: 2px !important;
    flex-direction: column !important;
}
[data-testid="stRadio"] > div > label {
    display: flex !important;
    align-items: center !important;
    gap: .65rem !important;
    padding: .6rem 1rem !important;
    border-radius: 8px !important;
    font-family: 'Barlow', sans-serif !important;
    font-size: .88rem !important;
    font-weight: 500 !important;
    color: #6b7a6d !important;
    cursor: pointer !important;
    transition: all .15s !important;
    margin: 2px 8px !important;
    background: transparent !important;
}
[data-testid="stRadio"] > div > label:has(input:checked) {
    background: #162119 !important;
    color: #4ade80 !important;
    border-left: 2px solid #4ade80 !important;
}
[data-testid="stRadio"] > div > label > div:first-child { display: none !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > label {
    color: #6b7a6d !important;
    font-size: .8rem !important;
    font-family: 'DM Mono', monospace !important;
    letter-spacing: .05em !important;
    text-transform: uppercase !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #111412 !important;
    border: 1px solid #1e2420 !important;
    color: #e2e8df !important;
    font-family: 'Barlow', sans-serif !important;
}

/* ── Métricas / KPI cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 12px;
    margin: 1rem 0 1.8rem;
}
.kpi-card {
    background: #111412;
    border: 1px solid #1e2420;
    border-radius: 12px;
    padding: 1.1rem 1.2rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #4ade80, transparent);
}
.kpi-label {
    font-family: 'DM Mono', monospace;
    font-size: .68rem;
    color: #4b5a4d;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: .4rem;
}
.kpi-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #fff;
    line-height: 1;
}
.kpi-sub {
    font-family: 'Barlow', sans-serif;
    font-size: .75rem;
    color: #4b5a4d;
    margin-top: .3rem;
}
.kpi-card.gold::before { background: linear-gradient(90deg, #f59e0b, transparent); }
.kpi-card.coral::before { background: linear-gradient(90deg, #f87171, transparent); }
.kpi-card.blue::before { background: linear-gradient(90deg, #60a5fa, transparent); }

/* ── Section header ── */
.section-header {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    margin: 2rem 0 1rem;
    padding-bottom: .6rem;
    border-bottom: 1px solid #1e2420;
}
.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #e2e8df;
    letter-spacing: .04em;
    text-transform: uppercase;
}
.section-sub {
    font-family: 'DM Mono', monospace;
    font-size: .72rem;
    color: #4b5a4d;
    letter-spacing: .06em;
}

/* ── Tablas ── */
.futdb-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Barlow', sans-serif;
    font-size: .88rem;
    color: #cdd5ca;
}
.futdb-table thead tr {
    background: #0d0f0e;
    border-bottom: 1px solid #1e2420;
}
.futdb-table thead th {
    padding: .6rem .9rem;
    text-align: left;
    font-family: 'DM Mono', monospace;
    font-size: .68rem;
    font-weight: 400;
    color: #4b5a4d;
    text-transform: uppercase;
    letter-spacing: .08em;
}
.futdb-table thead th.num { text-align: right; }
.futdb-table tbody tr {
    border-bottom: 1px solid #141714;
    transition: background .1s;
}
.futdb-table tbody tr:hover { background: #141714; }
.futdb-table tbody td {
    padding: .65rem .9rem;
    vertical-align: middle;
}
.futdb-table tbody td.num {
    text-align: right;
    font-family: 'DM Mono', monospace;
    font-size: .82rem;
}
.futdb-table tbody td.highlight {
    font-weight: 500;
    color: #e2e8df;
}
.rank-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px; height: 24px;
    border-radius: 6px;
    font-family: 'DM Mono', monospace;
    font-size: .78rem;
    font-weight: 500;
    background: #1a1f1c;
    color: #6b7a6d;
}
.rank-badge.top1 { background: #3d2e00; color: #f59e0b; }
.rank-badge.top2 { background: #1a2330; color: #60a5fa; }
.rank-badge.top3 { background: #2a1a12; color: #f87171; }
.forma-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin: 0 1px;
}
.forma-dot.W { background: #4ade80; }
.forma-dot.D { background: #f59e0b; }
.forma-dot.L { background: #f87171; }

/* ── Tabla wrapper ── */
.table-card {
    background: #111412;
    border: 1px solid #1e2420;
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 1.5rem;
}
.table-card-header {
    padding: .8rem 1rem;
    border-bottom: 1px solid #1a1f1c;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    color: #4b5a4d;
    letter-spacing: .06em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.table-card-header .tag {
    font-family: 'DM Mono', monospace;
    font-size: .65rem;
    padding: .2rem .5rem;
    background: #1e2420;
    border-radius: 4px;
    color: #4b5a4d;
}

/* ── Estadio cards ── */
.stadium-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
    margin-top: 1rem;
}
.stadium-card {
    background: #111412;
    border: 1px solid #1e2420;
    border-radius: 12px;
    overflow: hidden;
    transition: border-color .2s;
}
.stadium-card:hover { border-color: #2e3a30; }
.stadium-img {
    width: 100%; height: 130px;
    object-fit: cover;
    filter: grayscale(40%) brightness(.85);
    display: block;
}
.stadium-img-placeholder {
    width: 100%; height: 130px;
    background: linear-gradient(135deg, #141a14 0%, #0d100d 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.5rem;
}
.stadium-body { padding: .9rem 1rem 1rem; }
.stadium-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.05rem;
    font-weight: 700;
    color: #e2e8df;
    margin-bottom: .2rem;
}
.stadium-club {
    font-family: 'DM Mono', monospace;
    font-size: .7rem;
    color: #4b5a4d;
    margin-bottom: .6rem;
}
.stadium-stats {
    display: flex;
    gap: 1rem;
}
.stadium-stat { flex: 1; }
.stadium-stat .val {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #4ade80;
}
.stadium-stat .lbl {
    font-family: 'DM Mono', monospace;
    font-size: .62rem;
    color: #4b5a4d;
    text-transform: uppercase;
}

/* ── Nutrición cards ── */
.nutri-card {
    background: #111412;
    border: 1px solid #1e2420;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    margin-bottom: 10px;
}
.nutri-position {
    font-family: 'DM Mono', monospace;
    font-size: .68rem;
    color: #4ade80;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin-bottom: .3rem;
}
.nutri-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e2e8df;
    margin-bottom: .5rem;
}
.nutri-macros {
    display: flex;
    gap: .6rem;
    margin: .6rem 0;
    flex-wrap: wrap;
}
.macro-pill {
    padding: .2rem .65rem;
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: .7rem;
    font-weight: 500;
}
.macro-pill.carbs { background: #2a2200; color: #f59e0b; }
.macro-pill.prot  { background: #162119; color: #4ade80; }
.macro-pill.fat   { background: #1a1f30; color: #60a5fa; }
.macro-pill.cal   { background: #2a1a1a; color: #f87171; }
.nutri-detail {
    font-family: 'Barlow', sans-serif;
    font-size: .82rem;
    color: #6b7a6d;
    line-height: 1.5;
}

/* ── Señal/alerta ── */
.signal-card {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
    background: #111412;
    border: 1px solid #1e2420;
    border-radius: 10px;
    padding: .9rem 1rem;
    margin-bottom: 8px;
}
.signal-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-top: .35rem;
    flex-shrink: 0;
}
.signal-title {
    font-family: 'Barlow', sans-serif;
    font-weight: 500;
    font-size: .88rem;
    color: #e2e8df;
    margin-bottom: .2rem;
}
.signal-detail {
    font-family: 'DM Mono', monospace;
    font-size: .72rem;
    color: #4b5a4d;
}

/* ── Plotly override ── */
.js-plotly-plot .plotly { background: transparent !important; }

/* ── Streamlit overrides ── */
[data-testid="stMetric"] { display: none; }
div[data-testid="column"] > div > div > div { gap: 0 !important; }
.stSpinner > div { border-top-color: #4ade80 !important; }
hr { border-color: #1e2420 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Datos estáticos de respaldo ────────────────────────────────────────────────

ESTADIOS = [
    {"nombre": "Camp Nou",            "club": "Barcelona",          "liga": "LaLiga",        "capacidad": 99_354, "año": 1957, "pais": "🇪🇸", "emoji": "🏟"},
    {"nombre": "Wembley Stadium",     "club": "Selección Inglaterra","liga": "Internacional", "capacidad": 90_000, "año": 2007, "pais": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "emoji": "🏟"},
    {"nombre": "Estadio Azteca",      "club": "Selección México",   "liga": "MX",            "capacidad": 87_523, "año": 1966, "pais": "🇲🇽", "emoji": "🏟"},
    {"nombre": "Signal Iduna Park",   "club": "Borussia Dortmund",  "liga": "Bundesliga",    "capacidad": 81_365, "año": 1974, "pais": "🇩🇪", "emoji": "🏟"},
    {"nombre": "Santiago Bernabéu",   "club": "Real Madrid",        "liga": "LaLiga",        "capacidad": 81_044, "año": 1947, "pais": "🇪🇸", "emoji": "🏟"},
    {"nombre": "Old Trafford",        "club": "Manchester United",  "liga": "Premier League","capacidad": 74_140, "año": 1910, "pais": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "emoji": "🏟"},
    {"nombre": "Monumental",          "club": "River Plate",        "liga": "Liga Prof. ARG","capacidad": 84_567, "año": 1938, "pais": "🇦🇷", "emoji": "🏟"},
    {"nombre": "La Bombonera",        "club": "Boca Juniors",       "liga": "Liga Prof. ARG","capacidad": 54_000, "año": 1940, "pais": "🇦🇷", "emoji": "🏟"},
    {"nombre": "San Siro",            "club": "Milan / Inter",      "liga": "Serie A",       "capacidad": 75_817, "año": 1926, "pais": "🇮🇹", "emoji": "🏟"},
    {"nombre": "Allianz Arena",       "club": "Bayern Munich",      "liga": "Bundesliga",    "capacidad": 75_024, "año": 2005, "pais": "🇩🇪", "emoji": "🏟"},
    {"nombre": "Anfield",             "club": "Liverpool",          "liga": "Premier League","capacidad": 61_276, "año": 1884, "pais": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "emoji": "🏟"},
    {"nombre": "Maracanã",            "club": "Selección Brasil",   "liga": "Brasileirão",   "capacidad": 78_838, "año": 1950, "pais": "🇧🇷", "emoji": "🏟"},
]

NUTRICION = [
    {
        "posicion": "Delantero",
        "titulo": "Alta demanda explosiva",
        "calorias": "3.400–3.800 kcal",
        "calorias_val": 3600,
        "carbs": "55–60%",
        "proteinas": "20–25%",
        "grasas": "15–20%",
        "detalle": "Alta carga de carbohidratos para sprints repetidos. Énfasis en recuperación post-partido con proteína de rápida absorción (suero). Hidratación: 6–8 L/día en semana de partido.",
        "alimentos_clave": "Arroz integral · Pasta · Pollo · Huevo · Plátano · Avena",
    },
    {
        "posicion": "Mediocampista",
        "titulo": "Resistencia + agilidad cognitiva",
        "calorias": "3.200–3.600 kcal",
        "calorias_val": 3400,
        "carbs": "50–55%",
        "proteinas": "22–26%",
        "grasas": "18–22%",
        "detalle": "Los volantes recorren hasta 12–14 km por partido. Suplementación con creatina monohidratada en pretemporada. Omega-3 para recuperación muscular y función cognitiva.",
        "alimentos_clave": "Quinoa · Salmón · Legumbres · Frutos secos · Arándanos",
    },
    {
        "posicion": "Defensor",
        "titulo": "Potencia + recuperación ósea",
        "calorias": "3.100–3.500 kcal",
        "calorias_val": 3300,
        "carbs": "45–50%",
        "proteinas": "25–28%",
        "grasas": "20–25%",
        "detalle": "Mayor masa muscular requiere más proteína. Calcio y vitamina D para proteger articulaciones expuestas a duelos físicos. Énfasis en anti-inflamatorios naturales.",
        "alimentos_clave": "Carne magra · Lácteos · Brócoli · Huevos · Cúrcuma · Boniato",
    },
    {
        "posicion": "Arquero",
        "titulo": "Reacción + concentración sostenida",
        "calorias": "2.800–3.200 kcal",
        "calorias_val": 3000,
        "carbs": "40–45%",
        "proteinas": "25–28%",
        "grasas": "25–30%",
        "detalle": "Menor volumen aeróbico, mayor trabajo explosivo en el arco. Énfasis en grasas saludables para función nerviosa y reacción. Suplementación de magnesio para reducir calambres en situaciones de alta tensión.",
        "alimentos_clave": "Aguacate · Nueces · Sardinas · Batata · Cacao puro · Lentejas",
    },
]

# Datos de ejemplo para cuando el conector no está disponible
def _tabla_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"#": 1, "Club": "Manchester City",    "PJ": 32, "G": 22, "E": 6, "P": 4, "GF": 71, "GC": 31, "DG": "+40", "Pts": 72, "Forma": "WGWWW"},
        {"#": 2, "Club": "Arsenal",            "PJ": 32, "G": 21, "E": 5, "P": 6, "GF": 69, "GC": 28, "DG": "+41", "Pts": 68, "Forma": "WWDWW"},
        {"#": 3, "Club": "Liverpool",          "PJ": 32, "G": 20, "E": 7, "P": 5, "GF": 75, "GC": 38, "DG": "+37", "Pts": 67, "Forma": "WDWWL"},
        {"#": 4, "Club": "Aston Villa",        "PJ": 32, "G": 18, "E": 5, "P": 9, "GF": 68, "GC": 48, "DG": "+20", "Pts": 59, "Forma": "LWWDW"},
        {"#": 5, "Club": "Tottenham",          "PJ": 32, "G": 15, "E": 6, "P": 11,"GF": 60, "GC": 55, "DG": "+5",  "Pts": 51, "Forma": "WLWLW"},
        {"#": 6, "Club": "Chelsea",            "PJ": 32, "G": 13, "E": 9, "P": 10,"GF": 57, "GC": 53, "DG": "+4",  "Pts": 48, "Forma": "DWWLD"},
        {"#": 7, "Club": "Newcastle",          "PJ": 32, "G": 13, "E": 8, "P": 11,"GF": 55, "GC": 47, "DG": "+8",  "Pts": 47, "Forma": "LWDWW"},
        {"#": 8, "Club": "Manchester United",  "PJ": 32, "G": 12, "E": 4, "P": 16,"GF": 32, "GC": 52, "DG": "-20", "Pts": 40, "Forma": "LLWLL"},
        {"#": 9, "Club": "West Ham",           "PJ": 32, "G": 12, "E": 3, "P": 17,"GF": 48, "GC": 63, "DG": "-15", "Pts": 39, "Forma": "WLLWL"},
        {"#": 10,"Club": "Brighton",           "PJ": 32, "G": 11, "E": 6, "P": 15,"GF": 52, "GC": 60, "DG": "-8",  "Pts": 39, "Forma": "DLWDW"},
    ])

def _top_goleadores_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"#": 1, "Jugador": "Erling Haaland",   "Club": "Man City",  "Liga": "Premier League", "Goles": 27, "Partidos": 28, "xG": 24.3, "G/90": 0.87},
        {"#": 2, "Jugador": "Cole Palmer",       "Club": "Chelsea",   "Liga": "Premier League", "Goles": 20, "Partidos": 32, "xG": 16.1, "G/90": 0.56},
        {"#": 3, "Jugador": "Mohamed Salah",     "Club": "Liverpool", "Liga": "Premier League", "Goles": 19, "Partidos": 30, "xG": 17.8, "G/90": 0.57},
        {"#": 4, "Jugador": "Kylian Mbappé",     "Club": "Real Madrid","Liga": "LaLiga",        "Goles": 24, "Partidos": 31, "xG": 19.2, "G/90": 0.70},
        {"#": 5, "Jugador": "Robert Lewandowski","Club": "Barcelona",  "Liga": "LaLiga",        "Goles": 18, "Partidos": 29, "xG": 15.9, "G/90": 0.56},
        {"#": 6, "Jugador": "Lautaro Martínez",  "Club": "Inter",     "Liga": "Serie A",        "Goles": 21, "Partidos": 30, "xG": 18.4, "G/90": 0.63},
        {"#": 7, "Jugador": "Harry Kane",        "Club": "Bayern",    "Liga": "Bundesliga",     "Goles": 29, "Partidos": 31, "xG": 25.1, "G/90": 0.84},
        {"#": 8, "Jugador": "Mateo Retegui",     "Club": "Atalanta",  "Liga": "Serie A",        "Goles": 19, "Partidos": 30, "xG": 16.3, "G/90": 0.57},
        {"#": 9, "Jugador": "Jonathan David",    "Club": "Lille",     "Liga": "Ligue 1",         "Goles": 22, "Partidos": 30, "xG": 17.5, "G/90": 0.66},
        {"#": 10,"Jugador": "Alexander Isak",    "Club": "Newcastle", "Liga": "Premier League", "Goles": 17, "Partidos": 27, "xG": 15.2, "G/90": 0.57},
    ])

def _transferencias_ejemplo() -> pd.DataFrame:
    return pd.DataFrame([
        {"Jugador": "Jude Bellingham",    "Origen": "Dortmund",   "Destino": "Real Madrid",   "€ M": 103, "Tipo": "Traspaso",  "Temp.": "23/24"},
        {"Jugador": "Enzo Fernández",     "Origen": "Benfica",    "Destino": "Chelsea",        "€ M": 121, "Tipo": "Traspaso",  "Temp.": "22/23"},
        {"Jugador": "Moises Caicedo",     "Origen": "Brighton",   "Destino": "Chelsea",        "€ M": 116, "Tipo": "Traspaso",  "Temp.": "23/24"},
        {"Jugador": "Valentín Carboni",   "Origen": "Inter",      "Destino": "Marseille",      "€ M":  36, "Tipo": "Traspaso",  "Temp.": "24/25"},
        {"Jugador": "Alexis Mac Allister","Origen": "Brighton",   "Destino": "Liverpool",      "€ M":  35, "Tipo": "Traspaso",  "Temp.": "23/24"},
        {"Jugador": "Facundo Colidio",    "Origen": "Tigre",      "Destino": "Boca Juniors",   "€ M":   2, "Tipo": "Traspaso",  "Temp.": "24/25"},
        {"Jugador": "Nicolás González",   "Origen": "Fiorentina", "Destino": "Juventus",       "€ M":  30, "Tipo": "Traspaso",  "Temp.": "24/25"},
        {"Jugador": "Rodrigo De Paul",    "Origen": "Atlético",   "Destino": "Atlético",       "€ M":   0, "Tipo": "Renovación","Temp.": "24/25"},
    ])

# ─── Helpers de renderizado ──────────────────────────────────────────────────────

def render_forma(forma: str) -> str:
    """Convierte string de forma (ej: 'WWDLW') en puntos de color HTML."""
    html = ""
    for c in str(forma)[:5]:
        css = {"W": "W", "G": "W", "D": "D", "E": "D", "L": "L", "P": "L"}.get(c, "D")
        html += f'<span class="forma-dot {css}"></span>'
    return html

def rank_badge(pos: int) -> str:
    cls = {1: "top1", 2: "top2", 3: "top3"}.get(pos, "")
    return f'<span class="rank-badge {cls}">{pos}</span>'

def render_kpis(datos: dict):
    cards_html = '<div class="kpi-grid">'
    for item in datos:
        tipo = item.get("tipo", "")
        cards_html += f"""
        <div class="kpi-card {tipo}">
            <div class="kpi-label">{item['label']}</div>
            <div class="kpi-value">{item['value']}</div>
            <div class="kpi-sub">{item.get('sub', '')}</div>
        </div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

def section(titulo: str, sub: str = ""):
    sub_html = f'<span class="section-sub">— {sub}</span>' if sub else ""
    st.markdown(f"""
    <div class="section-header">
        <span class="section-title">{titulo}</span>
        {sub_html}
    </div>""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        ⚽ FUT<span>DB</span>
    </div>
    """, unsafe_allow_html=True)

    pagina = st.radio(
        "Navegación",
        options=[
            "🏠  Dashboard",
            "📊  Posiciones",
            "⚽  Top Jugadores",
            "🔄  Transferencias",
            "🏟  Estadios",
            "🥗  Nutrición",
            "📋  Plantel",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    liga_sel = st.selectbox(
        "Competición",
        options=list(LIGAS.keys()),
        format_func=lambda x: LIGAS[x]["nombre"],
        index=0,
    )

    temporada_sel = st.selectbox(
        "Temporada",
        options=["2026", "2025", "2024"],
        index=0,
    )

    st.markdown("""
    <div style="margin-top:auto;padding:1.2rem 0 0;border-top:1px solid #1e2420;
                font-family:'DM Mono',monospace;font-size:.65rem;color:#2e3a30;margin-top:2rem">
        FUTDB · Analytics v2.0<br>
        Fútbol Argentino · api-sports.io<br>
        Supabase · Plantel en vivo
    </div>""", unsafe_allow_html=True)

# ─── Páginas ─────────────────────────────────────────────────────────────────────

# ── 1. DASHBOARD ──────────────────────────────────────────────────────────────
if pagina.startswith("🏠"):
    st.markdown("""
    <div style="margin-bottom:1.5rem">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:2.2rem;
                    font-weight:900;color:#fff;letter-spacing:.02em;line-height:1.1">
            Fútbol <span style="color:#4ade80">Argentino</span>
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:.75rem;
                    color:#4b5a4d;margin-top:.4rem;letter-spacing:.05em">
            Liga Profesional · Temporada 2024
        </div>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Cargando datos..."):
        df_tabla = _conector_arg.tabla_posiciones("CLI") if CONECTOR_ARG_OK and _conector_arg else None
        df_goles = _conector_arg.top_goleadores("CLI")  if CONECTOR_ARG_OK and _conector_arg else None
        df_res   = _conector_arg.resultados_recientes("CLI", 5) if CONECTOR_ARG_OK and _conector_arg else None

    lider     = df_tabla.iloc[0]["Club"] if df_tabla is not None and not df_tabla.empty else "—"
    lider_pts = df_tabla.iloc[0]["Pts"]  if df_tabla is not None and not df_tabla.empty else "—"
    tot_goles = int(df_tabla["GF"].sum()) if df_tabla is not None and not df_tabla.empty else "—"
    equipos   = len(df_tabla) if df_tabla is not None else "—"
    top_gol   = df_goles.iloc[0]["Jugador"] if df_goles is not None and not df_goles.empty else "—"
    top_cant  = df_goles.iloc[0]["Goles"]   if df_goles is not None and not df_goles.empty else "—"

    render_kpis([
        {"label": "Líder",           "value": lider,          "sub": f"{lider_pts} puntos",          "tipo": "gold"},
        {"label": "Goles temporada", "value": str(tot_goles), "sub": "Liga Profesional 2024",        "tipo": "coral"},
        {"label": "Equipos",         "value": str(equipos),   "sub": "en competencia",               "tipo": ""},
        {"label": "Top goleador",    "value": top_gol,        "sub": f"{top_cant} goles",            "tipo": ""},
    ])

    col1, col2 = st.columns([3, 2])

    with col1:
        section("Top 5 Goleadores", "Liga Profesional Argentina 2024")
        if df_goles is not None and not df_goles.empty:
            rows_html = ""
            for _, r in df_goles.head(5).iterrows():
                rows_html += f"""
                <tr>
                    <td>{rank_badge(int(r['#']))}</td>
                    <td class="highlight">{r['Jugador']}</td>
                    <td style="color:#4b5a4d;font-size:.8rem">{r['Club']}</td>
                    <td class="num" style="color:#4ade80;font-weight:600;font-size:1rem">{r['Goles']}</td>
                    <td class="num">{r['G/90']}</td>
                </tr>"""
            st.markdown(f"""
            <div class="table-card">
                <div class="table-card-header">Goleadores <span class="tag">2024</span></div>
                <table class="futdb-table">
                    <thead><tr>
                        <th>#</th><th>Jugador</th><th>Club</th>
                        <th class="num">Goles</th><th class="num">G/90</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>""", unsafe_allow_html=True)

    with col2:
        section("Últimos resultados", "Liga Profesional")
        if df_res is not None and not df_res.empty:
            for _, r in df_res.iterrows():
                st.markdown(f"""
                <div class="signal-card">
                    <div class="signal-dot" style="background:#4ade80"></div>
                    <div>
                        <div class="signal-title">{r.get('Local','—')} {r.get('Resultado','—')} {r.get('Visitante','—')}</div>
                        <div class="signal-detail">{r.get('Jornada','—')} · {r.get('Fecha','—')}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

    if df_tabla is not None and not df_tabla.empty:
        section("Distribución de puntos", "todos los equipos")
        df_pts = df_tabla.sort_values("Pts", ascending=True)
        fig = px.bar(df_pts, y="Club", x="Pts", orientation="h",
                     color="Pts", color_continuous_scale=["#1e2420","#4ade80"],
                     text="Pts")
        fig.update_traces(marker_line_width=0, textposition="outside",
                          textfont=dict(family="DM Mono", size=9, color="#4b5a4d"))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111412",
            height=max(320, len(df_pts)*24),
            coloraxis_showscale=False,
            margin=dict(l=10, r=40, t=10, b=10),
            xaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=9, color="#4b5a4d")),
            yaxis=dict(tickfont=dict(family="DM Mono", size=9, color="#6b7a6d"), title=None),
        )
        st.plotly_chart(fig, use_container_width=True)


# ── 2. POSICIONES ──────────────────────────────────────────────────────────────
elif pagina.startswith("📊"):
    liga_info = LIGAS.get(liga_sel, LIGAS["CLI"])
    st.markdown(f"""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                font-weight:900;color:#fff;margin-bottom:1.5rem">
        <span style="color:#4ade80">{liga_info['nombre']}</span>
        <span style="font-size:1rem;color:#4b5a4d;font-weight:300"> · {temporada_sel}</span>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Cargando tabla de posiciones..."):
        df_pos = _conector_arg.tabla_posiciones(liga_sel) if CONECTOR_ARG_OK and _conector_arg else pd.DataFrame()

    if df_pos.empty:
        st.caption("📡 Sin datos disponibles para esta competición")
    else:
        fuente = "api-sports.io (en vivo)" if CONECTOR_ARG_OK and _conector_arg and _conector_arg.disponible else "datos ejemplo"
        st.caption(f"✅ {fuente} · {liga_info['nombre']} · Temporada {temporada_sel}")

    render_kpis([
        {"label": "Líder",         "value": str(df_pos.iloc[0]["Club"]) if not df_pos.empty else "—", "sub": f"{df_pos.iloc[0]['Pts'] if not df_pos.empty else '—'} pts", "tipo": "gold"},
        {"label": "Goles totales", "value": str(int(df_pos["GF"].sum())) if not df_pos.empty else "—", "sub": "en la temporada", "tipo": "coral"},
        {"label": "Promedio pts",  "value": f"{df_pos['Pts'].mean():.1f}" if not df_pos.empty else "—", "sub": "por equipo", "tipo": ""},
        {"label": "Equipos",       "value": str(len(df_pos)), "sub": "en competencia", "tipo": ""},
    ])

    rows_html = ""
    for i, r in df_pos.iterrows():
        pos   = r.get("#", i+1)
        club  = r.get("Club","—")
        pts   = r.get("Pts","—")
        pj    = r.get("PJ","—")
        g     = r.get("G","—")
        e     = r.get("E","—")
        p     = r.get("P","—")
        gf    = r.get("GF","—")
        gc    = r.get("GC","—")
        dg    = r.get("DG","—")
        forma = r.get("Forma","")
        zona_color = ""
        if   pos <= 4:              zona_color = "border-left:2px solid #60a5fa"
        elif pos <= 6:              zona_color = "border-left:2px solid #4ade80"
        elif pos >= len(df_pos)-2:  zona_color = "border-left:2px solid #f87171"
        rows_html += f"""
        <tr style="{zona_color}">
            <td>{rank_badge(int(pos))}</td>
            <td class="highlight">{club}</td>
            <td class="num">{pj}</td>
            <td class="num" style="color:#4ade80">{g}</td>
            <td class="num">{e}</td>
            <td class="num" style="color:#f87171">{p}</td>
            <td class="num">{gf}</td>
            <td class="num">{gc}</td>
            <td class="num">{dg}</td>
            <td class="num" style="color:#fff;font-weight:600">{pts}</td>
            <td>{render_forma(str(forma))}</td>
        </tr>"""

    st.markdown(f"""
    <div class="table-card">
        <div class="table-card-header">Tabla de posiciones <span class="tag">{temporada_sel}</span></div>
        <table class="futdb-table">
            <thead><tr>
                <th>#</th><th>Club</th><th class="num">PJ</th>
                <th class="num">G</th><th class="num">E</th><th class="num">P</th>
                <th class="num">GF</th><th class="num">GC</th><th class="num">DG</th>
                <th class="num">Pts</th><th>Forma</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:.65rem;color:#2e3a30;margin-top:.5rem">
        🔵 Copa Libertadores &nbsp;|&nbsp; 🟢 Copa Sudamericana &nbsp;|&nbsp; 🔴 Descenso
    </div>""", unsafe_allow_html=True)

    if not df_pos.empty:
        section("Goles a favor vs Goles en contra", "comparativa de equipos")
        fig2 = px.scatter(df_pos, x="GC", y="GF", text="Club", size="Pts",
                          color="Pts", color_continuous_scale=["#1e2420","#4ade80"],
                          size_max=30)
        fig2.update_traces(textposition="top center",
                           textfont=dict(family="DM Mono", size=8, color="#6b7a6d"),
                           marker_line_width=0)
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111412",
            height=320, coloraxis_showscale=False,
            margin=dict(l=10, r=10, t=20, b=20),
            xaxis=dict(title="Goles en contra", gridcolor="#1a1f1c",
                       tickfont=dict(family="DM Mono", size=9, color="#4b5a4d")),
            yaxis=dict(title="Goles a favor", gridcolor="#1a1f1c",
                       tickfont=dict(family="DM Mono", size=9, color="#4b5a4d")),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ── 3. TOP JUGADORES ──────────────────────────────────────────────────────────
elif pagina.startswith("⚽"):
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                font-weight:900;color:#fff;margin-bottom:1.5rem">
        Top <span style="color:#4ade80">Jugadores</span>
        <span style="font-size:1rem;color:#4b5a4d;font-weight:300"> · Liga Profesional Argentina 2024</span>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Cargando estadísticas..."):
        df_g = _conector_arg.top_goleadores("CLI")    if CONECTOR_ARG_OK and _conector_arg else pd.DataFrame()
        df_a = _conector_arg.top_asistidores("CLI")   if CONECTOR_ARG_OK and _conector_arg else pd.DataFrame()
        df_prox = _conector_arg.proximos_partidos("CLI", 8) if CONECTOR_ARG_OK and _conector_arg else pd.DataFrame()

    tab1, tab2, tab3 = st.tabs(["⚽ Goleadores", "🎯 Asistidores", "📅 Próximos partidos"])

    with tab1:
        if not df_g.empty:
            rows_html = ""
            for _, r in df_g.iterrows():
                rows_html += f"""
                <tr>
                    <td>{rank_badge(int(r['#']))}</td>
                    <td class="highlight">{r['Jugador']}</td>
                    <td style="color:#4b5a4d;font-size:.8rem">{r['Club']}</td>
                    <td class="num">{r['Nac.']}</td>
                    <td class="num" style="color:#4ade80;font-weight:600;font-size:1rem">{r['Goles']}</td>
                    <td class="num">{r['Asist.']}</td>
                    <td class="num">{r['PJ']}</td>
                    <td class="num" style="color:#f59e0b">{r['G/90']}</td>
                </tr>"""
            st.markdown(f"""
            <div class="table-card">
                <div class="table-card-header">Goleadores <span class="tag">Liga Profesional 2024</span></div>
                <table class="futdb-table">
                    <thead><tr>
                        <th>#</th><th>Jugador</th><th>Club</th><th>Nac.</th>
                        <th class="num">Goles</th><th class="num">Asist.</th>
                        <th class="num">PJ</th><th class="num">G/90</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>""", unsafe_allow_html=True)

            section("Goles por jugador", "top 10")
            df_g10 = df_g.head(10).sort_values("Goles")
            fig3 = px.bar(df_g10, y="Jugador", x="Goles", orientation="h",
                          color="Goles", color_continuous_scale=["#1e2420","#4ade80"],
                          text="Goles")
            fig3.update_traces(marker_line_width=0, textposition="outside",
                               textfont=dict(family="DM Mono", size=9, color="#4b5a4d"))
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111412",
                height=320, coloraxis_showscale=False,
                margin=dict(l=10, r=40, t=10, b=10),
                xaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=9, color="#4b5a4d")),
                yaxis=dict(tickfont=dict(family="DM Mono", size=9, color="#6b7a6d"), title=None),
            )
            st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        if not df_a.empty:
            rows_html = ""
            for _, r in df_a.iterrows():
                rows_html += f"""
                <tr>
                    <td>{rank_badge(int(r['#']))}</td>
                    <td class="highlight">{r['Jugador']}</td>
                    <td style="color:#4b5a4d;font-size:.8rem">{r['Club']}</td>
                    <td class="num">{r['Nac.']}</td>
                    <td class="num" style="color:#60a5fa;font-weight:600;font-size:1rem">{r['Asist.']}</td>
                    <td class="num">{r['Goles']}</td>
                    <td class="num">{r['PJ']}</td>
                </tr>"""
            st.markdown(f"""
            <div class="table-card">
                <div class="table-card-header">Asistidores <span class="tag">Liga Profesional 2024</span></div>
                <table class="futdb-table">
                    <thead><tr>
                        <th>#</th><th>Jugador</th><th>Club</th><th>Nac.</th>
                        <th class="num">Asist.</th><th class="num">Goles</th><th class="num">PJ</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>""", unsafe_allow_html=True)

    with tab3:
        if not df_prox.empty:
            rows_html = ""
            for _, r in df_prox.iterrows():
                rows_html += f"""
                <tr>
                    <td style="color:#4b5a4d;font-family:'DM Mono',monospace;font-size:.75rem">{r.get('Fecha','—')}</td>
                    <td style="color:#f59e0b;font-family:'DM Mono',monospace;font-size:.75rem">{r.get('Hora','—')}</td>
                    <td style="color:#4b5a4d;font-size:.75rem">{r.get('Jornada','—')}</td>
                    <td class="highlight" style="text-align:right">{r.get('Local','—')}</td>
                    <td style="color:#4b5a4d;text-align:center;font-size:.8rem">vs</td>
                    <td class="highlight">{r.get('Visitante','—')}</td>
                    <td style="color:#4b5a4d;font-size:.75rem">{r.get('Estadio','—')}</td>
                </tr>"""
            st.markdown(f"""
            <div class="table-card">
                <div class="table-card-header">Próximos partidos <span class="tag">Liga Profesional</span></div>
                <table class="futdb-table">
                    <thead><tr>
                        <th>Fecha</th><th>Hora</th><th>Jornada</th>
                        <th style="text-align:right">Local</th><th></th>
                        <th>Visitante</th><th>Estadio</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("No hay próximos partidos programados.")


# ── 4. TRANSFERENCIAS ─────────────────────────────────────────────────────────
elif pagina.startswith("🔄"):
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                font-weight:900;color:#fff;margin-bottom:.4rem">
        Transferencias <span style="color:#f59e0b">Argentinas</span>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:.72rem;color:#4b5a4d;margin-bottom:1.5rem">
        Movimientos del mercado · jugadores argentinos en el mundo
    </div>""", unsafe_allow_html=True)

    df_t = _conector_arg.transferencias_recientes() if CONECTOR_ARG_OK and _conector_arg else pd.DataFrame()

    if df_t.empty:
        st.info("Sin datos de transferencias disponibles.")
    else:
        mayor = df_t.loc[df_t["€ M"].idxmax()]
        arg_ext = len(df_t[df_t["Destino"].str.contains(r"(?i)\((?!ARG)", regex=True)])

        render_kpis([
            {"label": "Mayor traspaso",   "value": f"€{int(mayor['€ M'])}M", "sub": f"{mayor['Jugador']} · {mayor['Destino']}", "tipo": "gold"},
            {"label": "ARG al exterior",  "value": str(arg_ext),             "sub": "jugadores exportados",                      "tipo": ""},
            {"label": "Valor promedio",   "value": f"€{df_t['€ M'].mean():.0f}M", "sub": "por transferencia",                   "tipo": ""},
            {"label": "Registros",        "value": str(len(df_t)),           "sub": "movimientos curados",                       "tipo": "coral"},
        ])

        rows_html = ""
        for i, r in df_t.iterrows():
            monto = r["€ M"]
            monto_str = f"€{int(monto)}M" if pd.notna(monto) and monto > 0 else "—"
            tipo_color = {"Traspaso": "#4ade80", "Préstamo": "#60a5fa", "Libre": "#f87171", "Renovación": "#f59e0b"}.get(r["Tipo"], "#4b5a4d")
            rows_html += f"""
            <tr>
                <td class="highlight">{r['Jugador']}</td>
                <td style="color:#4b5a4d;font-size:.82rem">{r['Origen']}</td>
                <td style="font-size:.75rem;color:#4b5a4d;text-align:center">→</td>
                <td class="highlight">{r['Destino']}</td>
                <td class="num" style="color:#f59e0b;font-weight:600">{monto_str}</td>
                <td><span style="font-family:'DM Mono',monospace;font-size:.7rem;
                    color:{tipo_color};background:{tipo_color}18;
                    padding:.15rem .5rem;border-radius:4px">{r['Tipo']}</span></td>
                <td class="num" style="color:#4b5a4d;font-size:.78rem">{r['Temp.']}</td>
            </tr>"""

        st.markdown(f"""
        <div class="table-card">
            <div class="table-card-header">Transferencias destacadas <span class="tag">jugadores ARG</span></div>
            <table class="futdb-table">
                <thead><tr>
                    <th>Jugador</th><th>Origen</th><th></th><th>Destino</th>
                    <th class="num">Monto</th><th>Tipo</th><th class="num">Temp.</th>
                </tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>""", unsafe_allow_html=True)

        section("Montos por transferencia", "en millones de €")
        df_sort = df_t[df_t["€ M"] > 0].sort_values("€ M", ascending=True)
        fig4 = px.bar(df_sort, y="Jugador", x="€ M", orientation="h",
                      color="€ M", color_continuous_scale=["#2a1f00","#f59e0b"],
                      text="€ M")
        fig4.update_traces(marker_line_width=0,
                           texttemplate="€%{text:.0f}M", textposition="outside",
                           textfont=dict(family="DM Mono", size=9, color="#4b5a4d"))
        fig4.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111412",
            height=max(280, len(df_sort)*28), coloraxis_showscale=False,
            margin=dict(l=10, r=60, t=10, b=10),
            xaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=9, color="#4b5a4d")),
            yaxis=dict(tickfont=dict(family="DM Mono", size=9, color="#6b7a6d"), title=None),
        )
        st.plotly_chart(fig4, use_container_width=True)


# ── 5. ESTADIOS ───────────────────────────────────────────────────────────────
elif pagina.startswith("🏟"):
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                font-weight:900;color:#fff;margin-bottom:.4rem">
        Grandes <span style="color:#4ade80">Estadios</span>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:.72rem;color:#4b5a4d;margin-bottom:1.5rem">
        Infraestructura · capacidad · historia
    </div>""", unsafe_allow_html=True)

    filtro = st.selectbox("Filtrar por liga/país",
                          ["Todos"] + sorted(set(e["liga"] for e in ESTADIOS)))
    estadios_fil = ESTADIOS if filtro == "Todos" else [e for e in ESTADIOS if e["liga"] == filtro]

    cards_html = '<div class="stadium-grid">'
    for e in sorted(estadios_fil, key=lambda x: -x["capacidad"]):
        cap_fmt = f"{e['capacidad']:,}".replace(",", ".")
        cards_html += f"""
        <div class="stadium-card">
            <div class="stadium-img-placeholder">{e['emoji']}</div>
            <div class="stadium-body">
                <div class="stadium-name">{e['nombre']}</div>
                <div class="stadium-club">{e['pais']} · {e['club']} · {e['liga']}</div>
                <div class="stadium-stats">
                    <div class="stadium-stat">
                        <div class="val">{cap_fmt}</div>
                        <div class="lbl">Capacidad</div>
                    </div>
                    <div class="stadium-stat">
                        <div class="val">{e['año']}</div>
                        <div class="lbl">Inauguración</div>
                    </div>
                    <div class="stadium-stat">
                        <div class="val">{2025 - e['año']}</div>
                        <div class="lbl">Años</div>
                    </div>
                </div>
            </div>
        </div>"""
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    section("Capacidad comparativa", "top 12 estadios en la base")
    df_est = pd.DataFrame(estadios_fil).sort_values("capacidad", ascending=True)
    fig5 = px.bar(df_est, y="nombre", x="capacidad", orientation="h",
                  color="capacidad", color_continuous_scale=["#1e2420", "#4ade80"])
    fig5.update_traces(marker_line_width=0)
    fig5.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111412",
        height=max(280, len(df_est) * 36),
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_showscale=False, showlegend=False,
        xaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=9, color="#4b5a4d")),
        yaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=9, color="#6b7a6d"),
                   title=None),
    )
    st.plotly_chart(fig5, use_container_width=True)

# ── 6. NUTRICIÓN ──────────────────────────────────────────────────────────────
elif pagina.startswith("🥗"):
    st.markdown("""
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:2rem;
                font-weight:900;color:#fff;margin-bottom:.4rem">
        Nutrición <span style="color:#4ade80">Deportiva</span>
    </div>
    <div style="font-family:'DM Mono',monospace;font-size:.72rem;color:#4b5a4d;margin-bottom:1.5rem">
        Requerimientos por posición · macros · estrategia de recuperación
    </div>""", unsafe_allow_html=True)

    st.info("🔬 Capa secundaria de datos — complementa el análisis de rendimiento físico con contexto nutricional por posición.", icon="🥗")

    col1, col2 = st.columns(2)
    for i, n in enumerate(NUTRICION):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(f"""
            <div class="nutri-card">
                <div class="nutri-position">{n['posicion']}</div>
                <div class="nutri-title">{n['titulo']}</div>
                <div class="nutri-macros">
                    <span class="macro-pill cal">🔥 {n['calorias']}</span>
                    <span class="macro-pill carbs">🍚 CH {n['carbs']}</span>
                    <span class="macro-pill prot">💪 Prot {n['proteinas']}</span>
                    <span class="macro-pill fat">🫒 Grasas {n['grasas']}</span>
                </div>
                <div class="nutri-detail">{n['detalle']}</div>
                <div style="margin-top:.6rem;font-family:'DM Mono',monospace;
                            font-size:.68rem;color:#4b5a4d">
                    ALIMENTOS CLAVE: {n['alimentos_clave']}
                </div>
            </div>""", unsafe_allow_html=True)

    section("Requerimiento calórico por posición", "kcal/día en semana de competición")
    df_nut = pd.DataFrame(NUTRICION)[["posicion", "calorias_val"]]
    fig6 = px.bar(df_nut, x="posicion", y="calorias_val",
                  color="calorias_val",
                  color_continuous_scale=["#162119", "#4ade80"],
                  text="calorias_val")
    fig6.update_traces(marker_line_width=0,
                       texttemplate="%{text:,} kcal",
                       textposition="outside",
                       textfont=dict(family="DM Mono", size=10, color="#4b5a4d"))
    fig6.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#111412",
        height=300, margin=dict(l=10, r=10, t=40, b=10),
        coloraxis_showscale=False,
        xaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=10, color="#6b7a6d"), title=None),
        yaxis=dict(gridcolor="#1a1f1c", tickfont=dict(family="DM Mono", size=9, color="#4b5a4d"), range=[2500, 4200]),
    )
    st.plotly_chart(fig6, use_container_width=True)

# ── 7. PLANTEL ────────────────────────────────────────────────────────────────
elif pagina.startswith("📋"):
    if _PLANTEL_OK:
        render_plantel()
    else:
        st.error("Módulo Plantel no disponible. Verificá que `pages/page_plantel.py` y `data/connector_plantel.py` estén en el proyecto.")

