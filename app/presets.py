"""Acceptable curing bands per stage. Tunable without code changes elsewhere."""

STAGES = ["yellowing", "colour_fixing", "leaf_drying", "stem_drying"]

STAGE_LABELS = {
    "yellowing": "Yellowing",
    "colour_fixing": "Colour fixing",
    "leaf_drying": "Leaf drying",
    "stem_drying": "Stem drying",
}

# temp_ok = ideal band, danger_high/low = burn / under-cure thresholds
PRESETS = {
    "yellowing": {
        "temp_ok": (32.0, 38.0), "danger_high": 40.0, "danger_low": 30.0,
        "hum_ok": (80.0, 90.0),
        "advice": "Keep it gentle. Too hot burns green leaf; too cold stalls yellowing and invites mold.",
    },
    "colour_fixing": {
        "temp_ok": (38.0, 48.0), "danger_high": 50.0, "danger_low": 35.0,
        "hum_ok": (50.0, 70.0),
        "advice": "Fix the colour before driving moisture hard.",
    },
    "leaf_drying": {
        "temp_ok": (48.0, 60.0), "danger_high": 63.0, "danger_low": 42.0,
        "hum_ok": (25.0, 45.0),
        "advice": "Dry the lamina fully before pushing stem temps.",
    },
    "stem_drying": {
        "temp_ok": (60.0, 75.0), "danger_high": 77.0, "danger_low": 55.0,
        "hum_ok": (10.0, 25.0),
        "advice": "Hot enough to dry midribs, but over 77C risks fire/scorch.",
    },
}
