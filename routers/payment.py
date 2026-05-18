"""
payment.py — eSewa and cash payment handling.
Mounted at prefix /api/payment in main.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import hmac, hashlib, base64, uuid, json, os, traceback

from database import get_db
from routers.deps import get_current_user
import models

router = APIRouter()

BACKEND_URL  = os.getenv("BACKEND_URL",  "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

ESEWA_PRODUCT_CODE = os.getenv("ESEWA_MERCHANT_CODE", "EPAYTEST")
ESEWA_SECRET_KEY   = os.getenv("ESEWA_SECRET_KEY",    "8gBm/:&EnhH.1/q")
ESEWA_PAYMENT_URL  = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"


def _sign(total_amount: int, transaction_uuid: str) -> str:
    msg = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={ESEWA_PRODUCT_CODE}"
    )
    digest = hmac.new(
        ESEWA_SECRET_KEY.encode(),
        msg.encode(),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode()


def _safe_redirect(url: str):
    """Return a redirect that always works — fallback to HTML page if redirect fails."""
    try:
        return RedirectResponse(url=url, status_code=303)
    except Exception:
        # Last resort: return HTML page with JS redirect
        return HTMLResponse(
            content=f'<html><head><meta http-equiv="refresh" content="0;url={url}"></head>'
                    f'<body>Redirecting... <a href="{url}">Click here</a></body></html>',
            status_code=200,
        )


# ── POST /api/payment/esewa/initiate ──────────────────────────────────────
class EsewaInitIn(BaseModel):
    bookingId: int
    amount:    int


@router.post("/esewa/initiate")
def esewa_initiate(
    body: EsewaInitIn,
    db:   Session     = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == body.bookingId
    ).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.patient_id != user.id:
        raise HTTPException(403, "Not authorized")
    if booking.is_paid:
        raise HTTPException(400, "Booking is already paid")

    txn_uuid = str(uuid.uuid4())

    # Save payment record using raw SQL to avoid column-not-found errors
    # if models.py and DB are out of sync
    try:
        payment = models.Payment(
            booking_id     = booking.id,
            patient_id     = user.id,
            amount         = body.amount,
            status         = "initiated",
            khalti_pidx    = txn_uuid,   # used for lookup on callback
        )
        # Try to set esewa_txn_uuid if column exists
        try:
            payment.esewa_txn_uuid = txn_uuid
        except Exception:
            pass
        db.add(payment)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create payment record: {str(e)}")

    return {
        "payment_url":             ESEWA_PAYMENT_URL,
        "transaction_uuid":        txn_uuid,
        "amount":                  str(body.amount),
        "tax_amount":              "0",
        "total_amount":            str(body.amount),
        "product_code":            ESEWA_PRODUCT_CODE,
        "product_service_charge":  "0",
        "product_delivery_charge": "0",
        "success_url":             f"{BACKEND_URL}/api/payment/esewa/success",
        "failure_url":             f"{BACKEND_URL}/api/payment/esewa/failure",
        "signed_field_names":      "total_amount,transaction_uuid,product_code",
        "signature":               _sign(body.amount, txn_uuid),
    }


# ── GET /api/payment/esewa/success ────────────────────────────────────────
@router.get("/esewa/success")
def esewa_success(data: str = "", db: Session = Depends(get_db)):
    """
    eSewa redirects here with ?data=<base64-JSON>.
    Must ALWAYS redirect to frontend — never return a 500.
    """
    txn_uuid   = None
    booking_id = None

    try:
        # ── 1. Decode payload ───────────────────────────────────────────
        if not data:
            return _safe_redirect(f"{FRONTEND_URL}/payment/failed?reason=no_data_received")

        padded  = data + "=" * (-len(data) % 4)
        payload = json.loads(base64.b64decode(padded).decode("utf-8"))

        txn_uuid = payload.get("transaction_uuid", "")
        status   = payload.get("status", "")
        ref_id   = payload.get("transaction_code", "") or payload.get("transaction_id", "")

        if status != "COMPLETE":
            return _safe_redirect(
                f"{FRONTEND_URL}/payment/failed?reason=payment_not_complete"
            )

        if not txn_uuid:
            return _safe_redirect(
                f"{FRONTEND_URL}/payment/failed?reason=missing_transaction_uuid"
            )

        # ── 2. Find payment record ──────────────────────────────────────
        # Try khalti_pidx column (always exists)
        payment = db.query(models.Payment).filter(
            models.Payment.khalti_pidx == txn_uuid
        ).first()

        # Also try esewa_txn_uuid if column exists
        if not payment:
            try:
                payment = db.query(models.Payment).filter(
                    models.Payment.esewa_txn_uuid == txn_uuid
                ).first()
            except Exception:
                pass

        if not payment:
            # Payment was made but no record found — still mark booking
            # by searching booking directly (edge case recovery)
            return _safe_redirect(
                f"{FRONTEND_URL}/payment/failed?reason=payment_record_not_found"
                f"&uuid={txn_uuid}"
            )

        booking_id = payment.booking_id

        # ── 3. Update payment record ────────────────────────────────────
        payment.status       = "completed"
        payment.khalti_token = ref_id
        try:
            payment.esewa_ref_id = ref_id
        except Exception:
            pass
        db.commit()

        # ── 4. Update booking ───────────────────────────────────────────
        booking = db.query(models.Booking).filter(
            models.Booking.id == booking_id
        ).first()

        if booking:
            booking.is_paid        = True
            booking.payment_method = "esewa"
            booking.status         = "confirmed"
            try:
                booking.payment_status = "paid_online"
            except Exception:
                pass
            db.commit()

        # ── 5. Redirect to frontend success page ────────────────────────
        return _safe_redirect(
            f"{FRONTEND_URL}/payment/success?method=esewa&bookingId={booking_id}"
        )

    except Exception as e:
        # Log the real error to backend console for debugging
        print(f"[eSewa callback error] txn={txn_uuid} booking={booking_id}")
        print(traceback.format_exc())
        db.rollback()

        # Always redirect to frontend — NEVER show 500 to user
        return _safe_redirect(
            f"{FRONTEND_URL}/payment/failed?reason=server_error"
        )


# ── GET /api/payment/esewa/failure ────────────────────────────────────────
@router.get("/esewa/failure")
def esewa_failure():
    return _safe_redirect(
        f"{FRONTEND_URL}/payment/failed?reason=esewa_cancelled"
    )


# ── POST /api/payment/cash ────────────────────────────────────────────────
class CashIn(BaseModel):
    bookingId: int


@router.post("/cash")
def pay_cash(
    body: CashIn,
    db:   Session     = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    booking = db.query(models.Booking).filter(
        models.Booking.id == body.bookingId
    ).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.patient_id != user.id:
        raise HTTPException(403, "Not authorized")
    if booking.is_paid:
        raise HTTPException(400, "Booking is already paid")

    booking.is_paid        = True
    booking.payment_method = "cash"
    try:
        booking.payment_status = "paid_cash"
    except Exception:
        pass
    db.commit()

    return {"message": "Cash payment recorded. Please pay at the clinic on your visit day."}