from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from schemas.requests import MapRequest, VideoRequest
from services.map_service import map_config as map_config_service
from services.map_service import prediction_image_path, prediction_options
from services.video_service import timeseries_video as timeseries_video_service


router = APIRouter()


@router.post("/map-config")
def map_config(req: MapRequest):
    return map_config_service(req)


@router.post("/timeseries-video")
def timeseries_video(req: VideoRequest):
    return timeseries_video_service(req)


@router.get("/prediction-options")
def get_prediction_options():
    return prediction_options()


@router.get("/prediction-image")
def get_prediction_image(region: str = Query(...), date: str = Query(...)):
    path = prediction_image_path(region, date)
    return FileResponse(path)
