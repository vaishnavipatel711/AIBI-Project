from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    created_at = Column(DateTime, default=func.now())

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, default=1)
    question = Column(String)
    answer = Column(String)
    created_at = Column(DateTime, default=func.now())
