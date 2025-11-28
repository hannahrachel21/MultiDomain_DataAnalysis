from sqlalchemy import Column, String, JSON
from database import Base

class SessionDB(Base):
    __tablename__ = "sessions"
    
    session_id = Column(String, primary_key=True, index=True)
    file_name = Column(String, index=True)
    file_path = Column(String)
    domain = Column(String)
    meta = Column(JSON, default={})
