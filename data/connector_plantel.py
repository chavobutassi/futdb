"""
connector_plantel.py
====================
Conector Supabase (PostgreSQL) — Plantel de rendimiento deportivo.
Reemplaza la versión Google Sheets anterior.

Configuración en .env:
    SUPABASE_URL = https://lmsfttuoolndstpqxmbk.supabase.co
    SUPABASE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Instalación:
    pip install supabase

Fallback automático a datos demo si no hay credenciales.
"""

import os
import logging
import random
from datetime import date, timedelta

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("connector_plantel")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lmsfttuoolndstpqxmbk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxtc2Z0dHVvb2xuZHN0cHF4bWJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA4NzA0NTIsImV4cCI6MjA5NjQ0NjQ1Mn0.9QNskG9ySoQAQ7K8zzxX1zTmLvIHlYZsI5g8nYYfe9c")

# Intentar importar supabase-py
try:
    from supabase import create_client, Client
    _SUPABASE_LIB_OK = True
except ImportError:
    _SUPABASE_LIB_OK = False
    log.warning("[Plantel] supabase no instalado — ejecutá: pip install supabase")


# Mapeo columnas DB → nombres de display para DataFrames
_COLS_JUGADORES = {
    "id_jugador": "ID_JUGADOR", "apellido": "APELLIDO", "nombre": "NOMBRE",
    "numero_camiseta": "NÚMERO CAMISETA", "posicion": "POSICIÓN",
    "fecha_nacim": "FECHA NACIM.", "edad": "EDAD",
    "peso_inicial_kg": "PESO INICIAL (kg)", "altura_cm": "ALTURA (cm)",
    "estado": "ESTADO",
}
_COLS_FISICO = {
    "id_sesion": "ID_SESION", "id_jugador": "ID_JUGADOR",
    "fecha": "FECHA", "peso_kg": "PESO (kg)",
    "km_recorridos": "KM RECORRIDOS", "kcal_quemadas": "KCAL QUEMADAS",
    "fc_maxima_bpm": "FC MÁXIMA (bpm)", "fc_promedio_bpm": "FC PROMEDIO (bpm)",
    "vel_max_kmh": "VEL. MÁX (km/h)", "sprints_25kmh": "SPRINTS >25km/h",
    "tiempo_activo_min": "TIEMPO ACTIVO (min)", "indice_carga": "ÍNDICE CARGA",
    "observaciones": "OBSERVACIONES",
}
_COLS_TECNICO = {
    "id_sesion": "ID_SESION", "id_jugador": "ID_JUGADOR",
    "fecha": "FECHA", "tipo_sesion": "TIPO SESIÓN",
    "pases_intentados": "PASES INTENT.", "pases_completados": "PASES COMPLET.",
    "pct_pases": "% PASES (auto)", "recuperaciones": "RECUP. PELOTA",
    "perdidas_pelota": "PÉRD. PELOTA", "duelos_ganados": "DUELOS GANADOS",
    "duelos_totales": "DUELOS TOTALES", "pct_duelos": "% DUELOS (auto)",
    "remates_arco": "REMATES AL ARCO", "goles": "GOLES",
    "km_con_pelota": "KM CON PELOTA", "minutos_jugados": "MINUTOS JUGADOS",
}


