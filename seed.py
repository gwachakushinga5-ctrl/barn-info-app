"""Seed demo barns + readings so admin dashboard shows totals immediately."""
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from app.db import engine, init_db
from app.models import Farmer, Barn, Reading
from app.detector import evaluate

init_db()

farmers = [("T. Moyo", "0711000001"), ("R. Sibanda", "0711000002"), ("K. Dube", "0711000003")]
barns = [
    ("TB-001", "T. Moyo", "Marondera Block C", 500),
    ("TB-002", "T. Moyo", "Marondera Block C", 500),
    ("TB-003", "R. Sibanda", "Rusape West", 600),
    ("TB-004", "K. Dube", "Karoi Central", 450),
    ("TB-005", "K. Dube", "Karoi Central", 450),
]
readings = [
    # (barn, stage, temp, hum, load, hours_ago)
    ("TB-001", "yellowing", 35.5, 85, 420, 1),
    ("TB-002", "leaf_drying", 64.0, 30, 520, 1),   # DANGER burn + overload
    ("TB-003", "stem_drying", 70.0, 18, 500, 2),   # OK
    ("TB-004", "colour_fixing", 33.0, 75, 300, 3), # WATCH low/stalled
    ("TB-005", "yellowing", 41.5, 88, 400, 2),     # DANGER overheat
    ("TB-001", "yellowing", 34.0, 84, 410, 5),
    ("TB-003", "leaf_drying", 55.0, 35, 490, 6),
]

with Session(engine) as s:
    if s.exec(select(Barn)).first():
        print("DB already seeded, skipping.")
        raise SystemExit(0)
    fmap = {}
    for name, phone in farmers:
        f = Farmer(name=name, phone=phone)
        s.add(f)
        s.commit()
        s.refresh(f)
        fmap[name] = f
    bmap = {}
    for code, fname, loc, cap in barns:
        b = Barn(barn_code=code, farmer_id=fmap[fname].id, farmer_name=fname,
                 location_text=loc, capacity_kg=cap)
        s.add(b)
        s.commit()
        s.refresh(b)
        bmap[code] = b
    now = datetime.now(timezone.utc)
    for code, stage, temp, hum, load, ago in readings:
        b = bmap[code]
        status, reasons, score = evaluate(stage, temp, hum, load, b.capacity_kg)
        s.add(Reading(barn_id=b.id, stage=stage, temp_c=temp, humidity_pct=hum,
                      load_kg=load, heat_source="coal", notes="seeded",
                      status=status, reasons=" | ".join(reasons), risk_score=score,
                      taken_at=now - timedelta(hours=ago)))
    s.commit()
    print("Seeded 3 farmers, 5 barns, 7 readings.")
