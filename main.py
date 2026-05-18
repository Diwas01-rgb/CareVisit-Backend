from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from dotenv import load_dotenv
import os

from routers import (
    auth, admin, doctor, patient,
    booking, schedule, hospital, triage, search,
    payment, dashboard, history, upload,
    doctor_profile,   # FormData version (the correct one)
)

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareVisit API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,           prefix="/api/auth",            tags=["Auth"])

# ── Dashboards  (frontend calls /api/patient/dashboard, /api/doctor/dashboard, /api/admin/dashboard)
app.include_router(dashboard.router,      prefix="/api",                 tags=["Dashboard"])

# ── Patient ────────────────────────────────────────────────────────────────
app.include_router(history.router,        prefix="/api/patient",         tags=["History"])
app.include_router(patient.router,        prefix="/api/patient",         tags=["Patient"])

# ── Doctor ─────────────────────────────────────────────────────────────────
app.include_router(doctor.router,         prefix="/api/doctor",          tags=["Doctor"])

# ── Bookings ───────────────────────────────────────────────────────────────
app.include_router(booking.router,        prefix="/api/bookings",        tags=["Bookings"])

# ── Schedules (doctor-facing: /api/schedules/my, /api/schedules/update/:id, /api/schedules/delete/:id)
app.include_router(schedule.router,       prefix="/api/schedules",       tags=["Schedule"])

# ── Admin ──────────────────────────────────────────────────────────────────
app.include_router(admin.router,          prefix="/api/admin",           tags=["Admin"])
# doctor_profile FormData CRUD — mounted at /api/admin (provides /profiles, /create-profile)
app.include_router(doctor_profile.router, prefix="/api/admin",           tags=["DoctorProfile"])
app.include_router(hospital.router,       prefix="/api/admin/hospitals", tags=["Hospital"])
# Admin schedule endpoints (/api/admin/schedules/create, /api/admin/schedules/list-all)
app.include_router(schedule.router,       prefix="/api/admin/schedules", tags=["AdminSchedule"])

# ── Search / Triage / Payment / Upload ────────────────────────────────────
app.include_router(search.router,         prefix="/api/doctors",         tags=["Search"])
app.include_router(triage.router,         prefix="/api",                 tags=["Triage"])   # → /api/triage
app.include_router(payment.router,        prefix="/api/payment",         tags=["Payment"])
app.include_router(upload.router,         prefix="/api/profile",         tags=["Upload"])

@app.get("/")
def root():
    return {"message": "CareVisit API is running"}

# ── Static files ───────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(os.path.join(UPLOADS_DIR, "profiles"), exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")