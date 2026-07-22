from sqlalchemy import Column, Integer, String, DateTime, Float, func
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

class ScoreHistory(Base):
    __tablename__ = "score_history"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    intelligence_score = Column(Float)
    momentum_score = Column(Float)
    sentiment_score = Column(Float)
    financial_score = Column(Float)
    risk_level = Column(String)
    personality = Column(String)
    created_at = Column(DateTime, default=func.now())
