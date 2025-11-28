from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import upload_router, data_router

# Import DB init function
from database import Base, engine
from models.session_db_model import SessionDB

def create_db():
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Data Analysis Backend",
    description="Backend API for Excel-based smart analytics over multiple domains.",
    version="0.1.0",
)

# Run create_db() once when app starts
@app.on_event("startup")
def on_startup():
    print("Initializing database...")
    create_db()
    print("Database initialized.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router.router)
app.include_router(data_router.router)

@app.get("/")
async def root():
    return {"message": "Smart Data Analysis API is running"}
