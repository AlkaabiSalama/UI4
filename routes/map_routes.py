from fastapi import APIRouter

from schemas.requests import MapRequest, VideoRequest
from services.map_service import map_config as map_config_service
from services.prediction_service import prediction_assets as prediction_assets_service
from services.video_service import timeseries_video as timeseries_video_service


router = APIRouter()


@router.post("/map-config")
def map_config(req: MapRequest):
    return map_config_service(req)


@router.post("/timeseries-video")
def timeseries_video(req: VideoRequest):
    return timeseries_video_service(req)


@router.get("/prediction-assets")
def prediction_assets():
    return prediction_assets_service()
