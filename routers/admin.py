from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import hash_password
from routers.deps import require_role
import models
from pydantic import BaseModel, EmailStr

router = APIRouter()

class CreateDoctorIn(BaseModel):
    name: str
    email: EmailStr
    password: str

def booking_out(b: models.Booking):
    return {
        "_id": b.id,
        "date": b.date,
        "timeSlot": b.time_slot,
        "status": b.status,
        "isPaid": b.is_paid,
        "paymentMethod": b.payment_method,
        "fee": b.fee,
        "doctorId": {
            "name": b.doctor.user.name if b.doctor and b.doctor.user else "",
            "email": b.doctor.user.email if b.doctor and b.doctor.user else "",
        },
        "patientId": {
            "name": b.patient.name if b.patient else "",
            "email": b.patient.email if b.patient else "",
        }
    }

# ── Create doctor account ─────────────────────────────────────────────────────
@router.post("/create-doctor")
def create_doctor(
    data: CreateDoctorIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = models.User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role="doctor"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "doctor": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

# ── Get all doctor users ──────────────────────────────────────────────────────
@router.get("/doctors")
def get_all_doctor_users(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    users = db.query(models.User).filter(models.User.role == "doctor").all()
    return [
        {"id": u.id, "name": u.name, "email": u.email}
        for u in users
    ]

# ── Get all bookings ──────────────────────────────────────────────────────────
@router.get("/bookings")
def get_all_bookings(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    bookings = (
        db.query(models.Booking)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    return [booking_out(b) for b in bookings]

# ── Get single booking ────────────────────────────────────────────────────────
@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    b = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    return booking_out(b)

# ── Delete booking ────────────────────────────────────────────────────────────
@router.delete("/bookings/{booking_id}")
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    b = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    db.delete(b)
    db.commit()
    return {"message": "Booking deleted"}