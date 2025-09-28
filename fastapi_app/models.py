from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    """
    SQLAlchemy model for the 'users' table.
    This class defines the structure of the table that will store user information.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    # This creates a one-to-one relationship with the Subscription model.
    # It allows you to easily access a user's subscription via `user.subscription`.
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Subscription(Base):
    """
    SQLAlchemy model for the 'subscriptions' table.
    This table will track the subscription status for each user.
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    # This column is generic to support different payment providers like Razorpay.
    payment_customer_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    
    # This defines the other side of the one-to-one relationship.
    # It allows you to access the user associated with a subscription via `subscription.user`.
    user = relationship("User", back_populates="subscription")

