"""
upload.py — profile picture and doctor certificate uploads.
Mounted at prefix /api/profile in main.py.

Endpoints:
  POST /api/profile/profile-picture
  POST /api/profile/doctor-certificate
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import os, shutil, uuid

from database import get_db
from routers.deps import get_current_user
import models

router = APIRouter()

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Always save profile images in uploads/profiles/
PROFILE_DIR = os.path.join(BASE_DIR, "uploads", "profiles")
os.makedirs(PROFILE_DIR, exist_ok=True)


def _save_file(file: UploadFile, directory: str) -> str:
    ext      = os.path.splitext(file.filename or "")[-1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path     = os.path.join(directory, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # Return path relative to uploads/ root so StaticFiles can serve it
    rel = os.path.relpath(path, os.path.join(BASE_DIR, "uploads"))
    return f"/uploads/{rel.replace(os.sep, '/')}"


def _abs_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http"):
        return path
    return f"{BACKEND_URL}{path}"


# ── POST /api/profile/profile-picture ─────────────────────────────────────
@router.post("/profile-picture")
def upload_profile_pic(
    image: UploadFile = File(...),
    db:    Session    = Depends(get_db),
    user:  models.User = Depends(get_current_user),
):
    rel_path = _save_file(image, PROFILE_DIR)
    user.profile_picture = rel_path
    db.commit()
    return {"profilePicture": _abs_url(rel_path)}


# ── POST /api/profile/doctor-certificate ──────────────────────────────────
@router.post("/doctor-certificate")
def upload_certificate(
    certificate: UploadFile = File(...),
    db:          Session    = Depends(get_db),
    user:        models.User = Depends(get_current_user),
):
    profile = (
        db.query(models.DoctorProfile)
        .filter(models.DoctorProfile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(404, "Doctor profile not found")

    rel_path = _save_file(certificate, PROFILE_DIR)
    profile.certificate = rel_path
    db.commit()
    return {"certificate": _abs_url(rel_path)}