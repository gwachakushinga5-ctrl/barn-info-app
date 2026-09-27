"""Rule-based risk engine: preset bands + overload check -> OK/WATCH/DANGER."""
from app.presets import PRESETS


def evaluate(stage: str, temp_c: float, humidity_pct=None, load_kg=None, capacity_kg=None):
    p = PRESETS.get(stage, PRESETS["yellowing"])
    t_lo, t_hi = p["temp_ok"]
    d_hi, d_lo = p["danger_high"], p["danger_low"]
    reasons: list[str] = []
    score = 0

    if temp_c >= d_hi:
        reasons.append(f"OVERHEAT/BURN RISK: {temp_c:.1f}C at/above {d_hi:.0f}C limit for {stage}")
        score += 85
    elif temp_c > t_hi:
        reasons.append(f"Above ideal ({t_lo:.0f}-{t_hi:.0f}C): {temp_c:.1f}C — watch closely, ease heat")
        score += 40
    elif temp_c <= d_lo:
        reasons.append(f"UNDER-CURE/STALLED: {temp_c:.1f}C at/below {d_lo:.0f}C floor for {stage} (mold risk)")
        score += 70
    elif temp_c < t_lo:
        reasons.append(f"Below ideal ({t_lo:.0f}-{t_hi:.0f}C): {temp_c:.1f}C — curing may stall")
        score += 35

    h = p.get("hum_ok")
    if humidity_pct is not None and h:
        h_lo, h_hi = h
        if humidity_pct > h_hi + 10:
            reasons.append(f"Humidity {humidity_pct:.0f}% far above {h_lo:.0f}-{h_hi:.0f}% band — mold/rot risk")
            score += 30
        elif humidity_pct > h_hi:
            reasons.append(f"Humidity {humidity_pct:.0f}% above {h_hi:.0f}% — ventilate a little")
            score += 15
        elif humidity_pct < h_lo - 10:
            reasons.append(f"Humidity {humidity_pct:.0f}% far below {h_lo:.0f}% — drying too fast, scorch risk")
            score += 30
        elif humidity_pct < h_lo:
            reasons.append(f"Humidity {humidity_pct:.0f}% below {h_lo:.0f}% — check for case-hardening")
            score += 15

    if load_kg is not None and capacity_kg:
        try:
            if float(capacity_kg) > 0 and float(load_kg) > float(capacity_kg):
                reasons.append(f"OVERLOADED: load {load_kg:.0f}kg > capacity {capacity_kg:.0f}kg — uneven cure likely")
                score += 30
        except (TypeError, ValueError):
            pass

    score = max(0, min(100, score))
    status = "DANGER" if score >= 60 else ("WATCH" if score >= 25 else "OK")
    if status == "OK":
        reasons.append("Within acceptable standard — keep steady.")
    return status, reasons, score