class ConectorPlantel:
    """
    Lee y escribe datos del plantel en Supabase.
    Si no hay conexión disponible, usa datos demo automáticamente.
    """

    def __init__(self):
        self._client: "Client | None" = None
        self._connected = False
        self._try_connect()

    def _try_connect(self):
        if not _SUPABASE_LIB_OK:
            log.warning("[Plantel] Librería supabase no disponible → modo demo")
            return
        if not SUPABASE_URL or not SUPABASE_KEY:
            log.warning("[Plantel] SUPABASE_URL / SUPABASE_KEY no definidos → modo demo")
            return
        try:
            self._client = create_client(SUPABASE_URL, SUPABASE_KEY)
            # Verificar conexión con una consulta mínima
            self._client.table("jugadores").select("id_jugador").execute()
            self._connected = True
            log.info("[Plantel] Conectado a Supabase ✓")
        except Exception as e:
            log.error(f"[Plantel] Error de conexión: {e} → modo demo")

    @property
    def modo(self) -> str:
        return "Supabase (PostgreSQL)" if self._connected else "Demo (sin conexión)"

    # ── Lectura ───────────────────────────────────────────────────────────────

    def jugadores(self) -> pd.DataFrame:
        if self._connected:
            try:
                res = self._client.table("jugadores").select("*").order("apellido").execute()
                df = pd.DataFrame(res.data)
                return df.rename(columns=_COLS_JUGADORES) if not df.empty else df
            except Exception as e:
                log.error(f"[Plantel] jugadores(): {e}")
        return _demo_jugadores()

    def sesiones_fisico(self, id_jugador: str = None) -> pd.DataFrame:
        if self._connected:
            try:
                q = self._client.table("sesiones_fisico").select("*").order("fecha")
                if id_jugador:
                    q = q.eq("id_jugador", id_jugador)
                res = q.execute()
                df = pd.DataFrame(res.data)
                return df.rename(columns=_COLS_FISICO) if not df.empty else df
            except Exception as e:
                log.error(f"[Plantel] sesiones_fisico(): {e}")
        df = _demo_fisico()
        return df[df["ID_JUGADOR"] == id_jugador] if id_jugador else df

    def sesiones_tecnico(self, id_jugador: str = None) -> pd.DataFrame:
        if self._connected:
            try:
                q = self._client.table("sesiones_tecnico").select("*").order("fecha")
                if id_jugador:
                    q = q.eq("id_jugador", id_jugador)
                res = q.execute()
                df = pd.DataFrame(res.data)
                return df.rename(columns=_COLS_TECNICO) if not df.empty else df
            except Exception as e:
                log.error(f"[Plantel] sesiones_tecnico(): {e}")
        df = _demo_tecnico()
        return df[df["ID_JUGADOR"] == id_jugador] if id_jugador else df

    # ── Escritura ─────────────────────────────────────────────────────────────

    def insertar_jugador(self, datos: dict) -> bool:
        """
        datos = {
            "id_jugador": "J009", "apellido": "Pérez", "nombre": "Carlos",
            "numero_camiseta": 14, "posicion": "Delantero", ...
        }
        """
        if not self._connected:
            log.warning("[Plantel] Sin conexión — no se puede insertar")
            return False
        try:
            self._client.table("jugadores").insert(datos).execute()
            return True
        except Exception as e:
            log.error(f"[Plantel] insertar_jugador(): {e}")
            return False

    def insertar_sesion_fisico(self, datos: dict) -> bool:
        """
        datos = {
            "id_sesion": "SF0050", "id_jugador": "J001", "fecha": "2026-06-07",
            "peso_kg": 72.3, "km_recorridos": 9.1, "kcal_quemadas": 720,
            "fc_maxima_bpm": 188, "fc_promedio_bpm": 152,
            "vel_max_kmh": 32.4, "sprints_25kmh": 14, "tiempo_activo_min": 75
        }
        Nota: indice_carga se calcula automáticamente en la DB (columna GENERATED).
        """
        if not self._connected:
            log.warning("[Plantel] Sin conexión — no se puede insertar")
            return False
        try:
            self._client.table("sesiones_fisico").insert(datos).execute()
            return True
        except Exception as e:
            log.error(f"[Plantel] insertar_sesion_fisico(): {e}")
            return False

    def insertar_sesion_tecnico(self, datos: dict) -> bool:
        """
        datos = {
            "id_sesion": "ST0050", "id_jugador": "J001", "fecha": "2026-06-07",
            "tipo_sesion": "Entrenamiento",
            "pases_intentados": 48, "pases_completados": 40,
            "recuperaciones": 7, "perdidas_pelota": 3,
            "duelos_ganados": 9, "duelos_totales": 13,
            "remates_arco": 2, "goles": 1,
            "km_con_pelota": 1.9, "minutos_jugados": 90
        }
        Nota: pct_pases y pct_duelos se calculan automáticamente en la DB.
        """
        if not self._connected:
            log.warning("[Plantel] Sin conexión — no se puede insertar")
            return False
        try:
            self._client.table("sesiones_tecnico").insert(datos).execute()
            return True
        except Exception as e:
            log.error(f"[Plantel] insertar_sesion_tecnico(): {e}")
            return False

    def actualizar_estado_jugador(self, id_jugador: str, nuevo_estado: str) -> bool:
        """Cambia el estado de un jugador (Activo/Lesionado/Suspendido/Baja)."""
        if not self._connected:
            return False
        try:
            self._client.table("jugadores").update({"estado": nuevo_estado}).eq("id_jugador", id_jugador).execute()
            return True
        except Exception as e:
            log.error(f"[Plantel] actualizar_estado(): {e}")
            return False


