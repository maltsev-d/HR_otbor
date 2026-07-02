# db/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=True)  # echo=True — если хочешь SQL в логах
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
