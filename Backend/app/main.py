from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.mongodb import connect_to_mongo, close_mongo_connection
from app.routers import auth, profiles, chat, admin, sync, quizzes
from app.services.quiz_scheduler import QuizScheduler
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=os.getenv("APP_NAME", "DigiMasterji"),
    description="AI-Powered STEM Learning Platform Backend",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(chat.router)