from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    Float, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


# ── User ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(150), nullable=False)
    email           = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(20),  default="patient")   # patient | doctor | admin
    profile_picture = Column(String(500), nullable=True)
    phone           = Column(String(20),  nullable=True)
    created_at      = Column(DateTime,    default=datetime.utcnow)

    # Relationships
    doctor_profile  = relationship("DoctorProfile", back_populates="user",     uselist=False)
    bookings        = relationship("Booking",        back_populates="patient",  foreign_keys="Booking.patient_id")
    triage_history  = relationship("TriageHistory",  back_populates="patient")


# ── Hospital ──────────────────────────────────────────────────────────────────
class Hospital(Base):
    __tablename__ = "hospitals"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False)
    address    = Column(String(300), nullable=True)
    lat        = Column(Float,       nullable=True)
    lng        = Column(Float,       nullable=True)
    created_at = Column(DateTime,    default=datetime.utcnow)

    # ✅ Both sides of back_populates must exist
    doctors   = relationship("DoctorProfile", back_populates="hospital")
    schedules = relationship("Schedule",      back_populates="hospital")


# ── DoctorProfile ─────────────────────────────────────────────────────────────
class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"),     nullable=False)
    hospital_id      = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    specialization   = Column(String(100), nullable=False)
    fee              = Column(Integer,     default=500)
    certificate      = Column(String(500), nullable=True)
    qualification    = Column(String(300), nullable=True)   # ✅ was missing
    experience_years = Column(Integer,     default=0)       # ✅ was missing
    bio              = Column(Text,        nullable=True)    # ✅ was missing
    address          = Column(String(300), nullable=True)   # ✅ was missing
    profile_image    = Column(String(500), nullable=True)
    created_at       = Column(DateTime,    default=datetime.utcnow)

    # ✅ back_populates must match the attribute name on the other model
    user      = relationship("User",     back_populates="doctor_profile")
    hospital  = relationship("Hospital", back_populates="doctors")      # Hospital.doctors ✅
    schedules = relationship("Schedule", back_populates="doctor")
    bookings  = relationship("Booking",  back_populates="doctor", foreign_keys="Booking.doctor_id")


# ── Schedule ──────────────────────────────────────────────────────────────────
class Schedule(Base):
    __tablename__ = "schedules"

    id          = Column(Integer, primary_key=True, index=True)
    doctor_id   = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"),       nullable=False)
    day         = Column(String(20),  nullable=False)
    start_time  = Column(String(10),  nullable=False)
    end_time    = Column(String(10),  nullable=False)
    created_at  = Column(DateTime,    default=datetime.utcnow)

    # ✅ Both sides defined
    doctor   = relationship("DoctorProfile", back_populates="schedules")
    hospital = relationship("Hospital",      back_populates="schedules")  # Hospital.schedules ✅


# ── Booking ───────────────────────────────────────────────────────────────────
class Booking(Base):
    __tablename__ = "bookings"

    id             = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(Integer, ForeignKey("users.id"),           nullable=False)
    doctor_id      = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False)
    date           = Column(String(20),  nullable=False)
    time_slot      = Column(String(20),  nullable=False)
    status         = Column(String(20),  default="pending")    # pending | confirmed | cancelled | completed
    is_paid        = Column(Boolean,     default=False)
    payment_method = Column(String(50),  nullable=True)        # cash | khalti | esewa
    payment_status = Column(String(30),  default="unpaid")     # unpaid | paid_cash | paid_online
    fee            = Column(Integer,     default=500)
    created_at     = Column(DateTime,    default=datetime.utcnow)

    # ✅ foreign_keys needed because patient and doctor both point to different tables
    patient = relationship("User",          back_populates="bookings",  foreign_keys=[patient_id])
    doctor  = relationship("DoctorProfile", back_populates="bookings",  foreign_keys=[doctor_id])


# ── TriageHistory ─────────────────────────────────────────────────────────────
class TriageHistory(Base):
    __tablename__ = "triage_history"

    id              = Column(Integer, primary_key=True, index=True)
    patient_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    symptoms        = Column(Text,        nullable=False)   # JSON string
    specialization  = Column(String(100), nullable=False)
    priority        = Column(String(20),  nullable=True)    # high | medium | low
    confidence      = Column(String(30),  nullable=True)
    all_scores      = Column(Text,        nullable=True)    # JSON string
    created_at      = Column(DateTime,    default=datetime.utcnow)

    # ✅ Both sides defined
    patient = relationship("User", back_populates="triage_history")


# ── Payment ───────────────────────────────────────────────────────────────────
class Payment(Base):
    __tablename__ = "payments"

    id            = Column(Integer, primary_key=True, index=True)
    booking_id    = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    patient_id    = Column(Integer, ForeignKey("users.id"),    nullable=False)
    amount        = Column(Integer, nullable=False)
    khalti_pidx   = Column(String(100), nullable=True)
    khalti_token  = Column(String(200), nullable=True)
    status        = Column(String(20),  default="initiated")  # initiated | completed | failed
    created_at    = Column(DateTime,    default=datetime.utcnow)