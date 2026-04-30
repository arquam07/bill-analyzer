import uuid
from datetime import datetime

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


_USERNAME_RE = re.compile(r"^[a-z0-9]{3,50}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=50)
    name: str | None = Field(default=None, max_length=255)

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("username must be 3-50 lowercase alphanumeric characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    username: str
    name: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    user: UserResponse
    token: str
