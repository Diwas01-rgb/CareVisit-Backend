"""
doctor_profile.py — FormData-based CRUD for doctor profiles (admin only).
Mounted at prefix /api/admin in main.py.

Endpoints:
  GET    /api/admin/profiles
  POST   /api/admin/create-profile
  PUT    /api/admin/profiles/{id}
  DELETE /api/admin/profiles/{id}
"""

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import os, shutil, uuid

from database import get_db
from routers.deps import get_current_user, require_role
import models

router = APIRouter()

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "profiles")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_image(file: UploadFile) -> str:
    """Save uploaded image and return the relative URL path."""
    ext      = os.path.splitext(file.filename or "")[-1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path     = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return f"/uploads/profiles/{filename}"


def _image_url(path: Optional[str]) -> Optional[str]:
    """Return an absolute URL for a stored image path."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{BACKEND_URL}{path}"


def _profile_out(p: models.DoctorProfile) -> dict:
    return {
        "id":             p.id,
        "_id":            p.id,
        "specialization": p.specialization,
        "fee":            p.fee,
        "qualification":  p.qualification,
        "experience":     p.experience_years,
        "bio":            p.bio,
        "profileImage":   _image_url(p.profile_image),
        "user": {
            "id":    p.user.id    if p.user else None,
            "_id":   p.user.id    if p.user else None,
            "name":  p.user.name  if p.user else "",
            "email": p.user.email if p.user else "",
        },
        "hospital": {
            "id":      p.hospital.id      if p.hospital else None,
            "_id":     p.hospital.id      if p.hospital else None,
            "name":    p.hospital.name    if p.hospital else "",
            "address": p.hospital.address if p.hospital else "",
        },
    }


# ── GET /api/admin/profiles ────────────────────────────────────────────────
@router.get("/profiles")
def get_all_profiles(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),          # any logged-in user can list profiles
):
    return [_profile_out(p) for p in db.query(models.DoctorProfile).all()]


# ── POST /api/admin/create-profile ────────────────────────────────────────
@router.post("/create-profile")
def create_profile(
    user_id:        int                  = Form(...),
    hospital_id:    int                  = Form(...),
    specialization: str                  = Form(...),
    fee:            int                  = Form(500),
    qualification:  str                  = Form(""),
    experience:     int                  = Form(0),
    bio:            str                  = Form(""),
    profile_image:  Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    if not db.query(models.User).filter(models.User.id == user_id).first():
        raise HTTPException(404, "User not found")
    if not db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first():
        raise HTTPException(404, "Hospital not found")
    if db.query(models.DoctorProfile).filter(models.DoctorProfile.user_id == user_id).first():
        raise HTTPException(400, "Doctor profile already exists for this user")

    image_path = None
    if profile_image and profile_image.filename:
        image_path = _save_image(profile_image)

    profile = models.DoctorProfile(
        user_id          = user_id,
        hospital_id      = hospital_id,
        specialization   = specialization,
        fee              = fee,
        qualification    = qualification,
        experience_years = experience,
        bio              = bio,
        profile_image    = image_path,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"message": "Doctor profile created", "profile": _profile_out(profile)}


# ── PUT /api/admin/profiles/{id} ──────────────────────────────────────────
@router.put("/profiles/{profile_id}")
def update_profile(
    profile_id:     int,
    hospital_id:    Optional[int]        = Form(None),
    specialization: Optional[str]        = Form(None),
    fee:            Optional[int]        = Form(None),
    qualification:  Optional[str]        = Form(None),
    experience:     Optional[int]        = Form(None),
    bio:            Optional[str]        = Form(None),
    profile_image:  Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    p = db.query(models.DoctorProfile).filter(models.DoctorProfile.id == profile_id).first()
    if not p:
        raise HTTPException(404, "Profile not found")

    if hospital_id    is not None: p.hospital_id      = hospital_id
    if specialization is not None: p.specialization   = specialization
    if fee            is not None: p.fee              = fee
    if qualification  is not None: p.qualification    = qualification
    if experience     is not None: p.experience_years = experience
    if bio            is not None: p.bio              = bio

    if profile_image and profile_image.filename:
        p.profile_image = _save_image(profile_image)

    db.commit()
    db.refresh(p)
    return {"message": "Profile updated", "profile": _profile_out(p)}


# ── DELETE /api/admin/profiles/{id} ───────────────────────────────────────
@router.delete("/profiles/{profile_id}")
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    p = db.query(models.DoctorProfile).filter(models.DoctorProfile.id == profile_id).first()
    if not p:
        raise HTTPException(404, "Profile not found")

    # Remove linked schedules and bookings first to avoid FK constraint errors
    db.query(models.Schedule).filter(models.Schedule.doctor_id == profile_id).delete()
    db.query(models.Booking).filter(models.Booking.doctor_id == profile_id).delete()
    db.delete(p)
    db.commit()
    return {"message": "Doctor profile deleted"}