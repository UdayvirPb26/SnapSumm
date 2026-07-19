import os
import json

import requests
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import text
from deep_translator import GoogleTranslator
from models import db, User, Summary
from summarizer import get_summary

ADMIN_USERNAME = "admin"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'dev-key-change-this-in-production'
)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'vidbrief.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    try:
        user_id_int = int(user_id)
        return User.query.get(user_id_int)
    except (ValueError, TypeError):
        return None


def is_admin_user(user):
    return getattr(user, "is_admin", False)


def is_guest_mode():
    return session.get("is_guest") is True


def ensure_user_role_column():
    if db.engine.dialect.name == "sqlite":
        with db.engine.begin() as conn:
            rows = conn.execute(text("PRAGMA table_info(user)")).all()
            if not any(row[1] == "role" for row in rows):
                conn.execute(text("ALTER TABLE user ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))


# ──── Authentication Routes (JSON API for the React frontend) ────
@app.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    email = payload.get("email", "").strip()
    password = payload.get("password", "")
    confirm_password = payload.get("confirm_password", "")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    role = "user"
    if username.lower() == ADMIN_USERNAME:
        if User.query.filter_by(role="admin").first():
            return jsonify({"error": "An admin account already exists"}), 400
        role = "admin"

    try:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"success": True}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@app.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        session.pop("is_guest", None)
        login_user(user)
        return jsonify({
            "success": True,
            "username": user.username,
            "is_admin": is_admin_user(user),
        })

    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/guest", methods=["POST"])
def guest():
    if current_user.is_authenticated:
        logout_user()
    session["is_guest"] = True
    return jsonify({"success": True})


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("is_guest", None)
    logout_user()
    return jsonify({"success": True})


@app.route("/api/me")
def api_me():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "username": current_user.username,
            "is_admin": is_admin_user(current_user),
            "is_guest": False,
        })
    if is_guest_mode():
        return jsonify({"authenticated": True, "username": "Guest", "is_admin": False, "is_guest": True})
    return jsonify({"authenticated": False})

# ──── Main Routes ────
# In production, `npm run build` inside frontend/ produces frontend/dist/.
# We serve those static files, with a catch-all so client-side routes
# like /admin still return the React app's index.html (React Router then
# takes over in the browser). During dev you don't hit this at all — you
# run `npm run dev` separately and open http://localhost:5173.
REACT_BUILD_DIR = os.path.join(BASE_DIR, "frontend", "dist")


@app.route("/")
@app.route("/<path:path>")
def index(path=""):
    if path.startswith(("api/", "login", "register", "logout", "guest",
                         "summarize", "translate-summary", "save-summary",
                         "summaries", "summary", "admin")):
        return jsonify({"error": "Not found"}), 404

    build_index = os.path.join(REACT_BUILD_DIR, "index.html")
    if os.path.exists(build_index):
        requested = os.path.join(REACT_BUILD_DIR, path)
        if path and os.path.isfile(requested):
            return send_from_directory(REACT_BUILD_DIR, path)
        return send_from_directory(REACT_BUILD_DIR, "index.html")

    return (
        "React build not found. Run `cd frontend && npm run build`, "
        "or run the dev server with `npm run dev` and open localhost:5173.",
        200,
    )


# GET /admin (a direct page load) now falls through to the catch-all
# index() route above, which serves the React app; React Router handles
# navigation to the Admin page client-side. The server still enforces
# admin-only access below — never trust the client alone for authorization.

@app.route("/api/admin/users")
@login_required
def api_admin_users():
    if not is_admin_user(current_user):
        return jsonify({"error": "Admin access required"}), 403

    users = User.query.order_by(User.username).all()
    return jsonify({
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    })


