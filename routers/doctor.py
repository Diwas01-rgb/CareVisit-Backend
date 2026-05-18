from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import require_role, get_current_user
import models
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class DoctorProfileIn(BaseModel):
    user_id: int
    hospital_id: int
    specialization: str
    fee: Optional[int] = 500

class DoctorProfileUpdate(BaseModel):
    hospital_id: int
    specialization: str
    fee: Optional[int] = 500

def profile_out(p: models.DoctorProfile):
    return {
        "id": p.id,
        "specialization": p.specialization,
        "fee": p.fee,
        "certificate": p.certificate,
        "user": {
            "id": p.user.id,
            "name": p.user.name,
            "email": p.user.email,
        } if p.user else None,
        "hospital": {
            "id": p.hospital.id,
            "name": p.hospital.name,
            "address": p.hospital.address,
            "lat": p.hospital.lat,
            "lng": p.hospital.lng,
        } if p.hospital else None,
    }

@router.post("/create-profile")
def create_profile(
    data: DoctorProfileIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    user = db.query(models.User).filter(
        models.User.id == data.user_id,
        models.User.role == "doctor"
    ).first()
    if not user:
        raise HTTPException(404, "Doctor user not found")

    existing = db.query(models.DoctorProfile).filter(
        models.DoctorProfile.user_id == data.user_id
    ).first()
    if existing:
        raise HTTPException(400, "Profile already exists for this doctor")

    profile = models.DoctorProfile(**data.dict())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"profile": profile_out(profile)}

@router.get("/profiles")
def get_all_profiles(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    profiles = db.query(models.DoctorProfile).all()
    return [profile_out(p) for p in profiles]

@router.get("/profiles/{profile_id}")
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    p = db.query(models.DoctorProfile).filter(models.DoctorProfile.id == profile_id).first()
    if not p:
        raise HTTPException(404, "Profile not found")
    return profile_out(p)

@router.put("/profiles/{profile_id}")
def update_profile(
    profile_id: int,
    data: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    p = db.query(models.DoctorProfile).filter(models.DoctorProfile.id == profile_id).first()
    if not p:
        raise HTTPException(404, "Profile not found")
    p.hospital_id    = data.hospital_id
    p.specialization = data.specialization
    p.fee            = data.fee
    db.commit()
    return {"message": "Updated"}

@router.delete("/profiles/{profile_id}")
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    p = db.query(models.DoctorProfile).filter(models.DoctorProfile.id == profile_id).first()
    if not p:
        raise HTTPException(404, "Profile not found")
    # Delete related schedules and bookings first
    db.query(models.Schedule).filter(models.Schedule.doctor_id == profile_id).delete()
    db.query(models.Booking).filter(models.Booking.doctor_id == profile_id).delete()
    db.delete(p)
    db.commit()
    return {"message": "Doctor and related data deleted"}