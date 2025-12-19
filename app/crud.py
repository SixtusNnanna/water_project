from sqlalchemy.orm import Session
from typing import Optional
from app.models import Customer, Order, Driver, OrderAssignment, OrderStatus, WaterSource, Price, generate_ulid
from app.schema import (
    CustomerCreate,
    OrderCreate,
    DriverCreate,
    OrderAssignmentCreate,
    PriceCreate,
    WaterSourceCreate,
)
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from math import radians, sin, cos, sqrt, atan2
from typing import Optional, Dict
from app.models import Customer, Order, OrderAssignment, Price, Driver, WaterSource, OrderStatus  # Adjust import based on your structure

import os
from dotenv import load_dotenv
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
WATER_SOURCES = json.loads(os.getenv("WATER_SOURCES", "[]"))


class CRUD:

    @staticmethod
    def create_customer(db: Session, customer: CustomerCreate):
        db_customer = Customer(
            phone=customer.phone,
            location=customer.location,
            latitude=customer.latitude,
            longitude=customer.longitude,
        )
        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)
        return db_customer

    @staticmethod
    def get_customer_by_phone(db: Session, phone: str):
        return db.query(Customer).filter(Customer.phone == phone).first()

    @staticmethod
    def update_customer_location(
        db: Session, phone: str, latitude: float, longitude: float, address: str
    ):
        db_customer = CRUD.get_customer_by_phone(db, phone)
        if db_customer:
            db_customer.latitude = latitude
            db_customer.longitude = longitude
            db_customer.location = address
            db.commit()
            db.refresh(db_customer)
            return db_customer
        return None

    @staticmethod
    def calculate_distance(
        start_lat: float, start_lng: float, dest_lat: float, dest_lng: float
    ):
        """Calculate driving distance using Google Maps Distance Matrix API."""
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={start_lat},{start_lng}&destinations={dest_lat},{dest_lng}&mode=driving&key={GOOGLE_MAPS_API_KEY}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data["status"] != "OK" or not data["rows"]:
                logger.error(f"Distance Matrix API error: {data}")
                return None
            distance_meters = data["rows"][0]["elements"][0]["distance"]["value"]
            distance_km = distance_meters / 1000
            return distance_km
        except Exception as e:
            logger.error(f"Error calculating distance: {str(e)}")
            return None

    @staticmethod
    def calculate_order_price(db: Session, price: PriceCreate) -> Optional[float]:
        # Fetch the order
        order = db.query(Order).filter(Order.id == price.order_id).first()
        if not order:
            raise ValueError(f"Order with ID {price.order_id} not found")

        # Fetch the customer
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if not customer:
            raise ValueError(f"Customer with ID {order.customer_id} not found")

        if customer.latitude is None or customer.longitude is None:
            return None  

        # Find the nearest water source
        water_sources = db.query(WaterSource).all()
        if not water_sources:
            raise ValueError("No water sources found")

        min_distance = float('inf')
        for source in water_sources:
            if source.latitude is None or source.longitude is None:
                continue  # Skip water sources without valid coordinates
            distance = CRUD.calculate_distance(
                customer.latitude, customer.longitude, source.latitude, source.longitude
            )
            min_distance = min(min_distance, distance)

        if min_distance == float('inf'):
            return None  # No valid water sources with coordinates

        # Calculate total price
        total_price = (price.base_price * order.quantity) + (min_distance * price.price_per_km) + price.tax

        # Store the price in the Price table
        db_price = Price(
            id=generate_ulid(),
            order_id=price.order_id,
            base_price=price.base_price,
            tax=price.tax,
            price_per_km=price.price_per_km,
            total_price=total_price
        )
        db.add(db_price)
        db.commit()

        return total_price

    @staticmethod
    def create_order(db: Session, order: OrderCreate):
        db_order = Order(
            **order.model_dump()
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order

    @staticmethod
    def get_order(db: Session, order_id: int):
        return db.query(Order).filter(Order.id == order_id).first()

    @staticmethod
    def create_driver(db: Session, driver: DriverCreate):
        db_driver = Driver(
            name=driver.name,
            phone=driver.phone,
            vehicle_number=driver.vehicle_number,
            availability=driver.availability,
            location=driver.location,
            latitude=driver.latitude,
            longitude=driver.longitude,
        )
        db.add(db_driver)
        db.commit()
        db.refresh(db_driver)
        return db_driver

    @staticmethod
    def update_driver_location(
        db: Session, driver_phone: str, latitude: float, longitude: float, address: str
    ):
        db_driver = db.query(Driver).filter(Driver.phone == driver_phone).first()
        if db_driver:
            db_driver.latitude = latitude
            db_driver.longitude = longitude
            db_driver.location = address
            db_driver.availability = True
            db.commit()
            db.refresh(db_driver)
            return db_driver
        return None

    @staticmethod
    def get_available_driver(db: Session, order_id: str):
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")

        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        if not customer:
            raise ValueError(f"Customer with ID {order.customer_id} not found")

        if customer.latitude is None or customer.longitude is None:
            raise ValueError(f"Customer with ID {order.customer_id} is missing coordinates")

        drivers = db.query(Driver).filter(Driver.is_available == True).all()
        if not drivers:
            raise ValueError("No available drivers found")

        min_distance = float('inf')
        closest_driver = None

        for driver in drivers:
            if driver.latitude is None or driver.longitude is None:
                print(f"Skipping driver ID {driver.id} due to missing coordinates")
                continue
            try:
                distance = CRUD.calculate_distance(
                    customer.latitude, customer.longitude, driver.latitude, driver.longitude
                )
                if distance is None:
                    print(f"Distance calculation failed for driver ID {driver.id}")
                    continue
                if distance < min_distance:
                    min_distance = distance
                    closest_driver = driver
            except Exception as e:
                print(f"Error calculating distance for driver ID {driver.id}: {str(e)}")
                continue

        if closest_driver is None:
            raise ValueError("No drivers with valid coordinates found")

        return closest_driver

    @staticmethod
    def create_order_assignment(db: Session, assignment: OrderAssignmentCreate):
        db_assignment = OrderAssignment(
            order_id=assignment.order_id, driver_id=assignment.driver_id
        )
        db.add(db_assignment)
        db.commit()
        db.refresh(db_assignment)
        driver = db.query(Driver).filter(Driver.id == assignment.driver_id).first()
        if driver:
            driver.availability = False
            db.commit()
        return db_assignment

    @staticmethod
    def generate_tracking_link(
        customer_lat: float, customer_lng: float, driver_lat: float, driver_lng: float
    ):
        if not all([customer_lat, customer_lng, driver_lat, driver_lng]):
            return None
        return f"https://www.google.com/maps/dir/?api=1&origin={driver_lat},{driver_lng}&destination={customer_lat},{customer_lng}&travelmode=driving"

    @staticmethod
    def generate_navigation_link(
        start_lat: float, start_lng: float, dest_lat: float, dest_lng: float
    ):
        if not all([start_lat, start_lng, dest_lat, dest_lng]):
            return None
        return f"https://www.google.com/maps/dir/?api=1&origin={start_lat},{start_lng}&destination={dest_lat},{dest_lng}&travelmode=driving"

    @staticmethod
    def create_water_source(db: Session, source: WaterSourceCreate):
        db_source = WaterSource(
            address=source.address,
            latitude=source.latitude,
            longitude=source.longitude,
        )
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source

    @staticmethod
    def update_driver_availability(db: Session, driver_id: str, is_available: bool):
        db_driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if db_driver:
            db_driver.is_available = is_available
            db.commit()
            db.refresh(db_driver)
            return db_driver
        return None

    @staticmethod
    def get_water_sources(db: Session):
        return db.query(WaterSource).all()


    @staticmethod
    def find_closest_water_source(driver_lat: float, driver_lng: float, db: Session):
        sources = CRUD.get_water_sources(db)
        closest_source = None
        min_distance = float("inf")
        for source in sources:
            distance = CRUD.calculate_distance(
                driver_lat, driver_lng, source.latitude, source.longitude
            )
            if distance is not None and distance < min_distance:
                min_distance = distance
                closest_source = source
        return closest_source, min_distance

    @staticmethod
    def create_customer_order_assignment_price(
        db: Session,
        customer_data: Dict,
        order_data: Dict,
        base_price: float,
        price_per_km: float,
        tax: float
    ) -> Dict:
        try:
            # Validate inputs
            if not customer_data.get("phone") or not customer_data.get("location"):
                raise ValueError("Customer phone and location are required")
            if not order_data.get("product") or not order_data.get("quantity"):
                raise ValueError("Order product and quantity are required")

            # Start a transaction
            with db.begin():
                # Create Customer
                customer = Customer(
                    id=generate_ulid(),
                    phone=customer_data["phone"],
                    location=customer_data["location"],
                    latitude=customer_data.get("latitude"),
                    longitude=customer_data.get("longitude")
                )
                db.add(customer)

                # Create Order
                order = Order(
                    id=generate_ulid(),
                    product=order_data["product"],
                    quantity=order_data["quantity"],
                    status=order_data.get("status", OrderStatus.PENDING),
                    customer_id=customer.id
                )
                db.add(order)

                # Find an available driver and dis
                driver = db.query(Driver).filter(Driver.availability == True).first() 
                if not driver:
                    raise ValueError("No available drivers found")
                

                # Create OrderAssignment
                order_assignment = OrderAssignment(
                    id=generate_ulid(),
                    order_id=order.id,
                    driver_id=driver.id
                )
                db.add(order_assignment)

                # Calculate price based on distance to nearest water source
                total_price = None
                if customer.latitude is not None and customer.longitude is not None:
                    water_sources = db.query(WaterSource).all()
                    if not water_sources:
                        raise ValueError("No water sources found")

                    min_distance = float('inf')
                    for source in water_sources:
                        if source.latitude is None or source.longitude is None:
                            continue
                        distance = crud.calculate_distance(
                            customer.latitude, customer.longitude, source.latitude, source.longitude
                        )
                        min_distance = min(min_distance, distance)

                    if min_distance != float('inf'):
                        total_price = base_price + (min_distance * price_per_km) + tax

                # Create Price
                price = Price(
                    id=generate_ulid(),
                    order_id=order.id,
                    base_price=base_price,
                    tax=tax,
                    price_per_km=price_per_km,
                    total_price=total_price if total_price is not None else base_price + tax
                )
                db.add(price)

                # Commit transaction
                db.commit()

                return {
                    "customer_id": customer.id,
                    "order_id": order.id,
                    "order_assignment_id": order_assignment.id,
                    "price_id": price.id,
                    "total_price": price.total_price
                }

        except IntegrityError as e:
            db.rollback()
            return {"error": f"Database error: {str(e)}"}
        except ValueError as e:
            db.rollback()
            return {"error": str(e)}
        except Exception as e:
            db.rollback()
            return {"error": f"Unexpected error: {str(e)}"}
    

crud = CRUD()