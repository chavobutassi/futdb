"""
connector_arg.py
================
Conector Argentina — api-sports.io (v3.football.api-sports.io)
Liga Profesional Argentina + Copa Argentina + Selección

API Key: variable APISPORTS_KEY en .env
Plan gratuito: 100 requests/día
Documentación: https://www.api-football.com/documentation-v3

Ligas Argentina:
    128  — Liga Profesional Argentina
    130  — Copa Argentina
    131  — Primera Nacional (ascenso)
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("futdb.connector_arg")

BASE = "https://v3.football.api-sports.io"

# Ligas disponibles
LIGAS_ARG = {
    "CLI": {"id": 128, "nombre": "Liga Profesional", "pais": "Argentina", "temporada": 2026},
    "CAR": {"id": 130, "nombre": "Copa Argentina",   "pais": "Argentina", "temporada": 2026},
    "PNA": {"id": 131, "nombre": "Primera Nacional", "pais": "Argentina", "temporada": 2026},
}

# Normalización de nombres
NOMBRES = {
    "Atletico Tucuman":   "Atlético Tucumán",
    "Lanus":              "Lanús",
    "Huracan":            "Huracán",
    "Talleres Cordoba":   "Talleres",
    "Velez Sarsfield":    "Vélez Sarsfield",
    "Union Santa Fe":     "Unión",
    "Colon Santa Fe":     "Colón",
    "Arsenal Sarandi":    "Arsenal",
    "San Martin Tucuman": "San Martín Tucumán",
    "Estudiantes LP":     "Estudiantes",
    "Newell's Old Boys":  "Newell's",
    "Godoy Cruz":         "Godoy Cruz",
    "Sarmiento Junin":    "Sarmiento",
    "Central Cordoba":    "Central Córdoba",
    "Argentinos Juniors": "Argentinos Jrs.",
}

def _n(s: str) -> str:
    return NOMBRES.get(s, s)


class ConectorArg:
    """
    Conector principal para fútbol argentino.
    Usa api-sports.io con la key APISPORTS_KEY del .env.
    Fallback automático a datos de ejemplo si no hay key.
    """

    def __init__(self):
        self._key     = os.getenv("APISPORTS_KEY", "")
        self._session = requests.Session()
        self._cache:  dict = {}
        self._req_count = 0

        if self._key:
            log.info("[ARG] Conectado a api-sports.io ✓")
        else:
            log.warning("[ARG] Sin APISPORTS_KEY — usando datos de ejemplo")

    @property
    def disponible(self) -> bool:
        return bool(self._key)

    def _hdr(self) -> dict:
        return {"x-apisports-key": self._key}

    def _get(self, endpoint: str, params: dict) -> dict:
        if not self._key:
            return {}
        cache_key = f"{endpoint}_{sorted(params.items())}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            r = self._session.get(
                f"{BASE}/{endpoint}",
                headers=self._hdr(),
                params=params,
                timeout=15,
            )
            remaining = r.headers.get("x-ratelimit-requests-remaining", "?")
            log.info(f"[ARG] {endpoint} — requests restantes hoy: {remaining}")
            r.raise_for_status()
            data = r.json()
            self._cache[cache_key] = data
            self._req_count += 1
            return data
        except Exception as e:
            log.error(f"[ARG] Error {endpoint}: {e}")
            return {}

    # ── Tabla de posiciones ───────────────────────────────────────────────────

    def tabla_posiciones(self, liga_id: str = "CLI") -> pd.DataFrame:
        meta = LIGAS_ARG.get(liga_id, LIGAS_ARG["CLI"])
        data = self._get("standings", {"league": meta["id"], "season": meta["temporada"]})

        try:
            standings = data["response"][0]["league"]["standings"][0]
        except (KeyError, IndexError):
            log.warning(f"[ARG] Sin standings → datos ejemplo")
            return _demo_tabla()

        filas = []
        for e in standings:
            dg  = e.get("goalsDiff", 0)
            all_ = e.get("all", {})
            goals = all_.get("goals", {})
            filas.append({
                "#":     e.get("rank"),
                "Club":  _n(e.get("team", {}).get("name", "")),
                "Logo":  e.get("team", {}).get("logo", ""),
                "PJ":    all_.get("played", 0),
                "G":     all_.get("win", 0),
                "E":     all_.get("draw", 0),
                "P":     all_.get("lose", 0),
                "GF":    goals.get("for", 0),
                "GC":    goals.get("against", 0),
                "DG":    f"+{dg}" if dg >= 0 else str(dg),
                "Pts":   e.get("points", 0),
                "Forma": e.get("form", ""),
            })

        df = pd.DataFrame(filas).sort_values("#").reset_index(drop=True)
        log.info(f"[ARG] Tabla cargada: {meta['nombre']} — {len(df)} equipos")
        return df

    # ── Resultados recientes ──────────────────────────────────────────────────

    def resultados_recientes(self, liga_id: str = "CLI", cantidad: int = 10) -> pd.DataFrame:
        meta = LIGAS_ARG.get(liga_id, LIGAS_ARG["CLI"])
        data = self._get("fixtures", {
            "league": meta["id"],
            "season": meta["temporada"],
            "status": "FT",
            "last":   cantidad,
        })
        filas = []
        for f in data.get("response", []):
            teams   = f.get("teams", {})
            goals   = f.get("goals", {})
            fixture = f.get("fixture", {})
            filas.append({
                "Fecha":     fixture.get("date", "")[:10],
                "Jornada":   f.get("league", {}).get("round", "").replace("Regular Season - ", "J"),
                "Local":     _n(teams.get("home", {}).get("name", "")),
                "Resultado": f"{goals.get('home','?')} - {goals.get('away','?')}",
                "Visitante": _n(teams.get("away", {}).get("name", "")),
                "Estadio":   fixture.get("venue", {}).get("name", ""),
            })
        if not filas:
            return _demo_resultados()
        return pd.DataFrame(filas)

    # ── Próximos partidos ─────────────────────────────────────────────────────

    def proximos_partidos(self, liga_id: str = "CLI", cantidad: int = 10) -> pd.DataFrame:
        meta = LIGAS_ARG.get(liga_id, LIGAS_ARG["CLI"])
        data = self._get("fixtures", {
            "league": meta["id"],
            "season": meta["temporada"],
            "status": "NS",
            "next":   cantidad,
        })
        filas = []
        for f in data.get("response", []):
            teams   = f.get("teams", {})
            fixture = f.get("fixture", {})
            filas.append({
                "Fecha":     fixture.get("date", "")[:10],
                "Hora":      fixture.get("date", "")[11:16],
                "Jornada":   f.get("league", {}).get("round", "").replace("Regular Season - ", "J"),
                "Local":     _n(teams.get("home", {}).get("name", "")),
                "Visitante": _n(teams.get("away", {}).get("name", "")),
                "Estadio":   fixture.get("venue", {}).get("name", ""),
            })
        if not filas:
            return _demo_proximos()
        return pd.DataFrame(filas)

    # ── Top goleadores ────────────────────────────────────────────────────────

    def top_goleadores(self, liga_id: str = "CLI") -> pd.DataFrame:
        meta = LIGAS_ARG.get(liga_id, LIGAS_ARG["CLI"])
        data = self._get("players/topscorers", {
            "league": meta["id"],
            "season": meta["temporada"],
        })
        filas = []
        for i, item in enumerate(data.get("response", []), 1):
            p    = item.get("player", {})
            stat = item.get("statistics", [{}])[0]
            goals = stat.get("goals", {})
            games = stat.get("games", {})
            filas.append({
                "#":        i,
                "Jugador":  p.get("name", ""),
                "Club":     _n(stat.get("team", {}).get("name", "")),
                "Goles":    goals.get("total", 0),
                "Asist.":   goals.get("assists", 0) or 0,
                "PJ":       games.get("appearences", 0) or 0,
                "G/90":     round((goals.get("total", 0) or 0) / max(games.get("minutes", 1) or 1, 1) * 90, 2),
                "Nac.":     p.get("nationality", ""),
            })
        if not filas:
            return _demo_goleadores()
        return pd.DataFrame(filas)

    # ── Top asistidores ───────────────────────────────────────────────────────

    def top_asistidores(self, liga_id: str = "CLI") -> pd.DataFrame:
        meta = LIGAS_ARG.get(liga_id, LIGAS_ARG["CLI"])
        data = self._get("players/topassists", {
            "league": meta["id"],
            "season": meta["temporada"],
        })
        filas = []
        for i, item in enumerate(data.get("response", []), 1):
            p    = item.get("player", {})
            stat = item.get("statistics", [{}])[0]
            goals = stat.get("goals", {})
            games = stat.get("games", {})
            filas.append({
                "#":       i,
                "Jugador": p.get("name", ""),
                "Club":    _n(stat.get("team", {}).get("name", "")),
                "Asist.":  goals.get("assists", 0) or 0,
                "Goles":   goals.get("total", 0) or 0,
                "PJ":      games.get("appearences", 0) or 0,
                "Nac.":    p.get("nationality", ""),
            })
        if not filas:
            return _demo_asistidores()
        return pd.DataFrame(filas)

    # ── Transferencias Argentina ──────────────────────────────────────────────

    def transferencias_recientes(self) -> pd.DataFrame:
        """
        Transferencias destacadas del fútbol argentino.
        api-sports.io no tiene endpoint de transferencias en plan free
        → datos curados actualizados manualmente.
        """
        return pd.DataFrame([
            {"Jugador": "Valentín Carboni",    "Origen": "Inter (ITA)",       "Destino": "Marsella (FRA)",    "€ M": 36,  "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Alexis Mac Allister", "Origen": "Brighton (ENG)",    "Destino": "Liverpool (ENG)",   "€ M": 35,  "Tipo": "Traspaso",   "Temp.": "23/24"},
            {"Jugador": "Enzo Fernández",      "Origen": "Benfica (POR)",     "Destino": "Chelsea (ENG)",     "€ M": 121, "Tipo": "Traspaso",   "Temp.": "22/23"},
            {"Jugador": "Nicolás González",    "Origen": "Fiorentina (ITA)",  "Destino": "Juventus (ITA)",    "€ M": 30,  "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Thiago Almada",       "Origen": "Atlanta Utd (USA)", "Destino": "Botafogo (BRA)",    "€ M": 18,  "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Facundo Colidio",     "Origen": "Tigre (ARG)",       "Destino": "Boca Juniors (ARG)","€ M": 2,   "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Gianluca Prestianni", "Origen": "Vélez (ARG)",       "Destino": "Benfica (POR)",     "€ M": 12,  "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Equi Fernández",      "Origen": "Boca Juniors (ARG)","Destino": "Chelsea (ENG)",     "€ M": 28,  "Tipo": "Traspaso",   "Temp.": "23/24"},
            {"Jugador": "Cristian Medina",     "Origen": "Boca Juniors (ARG)","Destino": "Fenerbahçe (TUR)",  "€ M": 10,  "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Lautaro Blanco",      "Origen": "Newell's (ARG)",    "Destino": "Boca Juniors (ARG)","€ M": 3,   "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Kevin Zenón",         "Origen": "Unión (ARG)",       "Destino": "Boca Juniors (ARG)","€ M": 4,   "Tipo": "Traspaso",   "Temp.": "24/25"},
            {"Jugador": "Miguel Merentiel",    "Origen": "Boca Juniors (ARG)","Destino": "Palmeiras (BRA)",   "€ M": 8,   "Tipo": "Traspaso",   "Temp.": "24/25"},
        ])

    # ── Info de requests ──────────────────────────────────────────────────────

    def requests_usados(self) -> int:
        return self._req_count


# ── Datos demo (fallback sin key) ─────────────────────────────────────────────

def _demo_tabla() -> pd.DataFrame:
    return pd.DataFrame([
        {"#":1,  "Club":"River Plate",      "PJ":27,"G":17,"E":5,"P":5, "GF":51,"GC":28,"DG":"+23","Pts":56,"Forma":"WWWDW"},
        {"#":2,  "Club":"Vélez Sarsfield",  "PJ":27,"G":16,"E":4,"P":7, "GF":43,"GC":29,"DG":"+14","Pts":52,"Forma":"WWDWL"},
        {"#":3,  "Club":"Racing Club",      "PJ":27,"G":15,"E":6,"P":6, "GF":45,"GC":27,"DG":"+18","Pts":51,"Forma":"WDWWW"},
        {"#":4,  "Club":"Boca Juniors",     "PJ":27,"G":14,"E":7,"P":6, "GF":40,"GC":30,"DG":"+10","Pts":49,"Forma":"DWWLW"},
        {"#":5,  "Club":"Huracán",          "PJ":27,"G":13,"E":6,"P":8, "GF":38,"GC":32,"DG":"+6", "Pts":45,"Forma":"WLWDW"},
        {"#":6,  "Club":"Independiente",    "PJ":27,"G":12,"E":7,"P":8, "GF":36,"GC":33,"DG":"+3", "Pts":43,"Forma":"DWLWW"},
        {"#":7,  "Club":"San Lorenzo",      "PJ":27,"G":11,"E":8,"P":8, "GF":35,"GC":34,"DG":"+1", "Pts":41,"Forma":"WDLWD"},
        {"#":8,  "Club":"Estudiantes",      "PJ":27,"G":11,"E":7,"P":9, "GF":34,"GC":35,"DG":"-1", "Pts":40,"Forma":"LDWWL"},
        {"#":9,  "Club":"Talleres",         "PJ":27,"G":10,"E":9,"P":8, "GF":33,"GC":33,"DG":"0",  "Pts":39,"Forma":"DWDLW"},
        {"#":10, "Club":"Atlético Tucumán", "PJ":27,"G":10,"E":8,"P":9, "GF":31,"GC":34,"DG":"-3", "Pts":38,"Forma":"WLLWD"},
    ])

def _demo_resultados() -> pd.DataFrame:
    return pd.DataFrame([
        {"Fecha":"2024-12-15","Jornada":"J27","Local":"River Plate",   "Resultado":"3 - 1","Visitante":"San Lorenzo",    "Estadio":"Monumental"},
        {"Fecha":"2024-12-15","Jornada":"J27","Local":"Boca Juniors",  "Resultado":"1 - 1","Visitante":"Racing Club",     "Estadio":"La Bombonera"},
        {"Fecha":"2024-12-14","Jornada":"J27","Local":"Huracán",       "Resultado":"2 - 0","Visitante":"Independiente",   "Estadio":"Palermo"},
        {"Fecha":"2024-12-14","Jornada":"J27","Local":"Vélez Sarsfield","Resultado":"2 - 1","Visitante":"Estudiantes",   "Estadio":"J. Amalfitani"},
        {"Fecha":"2024-12-13","Jornada":"J27","Local":"Talleres",      "Resultado":"0 - 0","Visitante":"Atlético Tucumán","Estadio":"Mario Kempes"},
    ])

def _demo_proximos() -> pd.DataFrame:
    return pd.DataFrame([
        {"Fecha":"2025-01-25","Hora":"21:00","Jornada":"J1","Local":"River Plate",    "Visitante":"Boca Juniors",    "Estadio":"Monumental"},
        {"Fecha":"2025-01-25","Hora":"19:00","Jornada":"J1","Local":"Racing Club",    "Visitante":"Independiente",   "Estadio":"El Cilindro"},
        {"Fecha":"2025-01-26","Hora":"21:00","Jornada":"J1","Local":"Vélez Sarsfield","Visitante":"Huracán",         "Estadio":"J. Amalfitani"},
        {"Fecha":"2025-01-26","Hora":"17:00","Jornada":"J1","Local":"San Lorenzo",    "Visitante":"Estudiantes",     "Estadio":"Nuevo Gasómetro"},
        {"Fecha":"2025-01-26","Hora":"19:00","Jornada":"J1","Local":"Talleres",       "Visitante":"Atlético Tucumán","Estadio":"Mario Kempes"},
    ])

def _demo_goleadores() -> pd.DataFrame:
    return pd.DataFrame([
        {"#":1, "Jugador":"Miguel Merentiel",  "Club":"Boca Juniors",  "Goles":18,"Asist.":5,"PJ":25,"G/90":0.72,"Nac.":"Uruguay"},
        {"#":2, "Jugador":"Facundo Colidio",   "Club":"Tigre",         "Goles":15,"Asist.":4,"PJ":26,"G/90":0.58,"Nac.":"Argentina"},
        {"#":3, "Jugador":"Salomón Rondón",    "Club":"River Plate",   "Goles":14,"Asist.":3,"PJ":24,"G/90":0.55,"Nac.":"Venezuela"},
        {"#":4, "Jugador":"Mauro Zárate",      "Club":"Vélez Sarsfield","Goles":13,"Asist.":6,"PJ":25,"G/90":0.52,"Nac.":"Argentina"},
        {"#":5, "Jugador":"Ramón Ábila",       "Club":"Huracán",       "Goles":12,"Asist.":2,"PJ":23,"G/90":0.50,"Nac.":"Argentina"},
        {"#":6, "Jugador":"Jonathan Calleri",  "Club":"San Lorenzo",   "Goles":11,"Asist.":4,"PJ":24,"G/90":0.46,"Nac.":"Argentina"},
        {"#":7, "Jugador":"Ignacio Pussetto",  "Club":"Independiente", "Goles":10,"Asist.":3,"PJ":25,"G/90":0.40,"Nac.":"Argentina"},
        {"#":8, "Jugador":"Javier Toledo",     "Club":"Talleres",      "Goles":9, "Asist.":2,"PJ":22,"G/90":0.38,"Nac.":"Argentina"},
        {"#":9, "Jugador":"Leandro Díaz",      "Club":"Estudiantes",   "Goles":9, "Asist.":5,"PJ":26,"G/90":0.37,"Nac.":"Argentina"},
        {"#":10,"Jugador":"Matías Giménez",    "Club":"Racing Club",   "Goles":8, "Asist.":3,"PJ":24,"G/90":0.35,"Nac.":"Argentina"},
    ])

def _demo_asistidores() -> pd.DataFrame:
    return pd.DataFrame([
        {"#":1, "Jugador":"Kevin Zenón",       "Club":"Boca Juniors",  "Asist.":10,"Goles":4,"PJ":25,"Nac.":"Argentina"},
        {"#":2, "Jugador":"Gonzalo Montiel",   "Club":"River Plate",   "Asist.":9, "Goles":2,"PJ":26,"Nac.":"Argentina"},
        {"#":3, "Jugador":"Leandro Díaz",      "Club":"Estudiantes",   "Asist.":8, "Goles":9,"PJ":26,"Nac.":"Argentina"},
        {"#":4, "Jugador":"Rodrigo Aliendro",  "Club":"Racing Club",   "Asist.":7, "Goles":3,"PJ":24,"Nac.":"Argentina"},
        {"#":5, "Jugador":"Mauro Zárate",      "Club":"Vélez Sarsfield","Asist.":6,"Goles":13,"PJ":25,"Nac.":"Argentina"},
    ])
