from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timezone
import json

db = SQLAlchemy()


def serialize_utc_datetime(value):
    if not value:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat().replace("+00:00", "Z")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    # Relationship to summaries
    summaries = db.relationship('Summary', backref='user', lazy=True, cascade='all, delete-orphan')

    @property
    def is_admin(self):
        return self.role == "admin"

    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    video_id = db.Column(db.String(11), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    key_points = db.Column(db.Text, nullable=False)  # JSON string
    transcript_length = db.Column(db.Integer, nullable=False)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def to_dict(self):
        """Convert summary to dictionary for JSON response"""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'video_id': self.video_id,
            'summary': self.summary,
            'key_points': json.loads(self.key_points) if self.key_points else [],
            'transcript_length': self.transcript_length,
            'thumbnail_url': self.thumbnail_url,
            'created_at': serialize_utc_datetime(self.created_at)
        }

    def __repr__(self):
        return f'<Summary {self.video_id}>'
