from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import get_current_user
import models, json, math, os
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Symptom scoring table ──────────────────────────────────────────────────
SCORES = {
    "chest_pain":          {"cardiology": 5, "general": 2},
    "shortness_breath":    {"cardiology": 4, "general": 2},
    "palpitations":        {"cardiology": 3},
    "fatigue":             {"cardiology": 1, "general": 2},
    "headache":            {"neurology": 2, "general": 1},
    "migraine":            {"neurology": 4},
    "numbness":            {"neurology": 3},
    "balance_issue":       {"neurology": 3},
    "memory_loss":         {"neurology": 2},
    "seizure":             {"neurology": 5},
    "knee_pain":           {"orthopedics": 4},
    "joint_swelling":      {"orthopedics": 3},
    "injury_history":      {"orthopedics": 3},
    "difficulty_walking":  {"orthopedics": 4},
    "back_pain":           {"orthopedics": 2},
    "stiffness_morning":   {"orthopedics": 2},
    "skin_rash":           {"dermatology": 4},
    "itching":             {"dermatology": 3},
    "acne":                {"dermatology": 2},
    "fever":               {"general": 3},
    "cold":                {"general": 2},
}

EMERGENCY_SYMPTOMS = {"chest_pain", "seizure"}


def haversine(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return round(R * 2 * math.asin(math.sqrt(a)), 1)


class TriageIn(BaseModel):
    answers:        List[str]
    location:       Optional[dict]       = None
    age:            Optional[int]        = None
    severity:       Optional[str]        = "mild"
    duration:       Optional[int]        = None
    medicalHistory: Optional[List[str]]  = []


# Route: POST /api/triage  (main.py mounts this router at prefix="/api")
@router.post("/triage")
def run_triage(
    data: TriageIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    totals = {k: 0 for k in ["cardiology", "neurology", "orthopedics", "dermatology", "general"]}

    for sym in data.answers:
        for dept, pts in SCORES.get(sym, {}).items():
            totals[dept] = totals.get(dept, 0) + pts

    mult = {"mild": 1.0, "moderate": 1.2, "severe": 1.5, "emergency": 2.0}.get(data.severity, 1.0)
    totals = {k: round(v * mult) for k, v in totals.items()}

    best_dept   = max(totals, key=lambda k: totals[k])
    best_score  = totals[best_dept]
    total_score = sum(totals.values()) or 1
    confidence  = f"{round((best_score / total_score) * 100)}% match"

    is_emergency = any(s in EMERGENCY_SYMPTOMS for s in data.answers) and data.severity == "emergency"

    if is_emergency:
        priority = "emergency"
    elif best_score >= 8:
        priority = "high"
    elif best_score >= 4:
        priority = "medium"
    else:
        priority = "low"

    lat = data.location.get("lat", 26.6649) if data.location else 26.6649
    lng = data.location.get("lng", 87.2798) if data.location else 87.2798

    profiles = (
        db.query(models.DoctorProfile)
        .filter(models.DoctorProfile.specialization == best_dept)
        .all()
    )

    nearby_doctors = []
    for p in profiles:
        if p.hospital and p.hospital.lat and p.hospital.lng:
            dist = haversine(lat, lng, p.hospital.lat, p.hospital.lng)
            if dist <= 50:
                # Build absolute image URL
                img = p.profile_image
                if img and not img.startswith("http"):
                    img = f"{BACKEND_URL}{img}"

                nearby_doctors.append({
                    "_id":            p.id,
                    "specialization": p.specialization,
                    "fee":            p.fee,
                    "distanceKm":     dist,
                    "profileImage":   img,
                    "hospital": {
                        "name":    p.hospital.name,
                        "address": p.hospital.address,
                        "lat":     p.hospital.lat,
                        "lng":     p.hospital.lng,
                    },
                    "user": {
                        "_id":  p.user_id,
                        "name": p.user.name if p.user else "",
                    },
                })

    nearby_doctors.sort(key=lambda x: x["distanceKm"])

    # Save triage history
    history = models.TriageHistory(
        patient_id=user.id,
        symptoms=json.dumps(data.answers),
        specialization=best_dept,
        priority=priority,
        confidence=confidence,
        all_scores=json.dumps(totals),
    )
    db.add(history)
    db.commit()

    return {
        "specialization":    best_dept,
        "priority":          priority,
        "confidence":        confidence,
        "allScores":         totals,
        "isEmergency":       is_emergency,
        "emergencyMessage":  "EMERGENCY: Seek immediate medical care NOW." if is_emergency else None,
        "doctors":           nearby_doctors,
        "doctorsFound":      len(nearby_doctors),
        "topDiseases":       [],
    }