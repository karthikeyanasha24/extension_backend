import os
import razorpay
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# --- Database Setup ---
DB_FILE = "licenses.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            plan TEXT,
            expires TEXT,
            order_id TEXT
        )
    ''')
    conn.commit()
    conn.close()

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- Razorpay Client ---
RZP_KEY_ID = os.getenv("RZP_KEY_ID")
RZP_KEY_SECRET = os.getenv("RZP_KEY_SECRET")

if not RZP_KEY_ID or not RZP_KEY_SECRET:
    raise RuntimeError("Razorpay keys not set in environment variables.")

client = razorpay.Client(auth=(RZP_KEY_ID, RZP_KEY_SECRET))

# --- API Endpoints ---
@app.post("/create-order")
def create_order(payload: dict):
    email = payload["email"]
    order = client.order.create({
        "amount": 99900,
        "currency": "INR",
        "payment_capture": 1
    })
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (email, order_id) VALUES (?, ?)", (email, order['id']))
    conn.commit()
    conn.close()
    
    return {"order_id": order["id"], "key": RZP_KEY_ID}

@app.post("/verify-payment")
def verify_payment(payload: dict):
    try:
        client.utility.verify_payment_signature(payload)
        email = payload["email"]
        expires_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET plan = ?, expires = ? WHERE email = ?", ('pro', expires_date, email))
        conn.commit()
        conn.close()
        
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {e}")

@app.get("/license-status")
def license_status(email: str):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT plan, expires FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not user['plan']:
        return {"plan": "free"}
    
    return dict(user)

