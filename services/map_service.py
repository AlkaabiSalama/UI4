from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import ee
from fastapi import HTTPException
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim

from config import (
    DW_MIN_DATE,
    LOCATION_LAT,
    LOCATION_LON,
    LOCATION_NAME,
    YEARS,
)
from gee_utils import get_dw_tile_urls, tile_url_at_point, tile_url_global_year
from schemas.requests import MapRequest
from services.ee_runtime import init_ee
import services.ee_runtime as ee_runtime


geolocator = Nominatim(user_agent="dw-change-app")
OUTPUTS_DIR = Path("outputs")
PREDICTION_SUFFIX = "_predicted_full_rgb.png"


def parse_iso_date(s: Optional[str]) -> date:
    if not s or not str(s).strip():
        return date.today() - timedelta(days=2)
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return date.today() - timedelta(days=2)


def clamp_map_date(d: date) -> date:
    today = date.today()
    if d < DW_MIN_DATE:
        return DW_MIN_DATE
    if d > today:
        return today
    return d


def display_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def resolve_city(city: Optional[str]):
    if not city or not city.strip():
        return LOCATION_NAME, LOCATION_LAT, LOCATION_LON

    try:
        loc = geolocator.geocode(city.strip())
        if loc:
            return city.strip(), loc.latitude, loc.longitude
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass

    return LOCATION_NAME, LOCATION_LAT, LOCATION_LON


def map_config(req: MapRequest):
    init_ee()
    if not ee_runtime.EE_READY:
        raise HTTPException(
            status_code=500,
            detail=f"Earth Engine is not ready: {ee_runtime.EE_ERROR}",
        )

    mode = req.mode
    da = clamp_map_date(parse_iso_date(req.date_a))
    db = clamp_map_date(parse_iso_date(req.date_b))
    if db < da:
        da, db = db, da

    # Dynamic World uses annual composites (original app): year from each selected date
    year_a = da.year
    year_b = db.year
    if year_a not in YEARS:
        year_a = YEARS[0]
    if year_b not in YEARS:
        year_b = YEARS[-1]

    if mode == "home":
        if not req.city or not str(req.city).strip():
            url = tile_url_global_year(year_a)
            return {
                "city": "World",
                "center_lat": 15.0,
                "center_lon": 0.0,
                "date_a": da.isoformat(),
                "date_b": da.isoformat(),
                "date_a_display": display_date(da),
                "date_b_display": display_date(da),
                "dw_year_a": year_a,
                "dw_year_b": year_a,
                "mode": mode,
                "tiles": {"a": url, "b": None, "change": None},
                "map_zoom": 2,
            }

        city_name, lat, lon = resolve_city(req.city)
        point = ee.Geometry.Point([lon, lat])
        url = tile_url_at_point(point, year_a)
        return {
            "city": city_name,
            "center_lat": lat,
            "center_lon": lon,
            "date_a": da.isoformat(),
            "date_b": da.isoformat(),
            "date_a_display": display_date(da),
            "date_b_display": display_date(da),
            "dw_year_a": year_a,
            "dw_year_b": year_a,
            "mode": mode,
            "tiles": {"a": url, "b": None, "change": None},
            "map_zoom": 11,
        }

    city_name, lat, lon = resolve_city(req.city)
    point = ee.Geometry.Point([lon, lat])
    tiles = get_dw_tile_urls(point, year_a, year_b)

    return {
        "city": city_name,
        "center_lat": lat,
        "center_lon": lon,
        "date_a": da.isoformat(),
        "date_b": db.isoformat(),
        "date_a_display": display_date(da),
        "date_b_display": display_date(db),
        "dw_year_a": year_a,
        "dw_year_b": year_b,
        "mode": mode,
        "tiles": tiles,
    }


def _prediction_records():
    records = []
    if not OUTPUTS_DIR.exists():
        return records

    for path in sorted(OUTPUTS_DIR.glob(f"*{PREDICTION_SUFFIX}")):
        stem = path.name[: -len(PREDICTION_SUFFIX)]
        if "_" not in stem:
            continue
        region, date_part = stem.rsplit("_", 1)
        try:
            date.fromisoformat(date_part)
        except ValueError:
            continue
        records.append(
            {
                "region": region,
                "date": date_part,
                "filename": path.name,
            }
        )
    return records


def prediction_options():
    records = _prediction_records()
    regions = sorted({item["region"] for item in records})
    dates = sorted({item["date"] for item in records})

    options_by_region = {region: [] for region in regions}
    options_by_date = {d: [] for d in dates}
    for item in records:
        options_by_region[item["region"]].append(item["date"])
        options_by_date[item["date"]].append(item["region"])

    for region in options_by_region:
        options_by_region[region] = sorted(options_by_region[region])
    for d in options_by_date:
        options_by_date[d] = sorted(options_by_date[d])

    return {
        "regions": regions,
        "dates": dates,
        "options_by_region": options_by_region,
        "options_by_date": options_by_date,
        "default_region": regions[0] if regions else None,
        "default_date": dates[0] if dates else None,
    }


def prediction_image_path(region: str, prediction_date: str) -> Path:
    if not region or not prediction_date:
        raise HTTPException(status_code=400, detail="Region and date are required.")
    try:
        date.fromisoformat(prediction_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date format.") from exc

    safe_region = Path(region).name
    filename = f"{safe_region}_{prediction_date}{PREDICTION_SUFFIX}"
    image_path = OUTPUTS_DIR / filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Prediction image not found.")
    return image_path
