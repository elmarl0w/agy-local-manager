from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
async def get_status():
    return {
        "provider": "CloudCore",
        "status": "Online",
        "uptime": "99.99%",
        "message": "Welcome to CloudCore - High performance cloud computing."
    }

@app.get("/api/plans")
async def get_plans():
    return [
        {"name": "Starter", "price": "$5/mo", "description": "Perfect for personal projects."},
        {"name": "Pro", "price": "$20/mo", "description": "Optimized for growing businesses."},
        {"name": "Enterprise", "price": "Custom", "description": "Scalable infrastructure for large corporations."}
    ]
