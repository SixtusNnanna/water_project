from pydantic import BaseModel
from typing import Optional
from app.models import OrderStatus


class CustomerCreate(BaseModel):
    phone: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Customer(BaseModel):
    id: str
    phone: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    quantity: int
    customer_id: str
    status: Optional[OrderStatus] = OrderStatus.PENDING


class Order(BaseModel):
    id: str
    quantity: int
    status: OrderStatus
    customer_id: str
    price: Optional[float] = None 

    class Config:
        from_attributes = True


class DriverCreate(BaseModel):
    name: str
    phone: str
    vehicle_number: str
    availability: bool
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DriverUpdateAvailability(BaseModel):
    is_available: bool
    

class Driver(BaseModel):
    id: str
    name: str
    phone: str
    vehicle_number: str
    is_available: bool
    location: str
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True


class OrderAssignmentCreate(BaseModel):
    order_id: str
    driver_id: str


class OrderAssignment(BaseModel):
    id: str
    order_id: str
    driver_id: str

    class Config:
        from_attributes = True


class WaterSourceCreate(BaseModel):
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class WaterSource(BaseModel):
    id: str
    address: str
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True


class PriceCreate(BaseModel):   
    order_id: str
    base_price: float = 15
    tax: float = 0
    price_per_km: float = 10
    distance_km: float = 0
    total_price: float | None = None

    
class Price(BaseModel):
    id: str
    order_id: str
    base_price: float
    tax: float
    price_per_km: float
    distance_km: float
    total_price: float

    class Config:
        from_attributes = True