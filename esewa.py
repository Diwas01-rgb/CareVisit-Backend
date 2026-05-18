from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import get_current_user
import models, hmac, hashlib, base64, os
from pydantic import BaseModel

router = APIRouter()

# eSewa credentials
ESEWA_MERCHANT_ID  = os.getenv("ESEWA_MERCHANT_ID", "EPAYTEST")
ESEWA_SECRET_KEY   = os.getenv("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
ESEWA_BASE_URL     = os.getenv("ESEWA_BASE_URL", "https://rc-epay.esewa.com.np")  # test URL
FRONTEND_URL       = os.getenv("FRONTEND_URL", "http://localhost:5173")

class EsewaInitIn(BaseModel):
    bookingId: int
    amount: int  # NPR

def generate_signature(message: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for eSewa v2"""
    key  = secret.encode('utf-8')
    msg  = message.encode('utf-8')
    h    = hmac.new(key, msg, hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

@router.post("/initiate")
def initiate_esewa(
    data: EsewaInitIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    b = db.query(models.Booking).filter(models.Booking.id == data.bookingId).first()
    if not b:
        raise HTTPException(404, "Booking not found")

    amount         = str(data.amount)
    tax_amount     = "0"
    product_code   = ESEWA_MERCHANT_ID
    transaction_id = f"CARE-{b.id}-{user.id}"
    total_amount   = str(data.amount)

    # eSewa v2 signature: "total_amount=X,transaction_uuid=Y,product_code=Z"
    message   = f"total_amount={total_amount},transaction_uuid={transaction_id},product_code={product_code}"
    signature = generate_signature(message, ESEWA_SECRET_KEY)

    # Save transaction id for verification
    b.esewa_ref = transaction_id
    db.commit()

    return {
        "amount":           amount,
        "tax_amount":       tax_amount,
        "total_amount":     total_amount,
        "transaction_uuid": transaction_id,
        "product_code":     product_code,
        "product_service_charge":  "0",
        "product_delivery_charge": "0",
        "success_url": f"{FRONTEND_URL}/esewa-callback?bookingId={b.id}",
        "failure_url": f"{FRONTEND_URL}/esewa-callback?bookingId={b.id}&status=failed",
        "signed_field_names": "total_amount,transaction_uuid,product_code",
        "signature":    signature,
        "payment_url":  f"{ESEWA_BASE_URL}/api/epay/main/v2/form",
    }

@router.post("/verify")
def verify_esewa(
    request_data: dict,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    booking_id    = request_data.get("bookingId")
    encoded_data  = request_data.get("data")  # base64 encoded response from eSewa

    if not booking_id or not encoded_data:
        raise HTTPException(400, "Missing booking ID or payment data")

    try:
        decoded   = base64.b64decode(encoded_data).decode('utf-8')
        import json
        resp_data = json.loads(decoded)
    except Exception:
        raise HTTPException(400, "Invalid payment data")

    status = resp_data.get("status")
    if status != "COMPLETE":
        raise HTTPException(400, f"Payment not complete: {status}")

    b = db.query(models.Booking).filter(models.Booking.id == int(booking_id)).first()
    if not b:
        raise HTTPException(404, "Booking not found")

    b.is_paid        = True
    b.payment_method = "esewa"
    b.status         = "confirmed"
    db.commit()

    return {"message": "eSewa payment verified! Booking confirmed."}