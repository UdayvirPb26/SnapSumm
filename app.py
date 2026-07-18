import os
import json

import requests
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


from flask import Flask, render_template, request, jsonify, redirect, url_for, session
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


# ──── Authentication Routes ────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not username or not email or not password:
            return render_template("register.html", error="All fields are required")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters")

        if User.query.filter_by(username=username).first():
            return render_template("register.html", error="Username already exists")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email already registered")

        role = "user"
        if username.lower() == ADMIN_USERNAME:
            if User.query.filter_by(role="admin").first():
                return render_template("register.html", error="An admin account already exists")
            role = "admin"

        try:
            user = User(username=username, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            return render_template("register.html", error=f"Registration failed: {str(e)}")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = User.query.filter_by(username=username).first()
 
        if user and user.check_password(password):
            session.pop("is_guest", None)
            login_user(user)
            return redirect(url_for("index"))

        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/guest")
def guest():
    if current_user.is_authenticated:
        logout_user()
    session["is_guest"] = True
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("is_guest", None)
    logout_user()
    return redirect(url_for("login"))

# ──── Main Routes ────
@app.route("/")
def index():
    if not current_user.is_authenticated and not is_guest_mode():
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        username=current_user.username if current_user.is_authenticated else "Guest",
        is_admin=is_admin_user(current_user) if current_user.is_authenticated else False,
        is_guest=is_guest_mode(),
    )


@app.route("/admin")
@login_required
def admin_dashboard():
    if not is_admin_user(current_user):
        return redirect(url_for("index"))

    users = User.query.order_by(User.username).all()
    return render_template(
        "admin.html",
        username=current_user.username,
        users=users,
        user_count=len(users),
    )


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
