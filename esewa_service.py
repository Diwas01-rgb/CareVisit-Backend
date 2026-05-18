import hmac
import hashlib
import base64
import uuid
import httpx
import os
from datetime import datetime
from sqlalchemy.orm import Session
import models

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── eSewa sandbox credentials ─────────────────────────────────────────────────
ESEWA_PRODUCT_CODE = "EPAYTEST"
ESEWA_SECRET_KEY   = "8gBm/:&EnhH.1/q"
ESEWA_PAYMENT_URL  = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
ESEWA_VERIFY_URL   = "https://rc-epay.esewa.com.np/api/epay/transaction/statuscheck"


def generate_signature(total_amount: int, transaction_uuid: str, product_code: str) -> str:
    message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
    digest  = hmac.new(
        ESEWA_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def initiate_esewa(db: Session, booking_id: int, patient_id: int, amount: int) -> dict:
    """Create eSewa payment params. Returns form fields for frontend POST."""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise ValueError("Booking not found")
    if booking.patient_id != patient_id:
        raise ValueError("Not authorized")
    if booking.is_paid:
        raise ValueError("Already paid")

    transaction_uuid = str(uuid.uuid4())

    # Store transaction_uuid in khalti_pidx column (reused for eSewa)
    payment = models.Payment(
        booking_id  = booking_id,
        patient_id  = patient_id,
        amount      = amount,
        status      = "initiated",
        khalti_pidx = transaction_uuid,
    )
    db.add(payment)
    db.commit()

    signature = generate_signature(amount, transaction_uuid, ESEWA_PRODUCT_CODE)

    return {
        "payment_url":             ESEWA_PAYMENT_URL,
        "transaction_uuid":        transaction_uuid,
        "amount":                  amount,
        "tax_amount":              0,
        "total_amount":            amount,
        "product_code":            ESEWA_PRODUCT_CODE,
        "product_service_charge":  0,
        "product_delivery_charge": 0,
        "success_url":             f"{BACKEND_URL}/api/payment/esewa/success",
        "failure_url":             f"{BACKEND_URL}/api/payment/esewa/failure",
        "signed_field_names":      "total_amount,transaction_uuid,product_code",
        "signature":               signature,
    }


async def verify_esewa(db: Session, data: str) -> dict:
    """Verify eSewa callback. Called by backend redirect handler."""
    import json

    decoded = base64.b64decode(data + "==").decode("utf-8")
    payload = json.loads(decoded)

    transaction_uuid = payload.get("transaction_uuid")
    status           = payload.get("status")
    ref_id           = payload.get("transaction_id") or payload.get("ref_id")

    if status != "COMPLETE":
        raise ValueError(f"Payment not complete. Status: {status}")

    payment = db.query(models.Payment).filter(
        models.Payment.khalti_pidx == transaction_uuid
    ).first()
    if not payment:
        raise ValueError("Payment record not found")

    # Optional: double-check with eSewa verify API
    async with httpx.AsyncClient() as client:
        resp = await client.get(ESEWA_VERIFY_URL, params={
            "product_code":     ESEWA_PRODUCT_CODE,
            "total_amount":     payment.amount,
            "transaction_uuid": transaction_uuid,
        })
    if resp.status_code == 200:
        if resp.json().get("status") != "COMPLETE":
            raise ValueError("eSewa verification failed")

    # Update payment record
    payment.status       = "completed"
    payment.khalti_token = ref_id
    db.commit()

    # Confirm the booking
    booking = db.query(models.Booking).filter(
        models.Booking.id == payment.booking_id
    ).first()
    if booking:
        booking.is_paid        = True
        booking.payment_status = "paid_online"
        booking.payment_method = "esewa"
        booking.status         = "confirmed"
        db.commit()

    return {
        "message":    "eSewa payment verified",
        "booking_id": payment.booking_id,
        "ref_id":     ref_id,
    }