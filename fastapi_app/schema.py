from pydantic import BaseModel, EmailStr
from fastapi.security import OAuth2PasswordRequestForm as FastAPIForm
import enum

# Define an Enum for user roles to match the database model
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

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
    It includes the ID, active status, and role, but crucially,
    it does NOT include the password, ensuring hashed passwords are never exposed.
    """
    id: int
    is_active: bool
    role: UserRole

    class Config:
        # This setting allows Pydantic to read data directly from ORM models.
        from_attributes = True

# --- Token Schemas ---

class Token(BaseModel):
    """Schema for the response when a user successfully logs in."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for the data contained within a JWT token."""
    email: str | None = None
    user_id: int | None = None
    role: str | None = None

# --- Exam Generation Schemas ---
class ExamGenerationRequest(BaseModel):
    """
    Schema for the request to generate a new exam, allowing for customization.
    Supports both CAT and GATE exams.
    For GATE exams, stream is required and must be one of the 30 valid streams.
    """
    exam_name: str = "CAT"  # CAT or GATE
    stream: str | None = None  # Required for GATE exams (CS, EE, ME, etc.)
    year: int | None = None
    
    class Config:
        schema_extra = {
            "example": {
                "exam_name": "GATE",
                "stream": "CS",
                "year": 2024
            }
        }


# --- OAuth2 Password Request Form ---
class OAuth2PasswordRequestForm(FastAPIForm):
    pass

