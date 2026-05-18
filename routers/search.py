"""
search.py — doctor search with optional geolocation filtering.
Mounted at prefix /api/doctors in main.py  →  GET /api/doctors/search

IMPORTANT: hospital object includes lat & lng so the frontend
           booking modal can render the HospitalMiniMap.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import math, os

from database import get_db
import models

router      = APIRouter()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _haversine(lat1, lng1, lat2, lng2) -> float:
    R    = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a    = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return round(R * 2 * math.asin(math.sqrt(a)), 1)


def _image_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{BACKEND_URL}{path}"


@router.get("/search")
def search_doctors(
    specialization: Optional[str]   = Query(None),
    lat:            Optional[float] = Query(None),
    lng:            Optional[float] = Query(None),
    maxDistanceKm:  Optional[float] = Query(50),
    db:             Session         = Depends(get_db),
):
    q = db.query(models.DoctorProfile)
    if specialization:
        q = q.filter(models.DoctorProfile.specialization == specialization)

    results = []
    for p in q.all():
        dist = None
        if lat is not None and lng is not None:
            if p.hospital and p.hospital.lat and p.hospital.lng:
                dist = _haversine(lat, lng, p.hospital.lat, p.hospital.lng)
                if dist > (maxDistanceKm or 50):
                    continue
            else:
                # No hospital coords — skip distance filter but still include
                pass

        results.append({
            "_id":            p.id,
            "specialization": p.specialization,
            "fee":            p.fee,
            "qualification":  p.qualification,
            "experience":     p.experience_years,
            "bio":            p.bio,
            "distanceKm":     dist,
            "profileImage":   _image_url(p.profile_image),
            # ↓ lat & lng included so frontend HospitalMiniMap can render
            "hospital": {
                "name":    p.hospital.name    if p.hospital else "",
                "address": p.hospital.address if p.hospital else "",
                "lat":     p.hospital.lat     if p.hospital else None,
                "lng":     p.hospital.lng     if p.hospital else None,
            },
            "user": {
                "_id":  p.user_id,
                "name": p.user.name if p.user else "",
            },
        })

    if lat is not None and lng is not None:
        results.sort(key=lambda x: x["distanceKm"] or 9999)

    return {"doctors": results}