# ── Datos demo (fallback sin conexión) ───────────────────────────────────────

_JUGADORES_BASE = [
    ("J001","Ramírez",   "Lucas",     10,"Mediocampista","2002-03-15",24,72.0,176,"Activo"),
    ("J002","Vera",      "Tomás",      9,"Delantero",    "2004-07-22",21,75.5,181,"Activo"),
    ("J003","Díaz",      "Sebastián",  4,"Defensor",     "1999-11-05",26,80.2,183,"Activo"),
    ("J004","Sosa",      "Mateo",      1,"Portero",      "1997-04-18",29,83.0,187,"Activo"),
    ("J005","González",  "Franco",     7,"Mediocampista","2003-09-30",22,70.8,174,"Activo"),
    ("J006","López",     "Agustín",    6,"Defensor",     "2001-12-10",24,78.0,180,"Lesionado"),
    ("J007","Martínez",  "Rodrigo",   11,"Delantero",    "2005-01-25",20,68.5,172,"Activo"),
    ("J008","Fernández", "Pablo",      5,"Defensor",     "2000-06-14",25,82.0,185,"Activo"),
]

def _demo_jugadores() -> pd.DataFrame:
    cols = ["ID_JUGADOR","APELLIDO","NOMBRE","NÚMERO CAMISETA","POSICIÓN",
            "FECHA NACIM.","EDAD","PESO INICIAL (kg)","ALTURA (cm)","ESTADO"]
    return pd.DataFrame(_JUGADORES_BASE, columns=cols)

def _demo_fisico() -> pd.DataFrame:
    random.seed(42)
    rows = []
    base = date(2026, 4, 1)
    for i, j in enumerate(_JUGADORES_BASE):
        for w in range(8):
            d = base + timedelta(weeks=w)
            rows.append({
                "ID_SESION": f"SF{i*8+w+1:04d}", "ID_JUGADOR": j[0],
                "FECHA": d.isoformat(),
                "PESO (kg)":        round(j[7] - w*0.12 + random.uniform(-0.1,0.15), 1),
                "KM RECORRIDOS":    round(6.5 + random.uniform(0, 4), 1),
                "KCAL QUEMADAS":    random.randint(560, 840),
                "FC MÁXIMA (bpm)":  random.randint(172, 196),
                "FC PROMEDIO (bpm)":random.randint(135, 162),
                "VEL. MÁX (km/h)":  round(26 + random.uniform(0, 8), 1),
                "SPRINTS >25km/h":  random.randint(6, 20),
                "TIEMPO ACTIVO (min)": random.randint(50, 90),
            })
    return pd.DataFrame(rows)

def _demo_tecnico() -> pd.DataFrame:
    random.seed(7)
    tipos = ["Entrenamiento","Partido amistoso","Partido oficial"]
    rows = []
    base = date(2026, 4, 1)
    for i, j in enumerate(_JUGADORES_BASE):
        for w in range(8):
            d = base + timedelta(weeks=w)
            pi = random.randint(32, 62)
            pc = random.randint(int(pi*0.62), pi)
            dw = random.randint(4, 13)
            dt = dw + random.randint(2, 7)
            rows.append({
                "ID_SESION": f"ST{i*8+w+1:04d}", "ID_JUGADOR": j[0],
                "FECHA": d.isoformat(), "TIPO SESIÓN": random.choice(tipos),
                "PASES INTENT.": pi, "PASES COMPLET.": pc,
                "% PASES (auto)": round(pc/pi*100, 1),
                "RECUP. PELOTA": random.randint(2, 11),
                "PÉRD. PELOTA":  random.randint(1, 8),
                "DUELOS GANADOS": dw, "DUELOS TOTALES": dt,
                "% DUELOS (auto)": round(dw/dt*100, 1),
                "REMATES AL ARCO": random.randint(0, 5),
                "GOLES": random.randint(0, 2),
                "KM CON PELOTA": round(0.7 + random.uniform(0, 1.8), 1),
            })
    return pd.DataFrame(rows)
