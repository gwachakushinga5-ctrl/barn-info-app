import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, date, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, Query, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from app.db import engine, init_db, get_session
from app.models import Farmer, Barn, Reading
from app.detector import evaluate
from app.presets import STAGES, STAGE_LABELS, PRESETS

load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin123")
BASE = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Tobacco Barn Curing Monitor", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))


def check_admin(token: str = ""):
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token. Use /admin?token=YOUR_TOKEN")


def _today_bounds():
    start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
    return start, datetime.now(timezone.utc)


def _latest_per_barn(session: Session):
    barns = session.exec(select(Barn)).all()
    rows = []
    for b in barns:
        r = session.exec(
            select(Reading).where(Reading.barn_id == b.id).order_by(Reading.taken_at.desc())
        ).first()
        farmer = session.get(Farmer, b.farmer_id) if b.farmer_id else None
        rows.append((b, r, farmer.name if farmer else b.farmer_name))
    # riskiest first
    rows.sort(key=lambda x: (x[1].risk_score if x[1] else -1, x[1].taken_at.replace(tzinfo=None) if x[1] and x[1].taken_at else datetime.min), reverse=True)
    return rows


@app.get("/health")
def health():
    return {"ok": True, "app": "barn-info-app", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/", response_class=HTMLResponse)
def farmer_form(request: Request, ok: str = "", status: str = "", barn: str = ""):
    return templates.TemplateResponse(request, "farmer.html", {
        "stages": STAGES, "labels": STAGE_LABELS,
        "presets": PRESETS, "ok": ok, "status": status, "barn": barn,
    })


@app.post("/submit")
def submit_reading(
    request: Request,
    barn_code: str = Form(...),
    farmer_name: str = Form(...),
    phone: str = Form(""),
    location_text: str = Form(...),
    stage: str = Form(...),
    temp_c: float = Form(...),
    humidity_pct: float = Form(None),
    load_kg: float = Form(None),
    capacity_kg: float = Form(500),
    heat_source: str = Form(""),
    notes: str = Form(""),
):
    if stage not in STAGES:
        raise HTTPException(400, f"Unknown stage {stage}")
    with Session(engine) as s:
        farmer = s.exec(select(Farmer).where(Farmer.name == farmer_name.strip())).first()
        if not farmer:
            farmer = Farmer(name=farmer_name.strip(), phone=phone.strip())
            s.add(farmer)
            s.commit()
            s.refresh(farmer)
        code = barn_code.strip().upper()
        barn = s.exec(select(Barn).where(Barn.barn_code == code)).first()
        if not barn:
            barn = Barn(barn_code=code, farmer_id=farmer.id, farmer_name=farmer.name,
                        location_text=location_text.strip(), capacity_kg=capacity_kg or 500)
            s.add(barn)
            s.commit()
            s.refresh(barn)
        else:
            barn.farmer_id = farmer.id
            barn.farmer_name = farmer.name
            barn.location_text = location_text.strip()
            if capacity_kg:
                barn.capacity_kg = capacity_kg
            s.add(barn)
            s.commit()
        status, reasons, score = evaluate(stage, temp_c, humidity_pct, load_kg, barn.capacity_kg)
        reading = Reading(barn_id=barn.id, stage=stage, temp_c=temp_c,
                          humidity_pct=humidity_pct, load_kg=load_kg,
                          heat_source=heat_source.strip(), notes=notes.strip(),
                          status=status, reasons=" | ".join(reasons), risk_score=score)
        s.add(reading)
        s.commit()
    return RedirectResponse(url=f"/?ok=1&status={status}&barn={code}", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, token: str = Query("")):
    check_admin(token)
    with Session(engine) as s:
        total_barns = s.exec(select(func.count(Barn.id))).one()
        total_farmers = s.exec(select(func.count(Farmer.id))).one()
        total_readings = s.exec(select(func.count(Reading.id))).one()
        start, _ = _today_bounds()
        today_n = s.exec(select(func.count(Reading.id)).where(Reading.taken_at >= start)).one()
        avg_temp = s.exec(select(func.avg(Reading.temp_c)).where(Reading.taken_at >= start)).one()
        rows = _latest_per_barn(s)
        ok = sum(1 for _, r, _ in rows if r and r.status == "OK")
        watch = sum(1 for _, r, _ in rows if r and r.status == "WATCH")
        danger = sum(1 for _, r, _ in rows if r and r.status == "DANGER")
        recent = s.exec(select(Reading).order_by(Reading.taken_at.desc()).limit(30)).all()
        # barn_code lookup for chart
        barn_map = {b.id: b.barn_code for b in s.exec(select(Barn)).all()}
        chart = [{"t": r.taken_at.strftime("%m-%d %H:%M"), "temp": r.temp_c,
                  "barn": barn_map.get(r.barn_id, "?"), "status": r.status}
                 for r in reversed(recent)]
    return templates.TemplateResponse(request, "admin.html", {
        "token": token,
        "totals": {"barns": total_barns, "farmers": total_farmers, "readings": total_readings,
                   "today": today_n, "avg_temp": round(avg_temp, 1) if avg_temp else None,
                   "ok": ok, "watch": watch, "danger": danger},
        "rows": rows, "chart": chart, "labels": STAGE_LABELS, "presets": PRESETS,
    })


@app.get("/api/stats")
def api_stats(token: str = Query("")):
    check_admin(token)
    with Session(engine) as s:
        total_barns = s.exec(select(func.count(Barn.id))).one()
        total_farmers = s.exec(select(func.count(Farmer.id))).one()
        total_readings = s.exec(select(func.count(Reading.id))).one()
        rows = _latest_per_barn(s)
        by_status = {"OK": 0, "WATCH": 0, "DANGER": 0, "NO_DATA": 0}
        risk = []
        for b, r, fname in rows:
            if not r:
                by_status["NO_DATA"] += 1
                continue
            by_status[r.status] = by_status.get(r.status, 0) + 1
            risk.append({"barn_code": b.barn_code, "location": b.location_text,
                         "farmer": fname, "stage": r.stage, "temp_c": r.temp_c,
                         "status": r.status, "risk_score": r.risk_score,
                         "reasons": r.reasons, "taken_at": r.taken_at.isoformat()})
    return {"totals": {"barns": total_barns, "farmers": total_farmers, "readings": total_readings},
            "by_status": by_status, "risk_list": risk}


@app.get("/api/barns")
def api_barns():
    with Session(engine) as s:
        barns = s.exec(select(Barn)).all()
        return [{"barn_code": b.barn_code, "farmer": b.farmer_name, "location": b.location_text,
                 "capacity_kg": b.capacity_kg} for b in barns]


@app.get("/api/readings")
def api_readings(barn_code: str = Query(None), limit: int = 50):
    with Session(engine) as s:
        q = select(Reading).order_by(Reading.taken_at.desc()).limit(limit)
        if barn_code:
            b = s.exec(select(Barn).where(Barn.barn_code == barn_code.strip().upper())).first()
            if not b:
                return []
            q = select(Reading).where(Reading.barn_id == b.id).order_by(Reading.taken_at.desc()).limit(limit)
        rows = s.exec(q).all()
        return [{"id": r.id, "barn_id": r.barn_id, "stage": r.stage, "temp_c": r.temp_c,
                 "humidity_pct": r.humidity_pct, "load_kg": r.load_kg, "status": r.status,
                 "risk_score": r.risk_score, "reasons": r.reasons,
                 "taken_at": r.taken_at.isoformat()} for r in rows]


@app.post("/api/readings")
def api_create_reading(payload: dict):
    """JSON alternative for integrations: {barn_code, farmer_name, location_text, stage, temp_c, ...}"""
    try:
        code = payload["barn_code"].strip().upper()
        stage = payload["stage"]
        temp_c = float(payload["temp_c"])
    except (KeyError, ValueError, AttributeError):
        raise HTTPException(400, "Required: barn_code, stage, temp_c (number)")
    if stage not in STAGES:
        raise HTTPException(400, f"Unknown stage {stage}")
    with Session(engine) as s:
        fname = str(payload.get("farmer_name", "Unknown")).strip()
        farmer = s.exec(select(Farmer).where(Farmer.name == fname)).first()
        if not farmer:
            farmer = Farmer(name=fname, phone=str(payload.get("phone", "")))
            s.add(farmer)
            s.commit()
            s.refresh(farmer)
        barn = s.exec(select(Barn).where(Barn.barn_code == code)).first()
        cap = float(payload.get("capacity_kg") or 500)
        if not barn:
            barn = Barn(barn_code=code, farmer_id=farmer.id, farmer_name=fname,
                        location_text=str(payload.get("location_text", "")), capacity_kg=cap)
            s.add(barn)
            s.commit()
            s.refresh(barn)
        hum = payload.get("humidity_pct")
        load = payload.get("load_kg")
        status, reasons, score = evaluate(stage, temp_c,
                                          float(hum) if hum is not None else None,
                                          float(load) if load is not None else None,
                                          barn.capacity_kg)
        r = Reading(barn_id=barn.id, stage=stage, temp_c=temp_c,
                    humidity_pct=float(hum) if hum is not None else None,
                    load_kg=float(load) if load is not None else None,
                    heat_source=str(payload.get("heat_source", "")),
                    notes=str(payload.get("notes", "")),
                    status=status, reasons=" | ".join(reasons), risk_score=score)
        s.add(r)
        s.commit()
        s.refresh(r)
        return {"id": r.id, "barn_code": code, "status": status,
                "risk_score": score, "reasons": reasons}
