"""Correr con: python diag2.py"""
import requests

HDR = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
s = requests.Session()
s.headers.update(HDR)

print("=== Buscando Liga Argentina en TheSportsDB ===\n")

# 1. Buscar todas las ligas de Argentina
r = s.get("https://www.thesportsdb.com/api/v1/json/1/search_all_leagues.php",
          params={"c": "Argentina", "s": "Soccer"}, timeout=10)
print(f"Status búsqueda: {r.status_code}")
ligas = r.json().get("countrys") or []
for l in ligas:
    print(f"  id={l.get('idLeague')}  nombre={l.get('strLeague')}")

print("\n=== Probando eventsseason con distintos IDs y temporadas ===\n")

# IDs candidatos y temporadas a probar
tests = [
    ("4406", "2024-2025"),
    ("4406", "2024"),
    ("4406", "2025"),
    ("4398", "2024-2025"),  # otro posible ID
    ("4399", "2024-2025"),
]

for lid, temp in tests:
    r = s.get("https://www.thesportsdb.com/api/v1/json/1/eventsseason.php",
              params={"id": lid, "s": temp}, timeout=10)
    ev = (r.json().get("events") or []) if r.status_code == 200 else []
    status = f"{len(ev)} eventos" if ev else f"vacío (HTTP {r.status_code})"
    print(f"  id={lid}  temporada={temp}  →  {status}")
    if ev:
        print(f"    Ejemplo: {ev[0].get('strHomeTeam')} vs {ev[0].get('strAwayTeam')}  fecha={ev[0].get('dateEvent')}")
        break
