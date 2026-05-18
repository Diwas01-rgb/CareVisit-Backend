"""
history.py — patient triage history.
Mounted at prefix /api/patient in main.py.

Endpoints:
  GET /api/patient/history/my
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json

from database import get_db
from routers.deps import get_current_user
import models

router = APIRouter()


@router.get("/history/my")
def my_history(
    db:   Session     = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    records = (
        db.query(models.TriageHistory)
        .filter(models.TriageHistory.patient_id == user.id)
        .order_by(models.TriageHistory.created_at.desc())
        .all()
    )
    return [
        {
            "_id":            r.id,
            "symptoms":       json.loads(r.symptoms)   if r.symptoms   else [],
            "specialization": r.specialization,
            "priority":       r.priority,
            "confidence":     r.confidence,
            "allScores":      json.loads(r.all_scores) if r.all_scores else {},
            "createdAt":      r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]