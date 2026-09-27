"""Weather hook (stub for v1). Plug Open-Meteo back in once locations have coords."""
# Kept intentionally minimal: v1 uses free-text location, so no auto weather lookup.
# Future: map location_text -> (lat, lon), cache 30 min, call:
#   https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&current=temperature_2m,relative_humidity_2m


def ambient_risk_stub():
    return {"enabled": False, "note": "Weather risk disabled in v1 (free-text location)."}
