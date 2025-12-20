# Gbammiri - Water Delivery Service Backend API

Gbammiri is a complete backend system for a **water delivery service app** that allows customers to order bottled water (or tanker services) seamlessly. The platform integrates with:

- **WhatsApp Business API** – For receiving orders, sending order confirmations, delivery updates, and customer support directly via WhatsApp.
- **Google Maps API** – For address autocomplete, distance calculation, delivery zone validation, and estimated delivery time.

Built with **FastAPI** for high performance, clean architecture, and production-ready features like  database migrations, and scalable design.

This project demonstrates real-world backend development skills: REST API design and  third-party API integrations.

## 🚀 Key Features


- **Order Management**  
  Full CRUD for water orders tanker, order status tracking (pending → confirmed → shipped → delivered).

- **WhatsApp Business API Integration**  
  - Receive incoming messages/orders via webhooks.
  - Send automated replies, order confirmations, and delivery notifications.
  - Interactive menus for product selection and address input.

- **Google Maps API Integration**  
  - Address autocomplete and validation.
  - Geocoding (convert address → coordinates).
  - Distance/duration calculation for delivery pricing and ETA.
  - Delivery zone restriction (only serve within defined areas).


- **Automatic API Documentation**  
  Interactive Swagger UI (`/docs`) and ReDoc (`/redoc`).

- **Clean & Scalable Architecture**  
  Modular code with separation of concerns (models, schemas, CRUD, utilities).

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **ORM**: SQLAlchemy
- **Database**: PostgreSQL (primary) 
- **Migrations**: Alembic
- **Third-Party Integrations**:
  - WhatsApp Business Cloud API
  - Google Maps Places & Distance Matrix API
- **Validation**: Pydantic
- **Server**: Uvicorn (development), Gunicorn (production)


## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/water_project.git
cd water_project

### 2. Set up virtual environment
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

### 3.Install dependencies
pip install -r requirements.txt

### 4. Environment variables
cp .env.example .env


DATABASE_URL=postgresql://

# JWT
SECRET_KEY=your_very_strong_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# WhatsApp Business API
WHATSAPP_TOKEN=your_whatsapp_business_token
WHATSAPP_PHONE_ID=your_phone_number_id
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_verify_token

# Google Maps API
GOOGLE_MAPS_API_KEY=your_google_maps_key

### 5. Run migrations
alembic upgrade head

Start the server
uvicorn app.main:app --reload

Use ngrok during development to expose webhook for WhatsApp testing.



