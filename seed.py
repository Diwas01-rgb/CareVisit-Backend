from database import SessionLocal, engine, Base
from auth import hash_password
import models
import json

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def seed():
    print("🌱 Seeding database with corrected Nepal hospital data...")

    # ─────────────────────────────────────────────────────────────
    # Clear Existing Data
    # ─────────────────────────────────────────────────────────────
    db.query(models.TriageHistory).delete()
    db.query(models.Payment).delete()       # ✅ Must delete before Booking (FK constraint)
    db.query(models.Booking).delete()
    db.query(models.Schedule).delete()
    db.query(models.DoctorProfile).delete()
    db.query(models.Hospital).delete()
    db.query(models.User).delete()
    db.commit()

    print("✅ Cleared old data")

    # ─────────────────────────────────────────────────────────────
    # Users
    # ─────────────────────────────────────────────────────────────
    admin = models.User(
        name="Admin CareVisit",
        email="admin@carevisit.com",
        hashed_password=hash_password("admin123"),
        role="admin"
    )

    patients = [
        models.User(
            name="Rajan Sharma",
            email="rajan@gmail.com",
            hashed_password=hash_password("patient123"),
            role="patient"
        ),
        models.User(
            name="Sita Rai",
            email="sita@gmail.com",
            hashed_password=hash_password("patient123"),
            role="patient"
        ),
        models.User(
            name="Bikram Thapa",
            email="bikram@gmail.com",
            hashed_password=hash_password("patient123"),
            role="patient"
        ),
        models.User(
            name="Anita Gurung",
            email="anita@gmail.com",
            hashed_password=hash_password("patient123"),
            role="patient"
        ),
        models.User(
            name="Prakash Limbu",
            email="prakash@gmail.com",
            hashed_password=hash_password("patient123"),
            role="patient"
        ),
    ]

    doctor_users = [
        models.User(
            name="Dr. Suresh Kumar Yadav",
            email="suresh@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Priya Shrestha",
            email="priya@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Ramesh Prasad Gupta",
            email="ramesh@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Sunita Karmacharya",
            email="sunita@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Bikash Kumar Limbu",
            email="bikash@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Anita Devi Mahato",
            email="anitad@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Rajesh Hamal",
            email="rajesh@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
        models.User(
            name="Dr. Kabita Rai",
            email="kabita@doctor.com",
            hashed_password=hash_password("doctor123"),
            role="doctor"
        ),
    ]

    db.add(admin)

    for patient in patients:
        db.add(patient)

    for doctor in doctor_users:
        db.add(doctor)

    db.commit()

    db.refresh(admin)

    for patient in patients:
        db.refresh(patient)

    for doctor in doctor_users:
        db.refresh(doctor)

    print("✅ Users created")

    # ─────────────────────────────────────────────────────────────
    # Hospitals (Exact GPS Coordinates from Google Maps)
    # ─────────────────────────────────────────────────────────────
    hospitals = [

        # ✅ Verified on Google Maps — near Dharan Road, Itahari highway
        models.Hospital(
            name="Itahari Community Hospital",
            address="Itahari-4, Sunsari, Nepal",
            lat=26.67187,
            lng=87.27211,
        ),

        # ✅ Verified on Google Maps — Rangeli Road, Biratnagar
        models.Hospital(
            name="Koshi Hospital",
            address="Rangeli Road, Biratnagar, Morang, Nepal",
            lat=26.45905,
            lng=87.28519,
        ),

        # ✅ Verified on Google Maps — ~6km from Biratnagar city center
        models.Hospital(
            name="Nobel Medical College Teaching Hospital",
            address="Biratnagar Road, Biratnagar, Morang, Nepal",
            lat=26.48982,
            lng=87.27028,
        ),

        # ✅ Verified on Google Maps — Buddha Road, Dharan
        models.Hospital(
            name="BP Koirala Institute of Health Sciences",
            address="Buddha Road, Dharan-18, Sunsari, Nepal",
            lat=26.81224,
            lng=87.26836,
        ),

        # ✅ Verified on Google Maps — Tankisinuwari, Morang
        models.Hospital(
            name="Birat Medical College & Teaching Hospital",
            address="Tankisinuwari, Morang, Nepal",
            lat=26.52409,
            lng=87.27782,
        ),

        # ✅ Verified on Google Maps — near Inaruwa Supermarket Chowk
        models.Hospital(
            name="Sunsari District Hospital",
            address="Inaruwa-1, Sunsari, Nepal",
            lat=26.60058,
            lng=87.15086,
        ),

        # ⚠️ Not found on Google Maps — approximate Itahari area coordinates
        models.Hospital(
            name="Purna Health Clinic",
            address="Itahari-6, Sunsari, Nepal",
            lat=26.66492,
            lng=87.27531,
        ),

        # ⚠️ Not found on Google Maps — approximate Itahari area coordinates
        models.Hospital(
            name="Sunrise Hospital & Research Center",
            address="Itahari-2, Sunsari, Nepal",
            lat=26.66150,
            lng=87.27711,
        ),
    ]

    for hospital in hospitals:
        db.add(hospital)

    db.commit()

    for hospital in hospitals:
        db.refresh(hospital)

    print("✅ Hospitals created")

    # ─────────────────────────────────────────────────────────────
    # Doctor Profiles
    # ─────────────────────────────────────────────────────────────
    profiles = [

        models.DoctorProfile(
            user_id=doctor_users[0].id,
            hospital_id=hospitals[0].id,
            specialization="cardiology",
            fee=800,
            qualification="MBBS, MD (Cardiology) - BPKIHS",
            experience_years=12,
            address="Itahari-4, Sunsari",
            bio="Senior cardiologist specializing in heart disease and preventive cardiology."
        ),

        models.DoctorProfile(
            user_id=doctor_users[1].id,
            hospital_id=hospitals[1].id,
            specialization="neurology",
            fee=1000,
            qualification="MBBS, DM (Neurology) - IOM",
            experience_years=8,
            address="Biratnagar, Morang",
            bio="Neurologist specializing in stroke, migraine and epilepsy."
        ),

        models.DoctorProfile(
            user_id=doctor_users[2].id,
            hospital_id=hospitals[2].id,
            specialization="orthopedics",
            fee=700,
            qualification="MBBS, MS Orthopedics",
            experience_years=10,
            address="Biratnagar, Morang",
            bio="Orthopedic surgeon for trauma and joint replacement."
        ),

        models.DoctorProfile(
            user_id=doctor_users[3].id,
            hospital_id=hospitals[3].id,
            specialization="general",
            fee=500,
            qualification="MBBS, MD General Medicine",
            experience_years=6,
            address="Dharan-18, Sunsari",
            bio="Experienced general physician for primary healthcare."
        ),

        models.DoctorProfile(
            user_id=doctor_users[4].id,
            hospital_id=hospitals[4].id,
            specialization="dermatology",
            fee=600,
            qualification="MBBS, MD Dermatology",
            experience_years=7,
            address="Tankisinuwari, Morang",
            bio="Skin specialist focusing on acne, allergy and cosmetic dermatology."
        ),

        models.DoctorProfile(
            user_id=doctor_users[5].id,
            hospital_id=hospitals[5].id,
            specialization="general",
            fee=400,
            qualification="MBBS",
            experience_years=4,
            address="Inaruwa-1, Sunsari",
            bio="General physician focused on preventive care."
        ),

        models.DoctorProfile(
            user_id=doctor_users[6].id,
            hospital_id=hospitals[6].id,
            specialization="cardiology",
            fee=900,
            qualification="MBBS, DM Cardiology",
            experience_years=15,
            address="Itahari-6, Sunsari",
            bio="Senior heart specialist with extensive clinical experience."
        ),

        models.DoctorProfile(
            user_id=doctor_users[7].id,
            hospital_id=hospitals[7].id,
            specialization="neurology",
            fee=850,
            qualification="MBBS, MD Neurology",
            experience_years=9,
            address="Itahari-2, Sunsari",
            bio="Neurologist for headache and movement disorders."
        ),
    ]

    for profile in profiles:
        db.add(profile)

    db.commit()

    for profile in profiles:
        db.refresh(profile)

    print("✅ Doctor profiles created")

    # ─────────────────────────────────────────────────────────────
    # Schedules
    # ─────────────────────────────────────────────────────────────
    schedules = [

        models.Schedule(
            doctor_id=profiles[0].id,
            hospital_id=hospitals[0].id,
            day="Sunday",
            start_time="09:00",
            end_time="13:00"
        ),

        models.Schedule(
            doctor_id=profiles[0].id,
            hospital_id=hospitals[0].id,
            day="Tuesday",
            start_time="09:00",
            end_time="13:00"
        ),

        models.Schedule(
            doctor_id=profiles[1].id,
            hospital_id=hospitals[1].id,
            day="Monday",
            start_time="10:00",
            end_time="14:00"
        ),

        models.Schedule(
            doctor_id=profiles[2].id,
            hospital_id=hospitals[2].id,
            day="Wednesday",
            start_time="08:00",
            end_time="12:00"
        ),

        models.Schedule(
            doctor_id=profiles[3].id,
            hospital_id=hospitals[3].id,
            day="Friday",
            start_time="09:00",
            end_time="17:00"
        ),
    ]

    for schedule in schedules:
        db.add(schedule)

    db.commit()

    print("✅ Schedules created")

    # ─────────────────────────────────────────────────────────────
    # Bookings
    # ─────────────────────────────────────────────────────────────
    bookings = [

        models.Booking(
            patient_id=patients[0].id,
            doctor_id=profiles[0].id,
            date="2025-05-15",
            time_slot="09:00-09:30",
            status="confirmed",
            is_paid=True,
            payment_method="esewa",
            fee=800
        ),

        models.Booking(
            patient_id=patients[1].id,
            doctor_id=profiles[1].id,
            date="2025-05-16",
            time_slot="10:00-10:30",
            status="confirmed",
            is_paid=True,
            payment_method="cash",
            fee=1000
        ),
    ]

    for booking in bookings:
        db.add(booking)

    db.commit()

    print("✅ Bookings created")

    # ─────────────────────────────────────────────────────────────
    # Triage History
    # ─────────────────────────────────────────────────────────────
    histories = [

        models.TriageHistory(
            patient_id=patients[0].id,
            symptoms=json.dumps([
                "chest_pain",
                "shortness_breath",
                "fatigue"
            ]),
            specialization="cardiology",
            priority="high",
            confidence="78% match",
            all_scores=json.dumps({
                "cardiology": 11,
                "neurology": 0,
                "orthopedics": 0,
                "dermatology": 0,
                "general": 4
            })
        ),

        models.TriageHistory(
            patient_id=patients[1].id,
            symptoms=json.dumps([
                "headache",
                "migraine",
                "numbness"
            ]),
            specialization="neurology",
            priority="medium",
            confidence="85% match",
            all_scores=json.dumps({
                "cardiology": 0,
                "neurology": 9,
                "orthopedics": 0,
                "dermatology": 0,
                "general": 1
            })
        ),
    ]

    for history in histories:
        db.add(history)

    db.commit()

    print("✅ Triage history created")

    # ─────────────────────────────────────────────────────────────
    # Final Output
    # ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("🎉 Database seeded successfully!")
    print("=" * 60)

    print("\n👑 Admin Login")
    print("admin@carevisit.com  |  admin123")

    print("\n🧑‍⚕️ Doctor Login")
    print("suresh@doctor.com  |  doctor123")
    print("priya@doctor.com   |  doctor123")

    print("\n🧑 Patient Login")
    print("rajan@gmail.com    |  patient123")
    print("sita@gmail.com     |  patient123")

    print("=" * 60)

    db.close()


if __name__ == "__main__":
    seed()