import random
import time
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from app.database.setup import Base, engine, get_db
from app.schema import (
    CustomerCreate,
    Customer,
    OrderCreate,
    Order,
    DriverCreate,
    Price,
    PriceCreate,
    WaterSourceCreate,
    Driver,
    OrderAssignmentCreate,
    OrderAssignment,
)
from app.crud import crud
import requests
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()

app = FastAPI()

# WhatsApp Business API config
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_API_URL = (
    f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
)

# Create database tables
Base.metadata.create_all(bind=engine)


def send_whatsapp_message(to_phone: str, text: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text},
    }
    response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
    response.raise_for_status()


@app.get("/whatsapp")
async def verify_webhook(request: Request):
    query = requests.query_params
    mode = query.get("hub.mode")
    token = query.get("hub.verify_token")
    challenge = query.get("hub.challenge")
    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    print(data)  # Debug: Inspect payload

    # Parse webhook payload
    if not (data.get("object") == "whatsapp_business_account" and data.get("entry")):
        return {"status": "ignored"}

    entry = data["entry"][0]
    changes = entry.get("changes", [])
    if not changes:
        return {"status": "no changes"}

    value = changes[0]["value"]
    messages = value.get("messages", [])
    if not messages:
        return {"status": "no messages"}

    message = messages[0]
    from_phone = message["from"]  # e.g., '1234567890'

    # Handle location message
    if message["type"] == "location":
        location = message["location"]
        latitude = location["latitude"]
        longitude = location["longitude"]
        address = location.get("address", "Unknown")

        # Check if sender is customer or driver
        db_customer = crud.get_customer_by_phone(db, from_phone)
        if db_customer:
            crud.update_customer_location(db, from_phone, latitude, longitude, address)
            send_whatsapp_message(
                from_phone,
                "Location updated! Send order in this format: 'I want <quantity> litres of water'",
            )
            return {"status": "customer location updated"}

        db_driver = db.query(Driver).filter(Driver.phone == from_phone).first()
        if db_driver:
            crud.update_driver_location(db, from_phone, latitude, longitude, address)
            send_whatsapp_message(
                from_phone, "Your location updated. Ready for assignments!"
            )
            return {"status": "driver location updated"}

        # New user
        customer_create = CustomerCreate(
            phone=from_phone, location=address, latitude=latitude, longitude=longitude
        )
        crud.create_customer(db, customer_create)
        send_whatsapp_message(
            from_phone,
            "Location saved! \n Send your order in this format: 'I want <quantity> litres of water'",
        )
        return {"status": "new customer created"}

    # Handle text message (order)
    if message["type"] == "text":
        body = message["text"]["body"].strip().lower()
        pattern = r"(\d+)\s*(litre|litres|liter|liters|gallon|gallons)\b"

        # match = re.match(r"\s+(\d+)", body)
        match = re.search(pattern, body)
        if not match:
            send_whatsapp_message(
                from_phone,
                "Invalid format. Share location, then: 'I want <quantity> litres of water'",
            )
            return {"status": "invalid format"}

        quantity_str, unit = match.groups()
        quantity = int(quantity_str)
        # total_price: Price = float(price_str)

        # Check customer and location
        db_customer = crud.get_customer_by_phone(db, from_phone)
        if not db_customer:
            customer_create = CustomerCreate(phone=from_phone, location=address)
            db_customer = crud.create_customer(db, customer_create)
            send_whatsapp_message(
                from_phone, "Please share your location first (attachment > Location)."
            )
            return {"status": "location required"}

        if not db_customer.latitude:
            send_whatsapp_message(
                from_phone, "Please share your location first (attachment > Location)."
            )
            return {"status": "location required"}

        try:
            # Create order
            order_create = OrderCreate(
                quantity=quantity,
                customer_id=db_customer.id,
            )
            db_order = crud.create_order(db, order_create)

            price_create = PriceCreate(
                order_id=db_order.id,
                base_price=20.0,  # Example base price calculation
                price_per_km=0.5,  # Example price per km (adjust as needed)
                tax=2.0,  # Example tax (adjust as needed)
            )
            try:
                total_price = crud.calculate_order_price(db, price_create)
            except ValueError as e:
                raise ValueError(f"Failed to calculate order price: {str(e)}")

            if db_order.total_price is None:
                db_order.total_price = total_price
                db.commit()
                db.refresh(db_order)
            else:
                print(
                    f"Order already has total_price: {db_order.total_price}, updating to {total_price}"
                )
                db_order.total_price = total_price
                db.commit()
                db.refresh(db_order)

        except ValueError as e:
            print(f"Error processing order: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise

            # Assign driver
        db_driver = crud.get_available_driver(db, db_order.id)
        print(db_driver)  # Debug: Check driver assignment
        if db_driver and db_driver.latitude:
            assignment_create = OrderAssignmentCreate(
                order_id=db_order.id, driver_id=db_driver.id
            )
            crud.create_order_assignment(db, assignment_create)
            tracking_link = crud.generate_tracking_link(
                db_customer.latitude,
                db_customer.longitude,
                db_driver.latitude,
                db_driver.longitude,
            )
            customer_msg = f"Order confirmed! {quantity} litres for N{total_price}. Track driver: {tracking_link}"
            send_whatsapp_message(from_phone, customer_msg)
            send_whatsapp_message(
                db_driver.phone,
                f"New order: {quantity} litres to {db_customer.location}. Share location if needed.",
            )
        else:
            send_whatsapp_message(
                from_phone,
                f"Order received! {quantity} litres for N{total_price}. No drivers available yet.",
            )
        return {"status": "order processed"}

    return {"status": "ignored"}


@app.post("/drivers/", response_model=Driver)
def create_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    return crud.create_driver(db, driver)


@app.post("/water_sources/")
def create_water_source(water_source: WaterSourceCreate, db: Session = Depends(get_db)):
    return crud.create_water_source(db, water_source)


@app.patch("/drivers/{driver_id}/availability", response_model=Driver)
def update_driver_availability(
    driver_id: str, availability: bool, db: Session = Depends(get_db)
):
    db_driver = crud.update_driver_availability(db, driver_id, availability)
    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return db_driver
