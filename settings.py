import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGO_URI:     str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME:       str = os.getenv("DB_NAME", "carevisit")
    JWT_SECRET:    str = os.getenv("JWT_SECRET", "changeme")
    FRONTEND_URL:  str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Khalti
    KHALTI_SECRET_KEY: str = os.getenv("KHALTI_SECRET_KEY", "")
    KHALTI_BASE_URL:   str = os.getenv("KHALTI_BASE_URL", "https://dev.khalti.com/api/v2")

    # eSewa
    ESEWA_MERCHANT_CODE: str = os.getenv("ESEWA_MERCHANT_CODE", "EPAYTEST")
    ESEWA_SECRET_KEY:    str = os.getenv("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
    ESEWA_BASE_URL:      str = os.getenv("ESEWA_BASE_URL", "https://rc-epay.esewa.com.np")

settings = Settings()