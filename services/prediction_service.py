from pathlib import Path
import re


OUTPUTS_DIR = Path("outputs")
PREDICTION_FILE_PATTERN = re.compile(
    r"^(?P<region>.+)_(?P<date>\d{4}-\d{2}-\d{2})_predicted_full_rgb\.(png|jpg|jpeg)$",
    re.IGNORECASE,
)


def prediction_assets():
    if not OUTPUTS_DIR.exists() or not OUTPUTS_DIR.is_dir():
        return {
            "ok": False,
            "message": "Prediction outputs folder is unavailable.",
            "dates": [],
            "regions": [],
            "items": [],
        }

    items = []
    for file_path in OUTPUTS_DIR.iterdir():
        if not file_path.is_file():
            continue
        match = PREDICTION_FILE_PATTERN.match(file_path.name)
        if not match:
            continue
        items.append(
            {
                "date": match.group("date"),
                "region": match.group("region"),
                "filename": file_path.name,
                "image_url": f"/outputs/{file_path.name}",
            }
        )

    if not items:
        return {
            "ok": False,
            "message": "No prediction outputs were found.",
            "dates": [],
            "regions": [],
            "items": [],
        }

    dates = sorted({item["date"] for item in items})
    regions = sorted({item["region"] for item in items})
    items.sort(key=lambda item: (item["date"], item["region"]))

    return {
        "ok": True,
        "message": "",
        "dates": dates,
        "regions": regions,
        "items": items,
    }
