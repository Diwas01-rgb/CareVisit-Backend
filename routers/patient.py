from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from routers.deps import get_current_user
import models

router = APIRouter()

@router.get("/me")
def get_me(user: models.User = Depends(get_current_user)):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "profilePicture": user.profile_picture
    }