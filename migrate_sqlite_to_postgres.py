import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import db, User, Summary
from app import app

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sqlite_url = f"sqlite:///{os.path.join(BASE_DIR, 'vidbrief.db')}"

sqlite_engine = create_engine(sqlite_url)
SQLiteSession = sessionmaker(bind=sqlite_engine)
sqlite_session = SQLiteSession()

with app.app_context():
    db.drop_all()
    db.create_all()

    users = sqlite_session.query(User).all()
    user_id_map = {}

    for old_user in users:
        new_user = User(
            username=old_user.username,
            email=old_user.email,
            role=getattr(old_user, "role", "user"),
            password_hash=old_user.password_hash,
            created_at=old_user.created_at,
        )
        db.session.add(new_user)
        db.session.flush()
        user_id_map[old_user.id] = new_user.id

    summaries = sqlite_session.query(Summary).all()

    for old_summary in summaries:
        new_summary = Summary(
            user_id=user_id_map[old_summary.user_id],
            title=old_summary.title,
            url=old_summary.url,
            video_id=old_summary.video_id,
            summary=old_summary.summary,
            key_points=old_summary.key_points,
            transcript_length=old_summary.transcript_length,
            thumbnail_url=old_summary.thumbnail_url,
            created_at=old_summary.created_at,
        )
        db.session.add(new_summary)

    db.session.commit()

print("Migration completed successfully.")