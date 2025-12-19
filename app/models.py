from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from app.database.setup import Base  # Adjust import if needed
import enum

from ulid import ULID


# Define Order Status Enum
class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


def generate_ulid():
    """Generate a ULID"""
    return str(ULID())


class Customer(Base):
    __tablename__ = "customers"

    id = Column(
        String(26), primary_key=True, default=generate_ulid, unique=True, index=True
    )
    phone = Column(
        String, unique=True, nullable=False
    )  # WhatsApp number (e.g., 'whatsapp:+1234567890')
    location = Column(String, nullable=False)  # New field: e.g., 'New York'
    latitude = Column(Float, nullable=True)  # New: Latitude from location share
    longitude = Column(Float, nullable=True)

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(
        String(26), primary_key=True, default=generate_ulid, unique=True, index=True
    )
    quantity = Column(Integer, nullable=False, default=1000)  
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    customer_id = Column(String(26), ForeignKey("customers.id"), nullable=False)
    total_price = Column(Float, nullable=True, default=0.0)  # New field for total price

    customer = relationship("Customer", back_populates="orders")
    price = relationship("Price", back_populates="order", uselist=False)


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(
        String(26), primary_key=True, default=generate_ulid, unique=True, index=True
    )
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    vehicle_number = Column(String, unique=True, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    orders = relationship("OrderAssignment", back_populates="driver")


class OrderAssignment(Base):
    __tablename__ = "order_assignments"

    id = Column(
        String(26), primary_key=True, default=generate_ulid, unique=True, index=True
    )
    order_id = Column(String(26), ForeignKey("orders.id"), nullable=False)
    driver_id = Column(String(26), ForeignKey("drivers.id"), nullable=False)

    order = relationship("Order")
    driver = relationship("Driver", back_populates="orders")


class WaterSource(Base):
    __tablename__ = "water_sources"

    id = Column(
        String(26), primary_key=True, default=generate_ulid, unique=True, index=True
    )
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


class Price(Base):
    __tablename__ = "prices"

    id = Column(
        String(26), primary_key=True, default=generate_ulid, unique=True, index=True
    )
    order_id = Column(String(26), ForeignKey("orders.id"), nullable=False, unique=True)
    base_price = Column(Float, nullable=False, default=15)
    tax = Column(Float, nullable=False, default=0)
    price_per_km = Column(Float, nullable=False, default=10)
    distance_km = Column(Float, nullable=False, default=0)
    total_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="price")


