import os, razorpay
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

RZP_KEY_ID = os.getenv("RZP_KEY_ID")
RZP_KEY_SECRET = os.getenv("RZP_KEY_SECRET")

if not RZP_KEY_ID or not RZP_KEY_SECRET:
    raise RuntimeError("Razorpay keys not set in environment variables. Please set RZP_KEY_ID and RZP_KEY_SECRET.")

client = razorpay.Client(auth=(RZP_KEY_ID, RZP_KEY_SECRET))

USERS = {}

@app.post("/create-order")
def create_order(payload: dict):
    email = payload["email"]
    order = client.order.create({
        "amount": 99900,
        "currency": "INR",
        "payment_capture": 1
    })
    USERS[email] = {"order_id": order["id"]}
    return {"order_id": order["id"], "key": RZP_KEY_ID}

@app.post("/verify-payment")
def verify_payment(payload: dict):
    try:
        client.utility.verify_payment_signature(payload)
        USERS[payload["email"]] = {
            "plan": "pro",
            "expires": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        return {"status": "ok"}
    except:
        raise HTTPException(400, "Verification failed")

@app.get("/license-status")
def license_status(email: str):
    user = USERS.get(email)
    if not user:
        return {"plan": "free"}
    return user

