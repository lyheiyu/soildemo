# app.py
from __future__ import annotations

import threading
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
from datetime import datetime
from database import (
    init_db,
    get_latest_measurements,
    get_devices,
    get_latest_by_code,
    upsert_template_meta,
    get_template_meta_map,
    get_templates_for_device,
    get_min_code,
    get_last_two_by_code,
    get_latest_ts_by_code
)
from tcp_server import start_tcp_server

app = FastAPI()
templates = Jinja2Templates(directory="templates")


# Temporary mapping: code -> template_id
# Later we can learn this mapping automatically once we confirm the protocol
CODE_TO_TEMPLATE: dict[int, int] = {
    0x0018: 342,  # example: treat code 0x0018 as Soil N for now
}


@app.on_event("startup")
def on_startup() -> None:
    init_db()

    # Insert/Update template meta information
    upsert_template_meta([
        (327, "Air Temperature", "°C", 0.1),
        (328, "Air Humidity", "%RH", 0.1),
        (554, "Air Pressure", "hPa", 0.01),
        (1575, "Illuminance / Optical Rain", "lux", 1.0),
        (555, "CO2", "ppm", 1.0),
        (468, "CO", "ppm", 1.0),
        (466, "SO2", "ppm", 1.0),
        (467, "NO2", "ppm", 1.0),
        (2694, "NH3", "ppm", 0.01),
        (345, "Wind Speed", "m/s", 0.1),
        (656, "Wind Direction", "deg", 1.0),
        (333, "Rainfall", "mm", 0.1),
        (336, "Solar Radiation", "W/m²", 1.0),
        (337, "Soil Temperature", "°C", 0.1),
        (338, "Soil Moisture", "%", 0.1),
        (341, "Soil pH", "pH", 0.01),
        (339, "Soil EC", "uS/cm", 1.0),
        (342, "Soil N", "mg/kg", 1.0),
        (556, "Soil P", "mg/kg", 1.0),
        (344, "Soil K", "mg/kg", 1.0),
    ])

    # Start TCP ingest server in background thread
    t = threading.Thread(target=start_tcp_server, daemon=True)
    t.start()


@app.get("/health")
def health():
    return {"ok": True}


from datetime import datetime

@app.get("/", response_class=HTMLResponse)
def home(request: Request, device_id: str | None = None):
    OFFLINE_AFTER_SECONDS = 600  # >10 min no report -> Offline
    STALE_AFTER_SECONDS = 600    # value unchanged for >=10 min -> Stale
    EPS = 1e-9

    devices = get_devices()
    if device_id is None and devices:
        device_id = devices[0]

    latest_rows = get_latest_measurements(limit=50)

    # Latest row per code (only codes that have ever reported)
    latest_by_code = get_latest_by_code(device_id) if device_id else []
    latest_map = {int(code): (ts, dev, int(code), float(value), flag)
                  for ts, dev, code, value, flag in latest_by_code}

    # For status judgement
    latest_ts_map = get_latest_ts_by_code(device_id) if device_id else {}
    last_two_map = get_last_two_by_code(device_id) if device_id else {}

    # template_id -> {name, unit, scale}
    meta_map = get_template_meta_map()

    # Templates list from 1001 (full sensor list)
    device_templates = get_templates_for_device(device_id) if device_id else []
    base_code = get_min_code(device_id) if device_id else None

    now = datetime.now()

    # Build the full code list so offline sensors are also shown
    if base_code is not None and device_templates:
        code_list = [int(base_code) + i for i in range(len(device_templates))]
    else:
        # fallback: only show codes that exist in DB
        code_list = sorted(latest_map.keys())

    latest_by_code_view = []

    for code in code_list:
        # Map code -> template_id
        template_id = None
        if base_code is not None and device_templates:
            idx = int(code) - int(base_code)
            if 0 <= idx < len(device_templates):
                template_id = device_templates[idx]
        if template_id is None and int(code) in meta_map:
            template_id = int(code)

        meta = meta_map.get(template_id) if template_id else None
        name = meta["name"] if meta else f"code_0x{int(code):04x}"
        unit = meta["unit"] if meta else ""
        scale = meta["scale"] if meta else 1.0

        # value/ts from DB (may be missing)
        row = latest_map.get(int(code))
        if row:
            ts, dev, _, value, flag = row
            value_view = float(value)  # you currently store raw, keep as-is
        else:
            ts, dev, value_view, flag = None, device_id, None, None

        # Status: Offline / Online / Stale
        status = "Offline"
        ts_str = latest_ts_map.get(int(code))
        if ts_str:
            last_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            age = (now - last_dt).total_seconds()

            if age <= OFFLINE_AFTER_SECONDS:
                status = "Online"

                last_two = last_two_map.get(int(code), [])
                if len(last_two) >= 2:
                    ts1, v1 = last_two[0]
                    ts2, v2 = last_two[1]
                    dt2 = datetime.strptime(ts2, "%Y-%m-%d %H:%M:%S")
                    stable_for = (now - dt2).total_seconds()

                    if abs(v1 - v2) <= EPS and stable_for >= STALE_AFTER_SECONDS:
                        status = "Stale"

        latest_by_code_view.append({
            "ts": ts,
            "device_id": dev,
            "code": int(code),
            "template_id": template_id,
            "name": name,
            "unit": unit,
            "scale": scale,
            "value": value_view,
            "flag": flag,
            "status": status,
        })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "devices": devices,
            "device_id": device_id,
            "latest_by_code": latest_by_code_view,
            "latest_rows": latest_rows,
        },
    )