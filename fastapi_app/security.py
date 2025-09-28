from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone

from . import schema, database, models, crud, config

# --- Password Hashing ---
# Use bcrypt for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This tells FastAPI where to look for the token (the /token endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.
    
    Args:
        plain_password (str): The password entered by the user.
        hashed_password (str): The hashed password stored in the database.
        
    Returns:
        bool: True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.
    
    Args:
        password (str): The plain-text password.
        
    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)

# --- JWT Token Functions ---

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Creates a new JWT access token.
    
    Args:
        data (dict): The data to encode in the token (the payload).
        expires_delta (timedelta, optional): The lifespan of the token. Defaults to settings.
        
    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.settings.SECRET_KEY, algorithm=config.settings.ALGORITHM)
    return encoded_jwt

# --- FastAPI Dependencies for Security ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    """
    FastAPI dependency to get the current user from a JWT token.
    This function will be used to protect API endpoints.
    
    It decodes the token, validates its signature and expiration, and fetches the user from the database.
    
    Raises:
        HTTPException(401): If the token is invalid, expired, or the user doesn't exist.
    
    Returns:
        models.User: The authenticated user object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.settings.SECRET_KEY, algorithms=[config.settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
        token_data = schema.TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_subscriber(current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    """
    A stricter dependency that checks if the user is not only authenticated but also has an active subscription.
    This will be used to protect the premium features like exam generation.
    
    Raises:
        HTTPException(403): If the user does not have an active subscription.
        
    Returns:
        models.User: The authenticated and subscribed user object.
    """
    if not current_user.is_active:
         raise HTTPException(status_code=400, detail="Inactive user")

    subscription = crud.get_subscription_by_user_id(db, user_id=current_user.id)
    
    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active subscription.",
        )
        
    # Optional: Check if the subscription is expired
    if subscription.expires_at and subscription.expires_at < datetime.now():
        # Here you could also have logic to set subscription.is_active to False
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscription has expired.",
        )
        
    return current_user

