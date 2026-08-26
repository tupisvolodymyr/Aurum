import re

from pydantic import BaseModel, EmailStr, field_validator, model_validator

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


class RegisterForm(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not _USERNAME_RE.match(value):
            raise ValueError("Username must be 3-32 characters: letters, digits, underscore only")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Password must be at least 10 characters long")
        return value

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "RegisterForm":
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self


class LoginForm(BaseModel):
    identifier: str
    password: str
