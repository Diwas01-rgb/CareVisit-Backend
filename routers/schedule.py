from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import get_current_user, require_role
import models
from pydantic import BaseModel

router = APIRouter()

class ScheduleIn(BaseModel):
    doctorId: int
    hospitalId: int
    day: str
    startTime: str
    endTime: str

def schedule_out(s: models.Schedule):
    return {
        "id": s.id,
        "_id": s.id,
        "day": s.day,
        "startTime": s.start_time,
        "endTime": s.end_time,
        "doctor": {
            "id": s.doctor.id,
            "specialization": s.doctor.specialization,
            "user": {
                "id": s.doctor.user.id,
                "name": s.doctor.user.name,
            } if s.doctor and s.doctor.user else None,
        } if s.doctor else None,
        "hospital": {
            "id": s.hospital.id,
            "name": s.hospital.name,
        } if s.hospital else None,
    }

@router.post("/create")
def create_schedule(
    data: ScheduleIn,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    s = models.Schedule(
        doctor_id=data.doctorId,
        hospital_id=data.hospitalId,
        day=data.day,
        start_time=data.startTime,
        end_time=data.endTime
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"schedule": schedule_out(s)}

@router.get("/list-all")
def get_all_schedules(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin"))
):
    schedules = db.query(models.Schedule).all()
    return [schedule_out(s) for s in schedules]

@router.get("/my")
def my_schedules(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    profile = db.query(models.DoctorProfile).filter(
        models.DoctorProfile.user_id == user.id
    ).first()
    if not profile:
        return []
    schedules = db.query(models.Schedule).filter(
        models.Schedule.doctor_id == profile.id
    ).all()
    return [schedule_out(s) for s in schedules]

@router.put("/update/{schedule_id}")
def update_schedule(
    schedule_id: int,
    data: dict,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    s = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "Schedule not found")
    if data.get("day"):       s.day = data["day"]
    if data.get("startTime"): s.start_time = data["startTime"]
    if data.get("endTime"):   s.end_time = data["endTime"]
    db.commit()
    return {"message": "Updated"}

@router.delete("/delete/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    s = db.query(models.Schedule).filter(models.Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(404, "Not found")
    db.delete(s)
    db.commit()
    return {"message": "Deleted"}