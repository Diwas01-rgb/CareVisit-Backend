from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import require_role
import models
from pydantic import BaseModel

router = APIRouter()

class HospitalIn(BaseModel):
    name: str
    address: str = ""
    lat: float
    lng: float

def hospital_out(h):
    return {
        "id": h.id,
        "name": h.name,
        "address": h.address,
        "lat": h.lat,
        "lng": h.lng
    }

@router.post("/create")
def create_hospital(
    data: HospitalIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    h = models.Hospital(
        name=data.name,
        address=data.address,
        lat=data.lat,
        lng=data.lng
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"hospital": hospital_out(h)}

@router.get("/list")
def get_all_hospitals(
    db: Session = Depends(get_db)
):
    hospitals = db.query(models.Hospital).all()
    return [hospital_out(h) for h in hospitals]

@router.put("/update/{hospital_id}")
def update_hospital(
    hospital_id: int,
    data: HospitalIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    h = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(404, "Hospital not found")
    h.name    = data.name
    h.address = data.address
    h.lat     = data.lat
    h.lng     = data.lng
    db.commit()
    return {"message": "Updated"}

@router.delete("/delete/{hospital_id}")
def delete_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    h = db.query(models.Hospital).filter(models.Hospital.id == hospital_id).first()
    if not h:
        raise HTTPException(404, "Hospital not found")
    db.delete(h)
    db.commit()
    return {"message": "Deleted"}