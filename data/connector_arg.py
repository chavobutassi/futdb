"""
FUTDB — connector_arg.py
Ligas no cubiertas por football-data.org
Fuente: API-Football via RapidAPI (100 req/día gratis)
Registro: rapidapi.com/api-sports/api/api-football → plan Basic (Free)
"""
from __future__ import annotations
import logging, os
from collections import defaultdict
from datetime import datetime
import pandas as pd
import requests

log = logging.getLogger("futdb.connector_arg")

# IDs de liga en API-Football
LIGAS_APIF = {
    "CLI": {"id": 128,  "nombre": "Liga Profesional Argentina", "temporada": 2024},
    "MLS": {"id": 253,  "nombre": "MLS",                        "temporada": 2024},
    "BSA": {"id": 71,   "nombre": "Brasileirão",                "temporada": 2024},
    "MX":  {"id": 262,  "nombre": "Liga MX",                    "temporada": 2024},
    "COL": {"id": 239,  "nombre": "Liga Betplay Colombia",      "temporada": 2024},
}

BASE = "https://api-football-v1.p.rapidapi.com/v3"

NOMBRES = {
    "Atletico Tucuman":  "Atlético Tucumán",
    "Lanus":             "Lanús",
    "Huracan":           "Huracán",
    "Talleres Cordoba":  "Talleres",
    "Velez Sarsfield":   "Vélez Sarsfield",
    "Union Santa Fe":    "Unión",
    "Colon Santa Fe":    "Colón",
    "Arsenal Sarandi":   "Arsenal",
    "San Martin Tucuman":"San Martín Tucumán",
    "Estudiantes LP":    "Estudiantes",
    "Newell's Old Boys": "Newell's",
}

def _n(s): return NOMBRES.get(s, s)


class ConectorArg:
    """
    Conector para ligas latinoamericanas y MLS.
    Requiere RAPIDAPI_KEY en el archivo .env del proyecto.
    Plan gratuito: 100 requests/día — suficiente para uso normal.
    """

    def __init__(self, rapidapi_key: str = ""):
        self._key = rapidapi_key or os.getenv("RAPIDAPI_KEY", "")
        self._session = requests.Session()
        self._cache: dict = {}
        if self._key:
            log.info("[ARG] Inicializado — API-Football (RapidAPI)")
        else:
            log.warning("[ARG] Sin RAPIDAPI_KEY — datos de ejemplo activos")

    def _hdr(self):
        return {
            "X-RapidAPI-Key":  self._key,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
        }

    def _get(self, endpoint: str, params: dict) -> dict:
        url = f"{BASE}/{endpoint}"
        cache_key = f"{endpoint}_{params}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            r = self._session.get(url, headers=self._hdr(), params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            self._cache[cache_key] = data
            return data
        except Exception as e:
            log.error(f"[ARG] Error {endpoint}: {e}")
            return {}

    @property
    def disponible(self) -> bool:
        return bool(self._key)

    # ── Tabla de posiciones ──────────────────────────────────────────────────

    def tabla_posiciones(self, liga_id: str = "CLI") -> pd.DataFrame:
        if not self._key:
            return pd.DataFrame()
        meta = LIGAS_APIF.get(liga_id)
        if not meta:
            return pd.DataFrame()

        data = self._get("standings", {"league": meta["id"], "season": meta["temporada"]})
        try:
            standings = data["response"][0]["league"]["standings"][0]
        except (KeyError, IndexError):
            log.warning(f"[ARG] Sin standings para {meta['nombre']}")
            return pd.DataFrame()

        filas = []
        for e in standings:
            dg = e.get("goalsDiff", 0)
            all_ = e.get("all", {})
            goals = all_.get("goals", {})
            forma = e.get("form", "")
            filas.append({
                "#":    e.get("rank"),
                "Club": e.get("team", {}).get("name", ""),
                "PJ":   all_.get("played", 0),
                "G":    all_.get("win", 0),
                "E":    all_.get("draw", 0),
                "P":    all_.get("lose", 0),
                "GF":   goals.get("for", 0),
                "GC":   goals.get("against", 0),
                "DG":   f"+{dg}" if dg >= 0 else str(dg),
                "Pts":  e.get("points", 0),
                "Forma": forma,
            })

        df = pd.DataFrame(filas).sort_values("#").reset_index(drop=True)
        log.info(f"[ARG] Tabla cargada: {meta['nombre']} — {len(df)} equipos")
        return df

    # ── Resultados recientes ─────────────────────────────────────────────────

    def resultados_recientes(self, liga_id: str = "CLI", cantidad: int = 10) -> pd.DataFrame:
        if not self._key:
            return pd.DataFrame()
        meta = LIGAS_APIF.get(liga_id, {})
        if not meta:
            return pd.DataFrame()

        data = self._get("fixtures", {
            "league": meta["id"], "season": meta["temporada"],
            "status": "FT", "last": cantidad,
        })
        filas = []
        for f in data.get("response", []):
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            fixture = f.get("fixture", {})
            filas.append({
                "fecha":           fixture.get("date", "")[:10],
                "jornada":         f.get("league", {}).get("round", ""),
                "local":           teams.get("home", {}).get("name", ""),
                "visitante":       teams.get("away", {}).get("name", ""),
                "goles_local":     goals.get("home"),
                "goles_visitante": goals.get("away"),
                "estadio":         fixture.get("venue", {}).get("name", ""),
            })
        return pd.DataFrame(filas)

    # ── Próximos partidos ────────────────────────────────────────────────────

    def proximos_partidos(self, liga_id: str = "CLI", cantidad: int = 10) -> pd.DataFrame:
        if not self._key:
            return pd.DataFrame()
        meta = LIGAS_APIF.get(liga_id, {})
        if not meta:
            return pd.DataFrame()

        data = self._get("fixtures", {
            "league": meta["id"], "season": meta["temporada"],
            "status": "NS", "next": cantidad,
        })
        filas = []
        for f in data.get("response", []):
            teams   = f.get("teams", {})
            fixture = f.get("fixture", {})
            filas.append({
                "fecha":     fixture.get("date", "")[:10],
                "hora":      fixture.get("date", "")[11:16],
                "jornada":   f.get("league", {}).get("round", ""),
                "local":     teams.get("home", {}).get("name", ""),
                "visitante": teams.get("away", {}).get("name", ""),
                "estadio":   fixture.get("venue", {}).get("name", ""),
            })
        return pd.DataFrame(filas)

    # ── Estadísticas de jugador ──────────────────────────────────────────────

    def stats_jugador(self, jugador_id: int, liga_id: str = "CLI") -> dict:
        """Estadísticas detalladas de un jugador en la temporada."""
        if not self._key:
            return {}
        meta = LIGAS_APIF.get(liga_id, {})
        data = self._get("players", {
            "id": jugador_id,
            "league": meta.get("id"),
            "season": meta.get("temporada"),
        })
        try:
            return data["response"][0]
        except (KeyError, IndexError):
            return {}
