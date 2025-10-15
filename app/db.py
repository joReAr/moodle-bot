from sqlmodel import SQLModel, create_engine, Session
from .config import settings
import os

os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
os.makedirs("./indices", exist_ok=True)

engine = create_engine(settings.DB_URL, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
