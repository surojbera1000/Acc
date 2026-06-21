"""
Database Models for Account Marketplace Bot
Uses SQLAlchemy ORM
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class AccountType(enum.Enum):
    """Account types enumeration"""
    SOCIAL_MEDIA = "social_media"
    STREAMING = "streaming"
    GAMING = "gaming"
    EMAIL = "email"
    OTHER = "other"

class OrderStatus(enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    REFUNDED = "refunded"

class TransactionType(enum.Enum):
    """Transaction type enumeration"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PURCHASE = "purchase"
    REFUND = "refund"

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.telegram_id} ({self.username})>"

class Account(Base):
    """Account model for sale"""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    account_type = Column(Enum(AccountType), nullable=False)
    country = Column(String(2), nullable=False)  # ISO country code
    title = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    credentials = Column(Text)  # Encrypted credentials
    otp = Column(String(50))  # Encrypted OTP
    two_factor = Column(Text)  # Encrypted 2FA details
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="account")
    
    def __repr__(self):
        return f"<Account {self.title} ({self.country}) - ${self.price}>"

class Order(Base):
    """Order model"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True, nullable=False)  # Custom order ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    delivery_attempts = Column(Integer, default=0)
    delivered_at = Column(DateTime)
    failed_at = Column(DateTime)
    refunded_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    account = relationship("Account", back_populates="orders")
    
    def __repr__(self):
        return f"<Order {self.order_id} - {self.status}>"

class Transaction(Base):
    """Transaction model"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(500))
    metadata = Column(Text)  # JSON metadata
    is_successful = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction {self.transaction_id} - {self.transaction_type}: ${self.amount}>"

class FailedDelivery(Base):
    """Failed delivery tracking model"""
    __tablename__ = "failed_deliveries"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_retry = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<FailedDelivery Order:{self.order_id}>"