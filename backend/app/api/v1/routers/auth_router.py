from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Any
from app.db.repositories.user_repo import UserRepository
from app.core.security import verify_password, create_access_token

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest) -> Any:
    repo = UserRepository()
    user = repo.get_user_by_email(login_data.email)
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


