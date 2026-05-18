from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import get_current_user, require_role
import models, os

router = APIRouter()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

def image_url(path: str | None) -> str | None:
    """Convert a stored relative path like /uploads/profiles/abc.jpg to a full URL."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{BACKEND_URL}{path}"


# ── Patient dashboard  →  GET /api/patient/dashboard ──────────────────────
@router.get("/patient/dashboard")
def patient_dashboard(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    bookings = (
        db.query(models.Booking)
        .filter(models.Booking.patient_id == user.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    upcoming = [b for b in bookings if b.status in ("pending", "confirmed")]

    def out(b):
        return {
            "_id":      b.id,
            "date":     b.date,
            "timeSlot": b.time_slot,
            "status":   b.status,
            "isPaid":   b.is_paid,
            "fee":      b.fee,
            "doctorId": {
                "name": b.doctor.user.name if b.doctor and b.doctor.user else "",
            },
        }

    return {
        "stats": {
            "total":     len(bookings),
            "pending":   sum(1 for b in bookings if b.status == "pending"),
            "confirmed": sum(1 for b in bookings if b.status == "confirmed"),
            "cancelled": sum(1 for b in bookings if b.status == "cancelled"),
        },
        "upcoming": [out(b) for b in upcoming[:5]],
    }


# ── Doctor dashboard  →  GET /api/doctor/dashboard ────────────────────────
@router.get("/doctor/dashboard")
def doctor_dashboard(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    profile = (
        db.query(models.DoctorProfile)
        .filter(models.DoctorProfile.user_id == user.id)
        .first()
    )
    bookings = []
    if profile:
        bookings = (
            db.query(models.Booking)
            .filter(models.Booking.doctor_id == profile.id)
            .order_by(models.Booking.created_at.desc())
            .all()
        )

    upcoming = [b for b in bookings if b.status in ("pending", "confirmed")]
    paid     = [b for b in bookings if b.is_paid]

    def out(b):
        return {
            "_id":       b.id,
            "date":      b.date,
            "timeSlot":  b.time_slot,
            "status":    b.status,
            "isPaid":    b.is_paid,
            "fee":       b.fee,
            "patientId": {
                "name":  b.patient.name  if b.patient else "",
                "email": b.patient.email if b.patient else "",
            },
        }

    return {
        "stats": {
            "total":      len(bookings),
            "pending":    sum(1 for b in bookings if b.status == "pending"),
            "confirmed":  sum(1 for b in bookings if b.status == "confirmed"),
            "cancelled":  sum(1 for b in bookings if b.status == "cancelled"),
            "totalEarned": sum(b.fee for b in paid),
        },
        "upcoming": [out(b) for b in upcoming[:5]],
        "profile": {
            "specialization": profile.specialization if profile else "",
            "fee":            profile.fee            if profile else 0,
            "hospital":       profile.hospital.name  if profile and profile.hospital else "",
            "profileImage":   image_url(profile.profile_image) if profile else None,
        },
    }


# ── Admin dashboard  →  GET /api/admin/dashboard ──────────────────────────
@router.get("/admin/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    bookings = (
        db.query(models.Booking)
        .order_by(models.Booking.created_at.desc())
        .all()
    )
    paid = [b for b in bookings if b.is_paid]

    recent = bookings[:10]

    def booking_out(b):
        return {
            "_id":       b.id,
            "date":      b.date,
            "timeSlot":  b.time_slot,
            "status":    b.status,
            "isPaid":    b.is_paid,
            "fee":       b.fee,
            "patientId": {"name": b.patient.name  if b.patient else ""},
            "doctorId":  {"name": b.doctor.user.name if b.doctor and b.doctor.user else ""},
        }

    return {
        "stats": {
            "totalPatients":     db.query(models.User).filter(models.User.role == "patient").count(),
            "totalDoctors":      db.query(models.User).filter(models.User.role == "doctor").count(),
            "totalHospitals":    db.query(models.Hospital).count(),
            "totalRevenueNPR":   sum(b.fee for b in paid),
            "pendingBookings":   sum(1 for b in bookings if b.status == "pending"),
            "confirmedBookings": sum(1 for b in bookings if b.status == "confirmed"),
            "cancelledBookings": sum(1 for b in bookings if b.status == "cancelled"),
        },
        "recentBookings": [booking_out(b) for b in recent],
    }