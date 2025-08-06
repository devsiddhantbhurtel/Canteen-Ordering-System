🧾 Canteen Ordering System
A full-stack Canteen Ordering System developed with Django (backend) and React (frontend). This platform streamlines canteen operations by enabling users to browse food items, place orders,
and track them in real-time, while staff and admins manage menus and monitor order statuses.

🚀 Features
👤 User Module
Register and login using secure authentication
View available food items with images, names, prices
Add items to cart
Place and track orders
Receive real-time order status updates via WebSockets

 Khalti Payment Integration
Pay directly using Khalti payment gateway
Token verification and backend confirmation
Payment status tracked and logged

RFID Scan Support for Teachers
RFID-based user authentication and order processing
Dedicated commands to manage and read RFID cards
Ideal for offline or quick scan-based ordering

🍽️ Food Management
Add, edit, delete food items (admin/staff only)
Upload images, descriptions, prices, and categories
🛒 Ordering System
Add multiple items to cart
Create and confirm orders
Order status updates: Placed → Preparing → Ready → Delivered

⚙️ Role-Based Access
Admin: Full access to all modules
Staff: Manage orders and food items
User: Browse, order, track

📡 Real-Time Updates
WebSocket integration using Django Channels
Live updates for staff when new orders are placed

📦 API Endpoints
REST API using Django Rest Framework (DRF)
Token-based authentication
JSON-based interaction between frontend and backend

📷 Media Support
Upload food images

Display images dynamically in frontend

🛠️ Tech Stack
🔙 Backend
Django

Django Rest Framework

Django Channels (WebSocket support)

SQLite / PostgreSQL (DBMS)

🔚 Frontend
React.js

Axios

TailwindCSS or Bootstrap (assumed based on project structure)

📦 Others
JWT / Cookie-based Authentication

CORS Support

Socket.IO / WebSocket Real-Time Connection

File upload handling

.env for environment configuration

📁 Project Structure
bash
Copy
Edit
Canteen Ordering System/
├── canteen_app/            # Core Django app
│   ├── models.py           # Database models
│   ├── views.py            # DRF Views and business logic
│   ├── serializers.py      # Data serialization
│   ├── urls.py             # URL routing
│   └── consumers.py        # WebSocket consumer for real-time order tracking
├── media/                  # Uploaded food images
├── manage.py               # Django CLI script
├── canteen-frontend/       # React frontend
└── .env                    # Environment variables
⚙️ Installation
Backend (Django)

cd "Canteen Ordering System"
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
Frontend (React)

cd canteen-frontend
npm install
npm start
🔐 Environment Variables
Create a .env file in the backend root and include:


SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
🧪 Sample API Endpoints
Endpoint	Method	Description
/api/login/	POST	User login
/api/register/	POST	User registration
/api/foods/	GET	List all food items
/api/orders/	POST	Place a new order
/api/orders/<id>/	PATCH	Update order status (admin/staff)

✅ To-Do / Improvements

Dockerize backend and frontend
CI/CD with GitHub Actions
Improve mobile responsiveness

🤝 Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