@app.route("/admin/delete/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    if not is_admin_user(current_user):
        return jsonify({"error": "Admin access required"}), 403

    user = User.query.get_or_404(user_id)
    if is_admin_user(user):
        return jsonify({"error": "Cannot delete admin accounts"}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"success": True, "message": "User deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500


@app.route("/summarize", methods=["POST"])
def summarize():
    if not current_user.is_authenticated and not is_guest_mode():
        return jsonify({"error": "Please sign in or continue as guest."}), 401

    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Invalid JSON in request"}), 400
        
        url = data.get("url", "").strip()

        if not url:
            return jsonify({"error": "No URL provided. Please paste a YouTube link."}), 400
        
        result = get_summary(url)

        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": f"Invalid request format: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occured. Please try again later."}), 500


@app.route("/translate-summary", methods=["POST"])
def translate_summary():
    if not current_user.is_authenticated and not is_guest_mode():
        return jsonify({"error": "Please sign in or continue as guest."}), 401

    data = request.get_json()
    text = data.get("text", "").strip()
    target_language = data.get("target_language", "hi").strip()

    allowed_languages = {
        "hi": "Hindi",
        "pa": "Punjabi",
        "bn": "Bengali",
        "ta": "Tamil",
        "te": "Telugu",
    }

    if not text:
        return jsonify({"error": "No summary text provided."}), 400

    if target_language not in allowed_languages:
        return jsonify({"error": "Unsupported language selected."}), 400

    try:
        translated_text = GoogleTranslator(
            source="auto",
            target=target_language
        ).translate(text)

        return jsonify({
            "translated_text": translated_text,
            "language": allowed_languages[target_language],
        })
    except (requests.RequestException, ValueError) as e: 
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500


# ──── Summary Management Routes ────
@app.route("/save-summary", methods=["POST"])
def save_summary():
    """Save a summary to the user's history"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Guest users cannot save summaries. Please create an account."}), 403

    data = request.get_json()
    
    # Extract required fields
    title = data.get("title", "Untitled").strip()
    url = data.get("url", "").strip()
    video_id = data.get("video_id", "").strip()
    summary = data.get("summary", "").strip()
    key_points = data.get("key_points", [])
    transcript_length = data.get("transcript_length", 0)
    thumbnail_url = data.get("thumbnail_url", "").strip()

    if not all([url, video_id, summary]):
        return jsonify({"error": "Missing required fields"}), 400

    # Validate key_points
    if not isinstance(key_points, list):
         return jsonify({"error": "key_points must be a list"}), 400
 
    try:
         json.dumps(key_points)
    except (TypeError, ValueError) as e:
         return jsonify({"error": f"Invalid key_points format: {str(e)}"}), 400    
    # Create summary record
    new_summary = Summary(
        user_id=current_user.id,
        title=title,
        url=url,
        video_id=video_id,
        summary=summary,
        key_points=json.dumps(key_points),
        transcript_length=transcript_length,
        thumbnail_url=thumbnail_url
    )

    try:
        db.session.add(new_summary)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Summary saved successfully!",
            "summary_id": new_summary.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save summary: {str(e)}"}), 500


@app.route("/summaries", methods=["GET"])
@login_required
def get_user_summaries():
    """Get all summaries for the logged-in user"""
    summaries = Summary.query.filter_by(user_id=current_user.id).order_by(Summary.created_at.desc()).all()
    return jsonify({
        "summaries": [s.to_dict() for s in summaries]
    })


@app.route("/summary/<int:summary_id>", methods=["GET"])
@login_required
def get_summary_detail(summary_id):
    """Get a specific summary"""
    summary = Summary.query.get_or_404(summary_id)
    
    # Verify ownership
    if summary.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify(summary.to_dict())


@app.route("/summary/<int:summary_id>", methods=["DELETE"])
@login_required
def delete_summary(summary_id):
    """Delete a summary"""
    summary = Summary.query.get_or_404(summary_id)
    
    # Verify ownership
    if summary.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        db.session.delete(summary)
        db.session.commit()
        return jsonify({"success": True, "message": "Summary deleted"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete summary: {str(e)}"}), 500


@app.route("/summary/<int:summary_id>/rename", methods=["PATCH"])
@login_required
def rename_summary(summary_id):
    """Rename a summary"""
    summary = Summary.query.get_or_404(summary_id)

    # Verify ownership
    if summary.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    new_title = data.get("title", "").strip()

    if not new_title:
        return jsonify({"error": "Title cannot be empty"}), 400

    try:
        summary.title = new_title
        db.session.commit()
        return jsonify({"success": True, "message": "Summary renamed"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to rename summary: {str(e)}"}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_user_role_column()
    
    print("\n Snap-Summ is running!")
    print(" Open your browser and go to: http://127.0.0.1:5001\n")
    app.run(debug=True, port=5001)
