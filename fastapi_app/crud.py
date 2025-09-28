from sqlalchemy.orm import Session
from . import models, schema, security
import datetime

# --- User CRUD Functions ---

def get_user_by_email(db: Session, email: str):
    """
    Retrieves a single user from the database based on their email address.
    
    Args:
        db (Session): The database session.
        email (str): The email of the user to retrieve.
        
    Returns:
        models.User | None: The user object if found, otherwise None.
    """
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schema.UserCreate):
    """
    Creates a new user in the database.
    
    Args:
        db (Session): The database session.
        user (schema.UserCreate): The Pydantic schema containing user creation data.
        
    Returns:
        models.User: The newly created user object.
    """
    # Hash the user's plain-text password before storing it
    hashed_password = security.get_password_hash(user.password)
    
    # Create a new SQLAlchemy User model instance
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    
    # Add the new user to the session and commit it to the database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Refresh the instance to get the new ID from the DB
    return db_user

# --- Subscription CRUD Functions ---

def get_subscription_by_user_id(db: Session, user_id: int):
    """
    Retrieves a user's subscription from the database.
    
    Args:
        db (Session): The database session.
        user_id (int): The ID of the user whose subscription is to be retrieved.
        
    Returns:
        models.Subscription | None: The subscription object if found, otherwise None.
    """
    return db.query(models.Subscription).filter(models.Subscription.user_id == user_id).first()

def create_or_update_subscription(db: Session, user_id: int, payment_customer_id: str | None, is_active: bool, expires_at: datetime):
    """
    Creates a new subscription for a user or updates their existing one.
    This is typically called by a payment provider webhook after a successful payment.
    
    Args:
        db (Session): The database session.
        user_id (int): The ID of the user.
        payment_customer_id (str | None): The customer ID from the payment provider.
        is_active (bool): The new status of the subscription.
        expires_at (datetime): The new expiration date of the subscription.
        
    Returns:
        models.Subscription: The created or updated subscription object.
    """
    db_subscription = get_subscription_by_user_id(db, user_id=user_id)
    
    if db_subscription:
        # If the subscription already exists, update its fields
        db_subscription.is_active = is_active
        db_subscription.expires_at = expires_at
        db_subscription.payment_customer_id = payment_customer_id
    else:
        # If it's a new subscription, create a new instance
        db_subscription = models.Subscription(
            user_id=user_id,
            payment_customer_id=payment_customer_id,
            is_active=is_active,
            expires_at=expires_at
        )
        db.add(db_subscription)
        
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

