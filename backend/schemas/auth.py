"""
Authentication schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    company: Optional[str] = None
    email: str
    role: str

class UserInfo(BaseModel):
    email: str
    company: Optional[str] = None
    role: str

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str] = None
    role: str = "user"

class UpdatePasswordRequest(BaseModel):
    email: EmailStr
    new_password: str

class DeleteUserRequest(BaseModel):
    email: EmailStr