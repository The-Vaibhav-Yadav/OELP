from pydantic import BaseModel, EmailStr
from fastapi.security import OAuth2PasswordRequestForm as FastAPIForm

# --- User Schemas ---

class UserBase(BaseModel):
    """Base schema for a user, containing common attributes."""
    email: EmailStr

class UserCreate(UserBase):
    """Schema used for creating a new user. Inherits from UserBase and adds a password."""
    password: str

class User(UserBase):
    """
    Schema used for returning user data from the API.
    It inherits from UserBase and includes the ID and active status, but crucially,
    it does NOT include the password, ensuring hashed passwords are never exposed.
    """
    id: int
    is_active: bool

    class Config:
        # This setting allows Pydantic to read data directly from ORM models
        # (like the User model from models.py), making it easy to convert
        # database objects into API responses.
        orm_mode = True

# --- Token Schemas ---

class Token(BaseModel):
    """Schema for the response when a user successfully logs in."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for the data contained within a JWT token."""
    email: str | None = None
    user_id: int | None = None

# --- OAuth2 Password Request Form ---
# This makes the standard username/password form data available in the
# interactive API docs (/docs) for easy testing of the login endpoint.
class OAuth2PasswordRequestForm(FastAPIForm):
    pass

