"""
booking.py — patient and doctor booking management.
Mounted at prefix /api/bookings in main.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os

from database import get_db
from routers.deps import get_current_user
import models

router      = APIRouter()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _image_url(path):
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{BACKEND_URL}{path}"


def _booking_out(b: models.Booking) -> dict:
    return {
        "_id":           b.id,
        "date":          b.date,
        "timeSlot":      b.time_slot,
        "status":        b.status,
        "isPaid":        b.is_paid,
        "paymentMethod": b.payment_method,
        "fee":           b.fee,
        "doctorId": {
            "name":         b.doctor.user.name  if b.doctor and b.doctor.user else "",
            "email":        b.doctor.user.email if b.doctor and b.doctor.user else "",
            "specialization": b.doctor.specialization if b.doctor else "",
            "profileImage": _image_url(b.doctor.profile_image) if b.doctor else None,
        },
        "patientId": {
            "name":  b.patient.name  if b.patient else "",
            "email": b.patient.email if b.patient else "",
        },
    }


class BookingIn(BaseModel):
    doctorId:   int
    scheduleId: int = 0
    date:       str
    timeSlot:   str


# ── POST /api/bookings/create ──────────────────────────────────────────────
@router.post("/create")
def create_booking(
    data: BookingIn,
    db:   Session    = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    profile = db.query(models.DoctorProfile).filter(
        models.DoctorProfile.id == data.doctorId
    ).first()
    if not profile:
        raise HTTPException(404, "Doctor not found")

    b = models.Booking(
        patient_id = user.id,
        doctor_id  = profile.id,
        date       = data.date,
        time_slot  = data.timeSlot,
        fee        = profile.fee,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"booking": _booking_out(b)}


# ── GET /api/bookings/me ───────────────────────────────────────────────────
@router.get("/me")
def my_bookings(
    db:   Session    = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.patient_id == user.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    return [_booking_out(b) for b in bookings]


# ── GET /api/bookings/doctor ───────────────────────────────────────────────
@router.get("/doctor")
def doctor_bookings(
    db:   Session    = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    profile = db.query(models.DoctorProfile).filter(
        models.DoctorProfile.user_id == user.id
    ).first()
    if not profile:
        return []
    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.doctor_id == profile.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    return [_booking_out(b) for b in bookings]


# ── PATCH /api/bookings/{id}/status ───────────────────────────────────────
@router.patch("/{booking_id}/status")
def update_status(
    booking_id: int,
    data:       dict,
    db:         Session    = Depends(get_db),
    user:       models.User = Depends(get_current_user),
):
    b = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not b:
        raise HTTPException(404, "Booking not found")

    new_status = data.get("status")
    if new_status == "confirmed" and not b.is_paid:
        raise HTTPException(402, "Patient has not paid yet. Cannot confirm an unpaid booking.")

    b.status = new_status
    db.commit()
    return {"message": f"Booking status updated to {new_status}"}