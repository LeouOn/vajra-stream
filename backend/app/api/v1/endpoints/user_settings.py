"""User settings kept server-side: the home location (``/api/v1/settings/location``).

The home location is where a working is sealed unless it names its own place,
so its witness shows the sky from there (core/home_location.py, core/sky.py).

* ``GET``    the stored location (or ``null``) and the configured default.
* ``PUT``    set it from coordinates (``source`` ``"browser"`` or ``"typed"``)
  or from a typed ``place`` name, geocoded with the shared GeocodingService
  (``source`` ``"geocoded"``; the label is the name as typed, not the full
  geocoder address).
* ``DELETE`` forget it.
"""

from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from config.settings import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from core import home_location

router = APIRouter()


class HomeLocationRequest(BaseModel):
    """Coordinates (with an optional label), or a ``place`` name to geocode."""

    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    label: str | None = Field(default=None, max_length=home_location.LABEL_MAX_CHARS)
    place: str | None = Field(default=None, max_length=200, description="A place name to geocode")
    source: Literal["browser", "typed"] | None = None

    @model_validator(mode="after")
    def _coordinates_or_place(self) -> HomeLocationRequest:
        has_lat, has_lon = self.latitude is not None, self.longitude is not None
        if has_lat != has_lon:
            raise ValueError("give both latitude and longitude")
        if not has_lat and not (self.place and self.place.strip()):
            raise ValueError("give latitude and longitude, or a place name")
        return self


def _response(location: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "location": location,
        "default": {"latitude": DEFAULT_LATITUDE, "longitude": DEFAULT_LONGITUDE},
        "display": home_location.describe(location) if location else None,
    }


@router.get("/location", summary="The home location workings are sealed at")
async def get_location() -> dict[str, Any]:
    return _response(home_location.get_home_location())


@router.put("/location", summary="Set the home location (coordinates or a place name)")
async def put_location(request: HomeLocationRequest) -> dict[str, Any]:
    if request.latitude is not None and request.longitude is not None:
        raw: dict[str, Any] = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "label": request.label,
            "source": request.source or "typed",
        }
    else:
        place = " ".join((request.place or "").split())
        # Function-level: the geocoder pulls in geopy lazily; tests stub this singleton.
        from backend.core.services.geocoding_service import geocoding_service

        found = await asyncio.to_thread(geocoding_service.get_coordinates_and_timezone, place)
        if not isinstance(found, dict) or found.get("error") or found.get("latitude") is None:
            raise HTTPException(status_code=400, detail=f"could not find a place called {place!r}")
        raw = {
            "latitude": found["latitude"],
            "longitude": found["longitude"],
            "label": request.label or place,
            "source": "geocoded",
        }
    try:
        stored = home_location.set_home_location(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"could not save the home location: {exc}") from None
    return _response(stored)


@router.delete("/location", summary="Forget the home location")
async def delete_location() -> dict[str, Any]:
    cleared = home_location.clear_home_location()
    return {**_response(None), "cleared": cleared}
