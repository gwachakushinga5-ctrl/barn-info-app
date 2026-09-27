# BarnCure MVP — tobacco barn curing monitor

FastAPI + SQLite (SQLModel) + Jinja + Tailwind CDN + Chart.js. No build step.

## Run now
```powershell
py -m pip install -r requirements.txt
copy .env.example .env   # optional; default ADMIN_TOKEN=admin123
py seed.py               # demo data (safe to re-run)
py -m uvicorn app.main:app --reload --port 8000
```

Open:
- Farmer form: http://127.0.0.1:8000/
- Admin (totals + detections): http://127.0.0.1:8000/admin?token=admin123
- Health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

## API
- `POST /submit` (form) and `POST /api/readings` (JSON) — auto-creates farmer/barn, returns status OK/WATCH/DANGER
- `GET /api/stats?token=admin123` — totals + risk list
- `GET /api/barns`, `GET /api/readings?barn_code=TB-001`

## Detection logic
`app/presets.py` holds per-stage bands; `app/detector.py` scores 0–100.
DANGER ≥60, WATCH ≥25. Overload (`load > capacity`) adds risk.

## Next hooks
- `app/weather.py` stub — re-enable Open-Meteo once locations gain coords.
- Swap SQLite → Postgres by setting `DATABASE_URL`.
