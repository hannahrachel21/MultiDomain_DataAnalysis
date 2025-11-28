from sqlalchemy.orm import Session
from database import SessionLocal
from models.session_db_model import SessionDB

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_session(session_id: str, file_path: str, file_name: str, domain: str, meta: dict = {}):
    db = SessionLocal()
    session = SessionDB(
        session_id=session_id,
        file_path=file_path,
        file_name=file_name,
        domain=domain,
        meta=meta
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_file_name(file_name: str):
    db = SessionLocal()
    return db.query(SessionDB).filter(SessionDB.file_name == file_name).first()


def get_session(session_id: str):
    db = SessionLocal()
    return db.query(SessionDB).filter(SessionDB.session_id == session_id).first()


def update_session_meta(session_id: str, key: str, value):
    db = SessionLocal()
    session = db.query(SessionDB).filter(SessionDB.session_id == session_id).first()

    if session:
        session.meta[key] = value
        db.commit()
    return session
