from datetime import datetime, timedelta
from bson import ObjectId


async def get_available_slots(db, doctor_id, date):
    
    schedules = await db.schedules.find({
        "doctor": ObjectId(doctor_id)
    }).to_list(100)

    booked = await db.appointments.find({
        "doctor": ObjectId(doctor_id),
        "date": date
    }).to_list(100)

    booked_slots = [b["time"] for b in booked]

    available_slots = []

    for schedule in schedules:

        start = datetime.strptime(schedule["startTime"], "%H:%M")
        end = datetime.strptime(schedule["endTime"], "%H:%M")

        current = start

        while current < end:

            slot = current.strftime("%H:%M")

            if slot not in booked_slots:
                available_slots.append(slot)

            current += timedelta(minutes=30)

    return {
        "doctorId": doctor_id,
        "date": date,
        "availableSlots": available_slots
    }