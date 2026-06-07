"""
FUTDB — connector_futbol.py
Conector principal. Ligas europeas vía football-data.org.
"""
from __future__ import annotations
import logging, sqlite3, time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup

log = logging.getLogger("futdb.connector")

LIGAS = {
    "PL":  {"nombre": "Premier League",   "pais": "Inglaterra", "tier": 1},
    "PD":  {"nombre": "LaLiga",           "pais": "España",     "tier": 1},
    "BL1": {"nombre": "Bundesliga",       "pais": "Alemania",   "tier": 1},
    "SA":  {"nombre": "Serie A",          "pais": "Italia",     "tier": 1},
    "FL1": {"nombre": "Ligue 1",          "pais": "Francia",    "tier": 1},
    "CL":  {"nombre": "Champions League", "pais": "Europa",     "tier": 0},
    "CLI": {"nombre": "Liga Profesional", "pais": "Argentina",  "tier": 1},
    "MLS": {"nombre": "MLS",             "pais": "USA",         "tier": 1},
    "BSA": {"nombre": "Brasileirão",      "pais": "Brasil",     "tier": 1},
}

FBREF_LIGAS = {"PL":"9","PD":"12","BL1":"20","SA":"11","FL1":"13","CLI":"21"}

DB_PATH = Path(__file__).parent.parent / "db" / "futdb.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jugadores (
    jugador_id TEXT PRIMARY KEY, nombre TEXT, nacionalidad TEXT,
    posicion TEXT, club_actual TEXT, liga_actual TEXT,
    contrato_hasta TEXT, valor_mercado REAL, actualizado TEXT
);
CREATE TABLE IF NOT EXISTS transferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT, jugador_id TEXT,
    nombre_jugador TEXT, club_origen TEXT, club_destino TEXT,
    liga_origen TEXT, liga_destino TEXT, fecha TEXT,
    monto_eur REAL, tipo TEXT, temporada TEXT, fuente TEXT
);
CREATE TABLE IF NOT EXISTS estadisticas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, jugador_id TEXT,
    temporada TEXT, liga_id TEXT, club TEXT, partidos INTEGER,
    minutos INTEGER, goles INTEGER, asistencias INTEGER,
    xg REAL, xag REAL, pases_clave INTEGER, fuente TEXT
);
CREATE TABLE IF NOT EXISTS partidos (
    partido_id TEXT PRIMARY KEY, liga_id TEXT, temporada TEXT,
    fecha TEXT, jornada INTEGER, local TEXT, visitante TEXT,
    goles_local INTEGER, goles_visitante INTEGER, estado TEXT
);
"""

def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.executescript(SCHEMA)
    conn.commit()
    log.info(f"[FUTDB] DB lista: {DB_PATH}")
    return conn


class ConectorFutbol:
    BASE_FD = "https://api.football-data.org/v4"
    BASE_FBREF = "https://fbref.com/en/comps"
    HDR_SCRAPING = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def __init__(self, api_key_football_data: str = ""):
        self._key = api_key_football_data
        self._conn = _init_db()
        self._session = requests.Session()
        self._session.headers.update(self.HDR_SCRAPING)
        log.info("[FUTDB] Conector inicializado.")

    def _hdr_fd(self):
        return {"X-Auth-Token": self._key, "User-Agent": "FUTDB/1.0"}

    def _get_fd(self, endpoint: str):
        url = f"{self.BASE_FD}/{endpoint}"
        try:
            r = self._session.get(url, headers=self._hdr_fd(), timeout=10)
            if r.status_code == 429:
                time.sleep(60)
                r = self._session.get(url, headers=self._hdr_fd(), timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error(f"[FUTDB] Error FD ({endpoint}): {e}")
            return None

    def _scrape(self, url: str, delay=1.5):
        time.sleep(delay)
        try:
            r = self._session.get(url, timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.error(f"[FUTDB] Error scraping {url}: {e}")
            return None

    def tabla_posiciones(self, liga_id="PL") -> pd.DataFrame:
        if not self._key:
            return pd.DataFrame()
        data = self._get_fd(f"competitions/{liga_id}/standings")
        if not data:
            return pd.DataFrame()
        filas = []
        for e in data.get("standings",[{}])[0].get("table",[]):
            dg = e.get("goalDifference", 0)
            filas.append({
                "#":   e.get("position"),
                "Club": e.get("team",{}).get("name"),
                "PJ":  e.get("playedGames"),
                "G":   e.get("won"),
                "E":   e.get("draw"),
                "P":   e.get("lost"),
                "GF":  e.get("goalsFor"),
                "GC":  e.get("goalsAgainst"),
                "DG":  f"+{dg}" if dg >= 0 else str(dg),
                "Pts": e.get("points"),
                "Forma": e.get("form",""),
            })
        return pd.DataFrame(filas)

    def proximos_partidos(self, liga_id="PL", dias=7) -> pd.DataFrame:
        if not self._key:
            return pd.DataFrame()
        d0 = datetime.today().strftime("%Y-%m-%d")
        d1 = (datetime.today()+timedelta(days=dias)).strftime("%Y-%m-%d")
        data = self._get_fd(f"competitions/{liga_id}/matches?dateFrom={d0}&dateTo={d1}&status=SCHEDULED")
        if not data:
            return pd.DataFrame()
        return pd.DataFrame([{
            "fecha":     m.get("utcDate","")[:10],
            "hora":      m.get("utcDate","")[11:16],
            "jornada":   m.get("matchday"),
            "local":     m.get("homeTeam",{}).get("name"),
            "visitante": m.get("awayTeam",{}).get("name"),
        } for m in data.get("matches",[])])

    def resultados_recientes(self, liga_id="PL", cantidad=10) -> pd.DataFrame:
        if not self._key:
            return pd.DataFrame()
        data = self._get_fd(f"competitions/{liga_id}/matches?status=FINISHED&limit={cantidad}")
        if not data:
            return pd.DataFrame()
        filas = []
        for m in data.get("matches",[])[-cantidad:]:
            sc = m.get("score",{}).get("fullTime",{})
            filas.append({
                "fecha":           m.get("utcDate","")[:10],
                "jornada":         m.get("matchday"),
                "local":           m.get("homeTeam",{}).get("name"),
                "visitante":       m.get("awayTeam",{}).get("name"),
                "goles_local":     sc.get("home"),
                "goles_visitante": sc.get("away"),
            })
        return pd.DataFrame(filas)

    def transferencias_recientes(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"Jugador":"Jude Bellingham",    "Origen":"Dortmund",  "Destino":"Real Madrid", "€ M":103,"Tipo":"Traspaso", "Temp.":"23/24"},
            {"Jugador":"Enzo Fernández",     "Origen":"Benfica",   "Destino":"Chelsea",     "€ M":121,"Tipo":"Traspaso", "Temp.":"22/23"},
            {"Jugador":"Moises Caicedo",     "Origen":"Brighton",  "Destino":"Chelsea",     "€ M":116,"Tipo":"Traspaso", "Temp.":"23/24"},
            {"Jugador":"Valentín Carboni",   "Origen":"Inter",     "Destino":"Marseille",   "€ M": 36,"Tipo":"Traspaso", "Temp.":"24/25"},
            {"Jugador":"Alexis Mac Allister","Origen":"Brighton",  "Destino":"Liverpool",   "€ M": 35,"Tipo":"Traspaso", "Temp.":"23/24"},
            {"Jugador":"Facundo Colidio",    "Origen":"Tigre",     "Destino":"Boca Juniors","€ M":  2,"Tipo":"Traspaso", "Temp.":"24/25"},
            {"Jugador":"Nicolás González",   "Origen":"Fiorentina","Destino":"Juventus",    "€ M": 30,"Tipo":"Traspaso", "Temp.":"24/25"},
        ])

    def __del__(self):
        try:
            if hasattr(self,"_conn") and self._conn:
                self._conn.close()
        except Exception:
            pass
