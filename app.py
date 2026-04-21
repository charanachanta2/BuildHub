from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask import Response
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
import os
from dotenv import load_dotenv
load_dotenv()
from flask import jsonify
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer
from functools import wraps
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId

import uuid
import os
import markdown
import random

app = Flask(__name__)
app.secret_key = "BuildHub@2026$Secret#987"

app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["MAIL_EMAIL"] = "buildhubcode@gmail.com"
app.config["MAIL_PASSWORD"] ="ysxi vkjm neoh seyl"

serializer = URLSafeTimedSerializer(app.secret_key)

# ---------------- DB ----------------
client = MongoClient("mongodb+srv://charanachanta2:Charan1114@cluster0.ysxk5ry.mongodb.net/")
db = client["buildhub"]

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- CREATE ADMIN ----------------
if not db.users.find_one({"username": "admin"}):
    db.users.insert_one({
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "role": "admin",
        "user_id": "BHADMIN",
        "github": "",
        "bio": "",
        "can_review": True,

        # 🔥 ADDED (progress)
        "progress": {
            "github": False,
            "project": False,
            "linkedin": False,
            "linkedin_link": ""
        }
    })

# ---------------- HOME ----------------
@app.route("/")
def landing():
    return render_template("index.html")

@app.route("/home")
def home():
    return redirect("/login")

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrap

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/sitemap.xml")
def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://www.buildhubcode.xyz/</loc></url>
      <url><loc>https://www.buildhubcode.xyz/about</loc></url>
      <url><loc>https://www.buildhubcode.xyz/projects</loc></url>
      <url><loc>https://www.buildhubcode.xyz/docs</loc></url>
      <url><loc>https://www.buildhubcode.xyz/login</loc></url>
      <url><loc>https://www.buildhubcode.xyz/register</loc></url>
    </urlset>"""
    return Response(xml, mimetype="application/xml")

# ---------------- SOCIAL LOGIN ----------------
@app.route("/social_login", methods=["POST"])
def social_login():

    data = request.get_json()

    email = data["email"].strip().lower()
    name = data.get("name", "")

    user = db.users.find_one({"email": email})

    # first time social user
    if not user:

        username = email.split("@")[0].lower()

        original = username
        count = 1

        while db.users.find_one({"username": username}):
            username = f"{original}{count}"
            count += 1

        db.users.insert_one({
            "username": username,
            "email": email,
            "password": "",
            "user_id": "BH" + str(uuid.uuid4())[:6],
            "role": "user",
            "bio": "",
            "github": "",
            "xp": 0,
            "badges": [],
            "oauth_user": True,
            "must_set_username": True,

            # 🔥 policy fields
            "terms_accepted": False,
            "privacy_accepted": False
        })

        user = db.users.find_one({"email": email})

    session["user"] = user["username"]
    session["role"] = user.get("role", "user")

    # first time username setup
    if user.get("must_set_username", False):
        return {"redirect": "/choose-username"}

    return {"redirect": "/dashboard"}

def send_reset_email(to_email, reset_link):

    subject = "BuildHub Password Reset"
    
    body = f"""
Hello,

Click the link below to reset your BuildHub password:

{reset_link}

If you didn't request this, ignore this email.

BuildHub Team
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = app.config["MAIL_EMAIL"]
    msg["To"] = to_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(
        app.config["MAIL_EMAIL"],
        app.config["MAIL_PASSWORD"]
    )

    server.send_message(msg)
    server.quit()

@app.route("/choose-username", methods=["GET", "POST"])
@login_required
def choose_username():

    user = db.users.find_one({"username": session["user"]})

    if request.method == "POST":

        new_username = request.form["username"].strip().lower()

        if db.users.find_one({"username": new_username}):
            return render_template("choose_username.html", error="Username already taken")

        old_username = user["username"]

        db.users.update_one(
            {"username": old_username},
            {
                "$set": {
                    "username": new_username,
                    "must_set_username": False
                }
            }
        )

        session["user"] = new_username

        return redirect("/dashboard")

    return render_template("choose_username.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"].strip().lower()

        user = db.users.find_one({"email": email})

        if user:

            token = serializer.dumps(email, salt="reset-password")

            reset_link = url_for(
                "reset_password",
                token=token,
                _external=True
            )

            send_reset_email(email, reset_link)

        return render_template(
            "forgot_password.html",
            success="If this email exists, a reset link has been sent."
        )

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    try:
        email = serializer.loads(
            token,
            salt="reset-password",
            max_age=3600
        )

    except:
        return "Reset link expired or invalid."

    if request.method == "POST":

        new_password = request.form["password"]

        hashed = generate_password_hash(new_password)

        db.users.update_one(
            {"email": email},
            {"$set": {"password": hashed}}
        )

        flash("Password changed successfully.")
        return redirect("/login")

    return render_template("reset_password.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form["username"].strip().lower()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        # username exists
        if db.users.find_one({"username": username}):
            flash("Username already exists")
            return redirect("/register")

        # email exists
        if db.users.find_one({"email": email}):
            flash("Email already registered")
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        db.users.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password,
            "user_id": "BH" + str(uuid.uuid4())[:6],
            "github": "",
            "bio": "",
            "role": "user",
            "can_review": False,
            "xp": 0,
            "badges": [],

            # 🔥 policy fields
            "terms_accepted": False,
            "privacy_accepted": False,

            "progress": {
                "github": False,
                "project": False,
                "linkedin": False,
                "linkedin_link": ""
            }
        })

        flash("Registration successful. Please login.")
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    # If already logged in
    if "user" in session:
        return redirect("/dashboard")

    if request.method == "POST":

        username = request.form["username"].strip().lower()
        password = request.form["password"]

        # =========================
        # REVIEWER LOGIN (.rev)
        # =========================
        if username.endswith(".rev"):

            base_username = username.replace(".rev", "")

            user = db.users.find_one({
                "username": base_username
            })

            if user:

                stored_password = user.get("password", "")

                # normal hashed password users only
                if stored_password and check_password_hash(stored_password, password):

                    if user.get("can_review", False):

                        session["user"] = user["username"]
                        session["role"] = "reviewer"

                        return redirect("/reviews")

                    flash("Reviewer access not enabled")
                    return redirect("/login")

            flash("Invalid reviewer credentials")
            return redirect("/login")

        # =========================
        # NORMAL LOGIN
        # =========================
        user = db.users.find_one({
            "username": username
        })

        if user:

            stored_password = user.get("password", "")

            # block oauth-only users
            if stored_password == "":
                flash("Use Google/GitHub login for this account.")
                return redirect("/login")

            if check_password_hash(stored_password, password):

                session["user"] = user["username"]   # source of truth
                session["role"] = user.get("role", "user")

                return redirect("/dashboard")

        flash("Invalid credentials")
        return redirect("/login")

    return render_template("login.html")

@app.route("/accept_policies", methods=["POST"])
@login_required
def accept_policies():

    db.users.update_one(
        {"username": session["user"]},
        {
            "$set": {
                "terms_accepted": True,
                "privacy_accepted": True,
                "accepted_at": datetime.utcnow()
            }
        }
    )

    return {"status": "ok"}

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@login_required
def dashboard():

    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})

    if not user:
        return redirect("/login")

    # ensure user_id exists
    if "user_id" not in user:
        new_id = "BH" + str(uuid.uuid4())[:6]

        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"user_id": new_id}}
        )

        user["user_id"] = new_id

    user_id = user["user_id"]

    # 🔥 policy status
    terms_accepted = user.get("terms_accepted", False)
    privacy_accepted = user.get("privacy_accepted", False)

    # notifications
    notifications = list(db.notifications.find({
        "user_id": user_id,
        "seen": False
    }))

    # =========================
    # PROJECT STATUS
    # =========================
    all_projects = list(db.projects.find({
        "status": "approved"
    }))

    enrollments = list(db.project_enrollments.find({
        "team": {"$in": [user_id]}
    }))

    project_status_map = {}

    for e in enrollments:

        submission = db.submissions.find_one({
            "project_id": e["project_id"],
            "team": e["team"]
        })

        if submission:
            project_status_map[e["project_id"]] = "completed"
        else:
            project_status_map[e["project_id"]] = "in_progress"

    projects = []

    for p in all_projects:

        pid = str(p["_id"])

        projects.append({
            "_id": p["_id"],
            "title": p["title"],
            "status": project_status_map.get(pid, "not_taken")
        })

    # completed count
    completed = list(db.submissions.find({
        "team": {"$in": [user_id]},
        "status": "completed"
    }))

    projects_completed = len(completed)

    # streak
    today = datetime.utcnow().date()

    days = set()

    for c in completed:
        if "created_at" in c:
            days.add(c["created_at"].date())

    streak = 0
    d = today

    while d in days:
        streak += 1
        d -= timedelta(days=1)

    # xp / level
    xp = user.get("xp", 0)
    level = (xp // 100) + 1
    xp_to_next = (level * 100) - xp

    # daily progress
    today_count = db.submissions.count_documents({
        "team": {"$in": [user_id]},
        "status": "completed",
        "created_at": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lte": datetime.combine(today, datetime.max.time())
        }
    })

    daily_progress = min(today_count * 100, 100)

    # heatmap
    activity = []

    for i in range(7):

        day = today - timedelta(days=6 - i)

        count = db.submissions.count_documents({
            "team": {"$in": [user_id]},
            "status": "completed",
            "created_at": {
                "$gte": datetime.combine(day, datetime.min.time()),
                "$lte": datetime.combine(day, datetime.max.time())
            }
        })

        if count == 0:
            heat = 0
        elif count == 1:
            heat = 1
        elif count == 2:
            heat = 2
        elif count == 3:
            heat = 3
        else:
            heat = 4

        activity.append(heat)

    badges = user.get("badges", [])

    return render_template(
        "dashboard.html",

        user={
            "name": user["username"],
            "xp": xp,
            "level": level,
            "xp_to_next": xp_to_next
        },

        stats={
            "streak": streak,
            "projects_completed": projects_completed,
            "badges": len(badges),
            "rank": "N/A",
            "daily_progress": daily_progress
        },

        activity=activity,
        badges=badges,
        projects=projects,
        notifications=notifications,

        # 🔥 popup check
        terms_accepted=terms_accepted,
        privacy_accepted=privacy_accepted
    )

@app.route("/create_project", methods=["GET", "POST"])
@app.route("/create_project", methods=["GET", "POST"])
def create_project():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})

    if request.method == "POST":
        title = request.form["title"]

        mdfile = request.files.get("mdfile")
        content = ""

        # 📄 READ MARKDOWN FILE
        if mdfile and mdfile.filename.endswith(".md"):
            content = mdfile.read().decode("utf-8")

        # 🔥 THIS IS THE IMPORTANT PART
        db.projects.insert_one({
            "title": title,
            "content": content,
            "created_by": user["username"],
            "status": "pending",   # ✅ THIS FIXES YOUR ISSUE
            "created_at": datetime.utcnow()
        })

        return redirect("/my_creations")

    return render_template("create_project.html", user=user) 
 
@app.route("/my_projects")
@login_required
def my_projects():

    user = db.users.find_one({"username": session["user"]})

    if not user:
        return redirect("/login")

    user_id = user["user_id"]

    # projects user joined
    enrollments = list(db.project_enrollments.find({
        "team": {"$in": [user_id]}
    }))

    projects = []

    for e in enrollments:

        project = db.projects.find_one({
            "_id": ObjectId(e["project_id"])
        })

        if not project:
            continue

        submission = db.submissions.find_one({
            "project_id": e["project_id"],
            "team": e["team"]
        })

        status = "In Progress"

        if submission:
            status = "Completed"

        projects.append({
            "title": project["title"],
            "description": project.get("content", "")[:180],
            "status": status
        })

    return render_template(
        "my_projects.html",
        projects=projects,
        user=user
    )

@app.route("/my_creations")
def my_creations():
    if "user" not in session:
        return redirect("/login")

    projects = list(db.projects.find({
        "created_by": session["user"]
    }))

    return render_template("my_creations.html", projects=projects)

# ---------------- NOTIFICATIONS ----------------
@app.route("/get_notifications")
def get_notifications():
    if "user" not in session:
        return {"notifications": []}

    user = db.users.find_one({"username": session["user"]})

    notifications = list(db.notifications.find({
        "user_id": user["user_id"]
    }).sort("created_at", -1))

    # convert ObjectId to string
    for n in notifications:
        n["_id"] = str(n["_id"])

    return {"notifications": notifications}

# ---------------- PROJECT ----------------
@app.route("/project/<id>")
def project(id):
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})
    if not user:
        return redirect("/login")

    user_id = user["user_id"]

    project = db.projects.find_one({"_id": ObjectId(id)})

    if not project:
        return redirect("/projects")

    # 🔥 STRICT ACCESS CONTROL
    if project.get("status") != "approved":
        if (
            project.get("created_by") != session["user"]
            and session.get("role") != "admin"
        ):
            return redirect("/projects")   # 👈 IMPORTANT CHANGE

    html_content = markdown.markdown(
        project.get("content", ""),
        extensions=["fenced_code", "tables"]
    )

    submission = db.submissions.find_one({
        "project_id": id,
        "team": {"$in": [user_id]}
    })

    reviews = []
    avg_score = 0
    can_view_review = False

    if submission:
        reviews = list(db.reviews.find({
            "submission_id": str(submission["_id"]),
            "status": "done"
        }))

        for r in reviews:
            if (
                user_id in submission.get("team", [])
                or r.get("reviewer") == session["user"]
            ):
                can_view_review = True
                break

        if can_view_review:
            scores = [r["score"] for r in reviews if r.get("score")]
            avg_score = sum(scores)/len(scores) if scores else 0

    return render_template(
        "project.html",
        project=project,
        content=html_content,
        reviews=reviews,
        avg_score=avg_score,
        can_view_review=can_view_review,
        user=user
    )

@app.route("/admin/projects")
def admin_projects():
    if session.get("role") != "admin":
        return "Access Denied"

    projects = list(db.projects.find({
        "status": "pending"
    }))

    return render_template("admin_projects.html", projects=projects)

@app.route("/approve_project/<id>")
def approve_project(id):
    if session.get("role") != "admin":
        return "Access Denied"

    project = db.projects.find_one({"_id": ObjectId(id)})

    if not project:
        return redirect("/admin/projects")

    # 🛑 avoid re-approving
    if project.get("status") == "approved":
        return redirect("/admin/projects")

    # ✅ update status
    db.projects.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "approved"}}
    )

    # 👤 find creator
    creator = db.users.find_one({
        "username": project.get("created_by")
    })

    # 🔔 send notification
    if creator:
        db.notifications.insert_one({
            "user_id": creator["user_id"],
            "message": f"Your project '{project.get('title')}' got approved 🎉",
            "type": "approval",
            "created_at": datetime.utcnow()
        })

    return redirect("/admin/projects")


@app.route("/reject_project/<id>")
def reject_project(id):
    if session.get("role") != "admin":
        return "Access Denied"

    project = db.projects.find_one({"_id": ObjectId(id)})

    if not project:
        return redirect("/admin/projects")

    # 🛑 avoid re-rejecting
    if project.get("status") == "rejected":
        return redirect("/admin/projects")

    # ❌ update status
    db.projects.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": "rejected"}}
    )

    # 👤 find creator
    creator = db.users.find_one({
        "username": project.get("created_by")
    })

    # 🔔 send notification
    if creator:
        db.notifications.insert_one({
            "user_id": creator["user_id"],
            "message": f"Your project '{project.get('title')}' was rejected ❌",
            "type": "rejection",
            "created_at": datetime.utcnow()
        })

    return redirect("/admin/projects")

# ---------------- PROFILE ----------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})

    if request.method == "POST":
        db.users.update_one(
          {"username": session["user"]},
          {"$set": {
            "github": request.form["github"],
            "linkedin": request.form.get("linkedin"),
            "leetcode": request.form.get("leetcode"),
            "instagram": request.form.get("instagram"),
            "bio": request.form["bio"]
          }}
        )
        return redirect("/profile")

    completed = db.submissions.count_documents({"leader": session["user"]})

    return render_template("profile.html", user=user, completed_count=completed)

# ---------------- APPLY REVIEWER ----------------
@app.route("/apply_reviewer")
def apply_reviewer():
    if "user" not in session:
        return redirect("/login")

    completed = db.submissions.count_documents({
        "leader": session["user"]
    })

    if completed < 1:
        return "Complete 1 project first!"

    db.users.update_one(
        {"username": session["user"]},
        {"$set": {"can_review": True}}
    )

    return redirect("/profile")

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("role") != "admin":
        return "Access Denied"

    user = db.users.find_one({"username": session["user"]})

    if request.method == "POST":
        title = request.form["title"]
        file = request.files.get("mdfile")

        content = ""
        if file and file.filename.endswith(".md"):
            content = file.read().decode("utf-8")

        # 🔥 FIX: ALWAYS SET STATUS
        db.projects.insert_one({
            "title": title,
            "content": content,
            "created_by": user["username"],
            "status": "approved",   # ✅ IMPORTANT
            "created_at": datetime.utcnow()
        })

        return redirect("/admin")

    # show only approved here (clean UI)
    projects = list(db.projects.find({
        "status": "approved"
    }))

    return render_template("admin.html", projects=projects, user=user)

# ---------------- TAKE PROJECT ----------------
@app.route("/take/<id>", methods=["GET", "POST"])
def take_project(id):
    if "user" not in session:
        return redirect("/login")

    project = db.projects.find_one({"_id": ObjectId(id)})

    if not project:
        return redirect("/projects")

    # 🔥 BLOCK NON-APPROVED PROJECTS
    if project.get("status") != "approved":
        return redirect("/projects")

    if request.method == "POST":
        team_ids = request.form["team"].split(",")
        team_ids = [tid.strip() for tid in team_ids if tid.strip()]

        user = db.users.find_one({"username": session["user"]})
        current_user_id = user["user_id"]

        team_ids.append(current_user_id)
        team_ids = list(set(team_ids))

        if len(team_ids) > 6:
            return "Max 6 members allowed!"

        valid_team = []
        for tid in team_ids:
            member = db.users.find_one({"user_id": tid})
            if member:
                valid_team.append(tid)

        db.project_enrollments.insert_one({
            "project_id": id,
            "team": valid_team,
            "leader": session["user"],
            "status": "in_progress"
        })

        return redirect("/dashboard")

    html_content = markdown.markdown(project.get("content", ""))
    return render_template("take_project.html", project=project, content=html_content)

# ---------------- SUBMIT ----------------
@app.route("/submit/<id>", methods=["GET", "POST"])
def submit_project(id):
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        # 👤 CURRENT USER
        user = db.users.find_one({"username": session["user"]})
        if not user:
            return "User not found"

        user_id = user["user_id"]

        # 🔍 FIND TEAM (ANY MEMBER CAN SUBMIT NOW)
        enrollment = db.project_enrollments.find_one({
            "project_id": id,
            "team": {"$in": [user_id]}
        })

        if not enrollment:
            return "You are not part of this team!"

        team_ids = enrollment.get("team", [])

        # 🚫 PREVENT DUPLICATE TEAM SUBMISSION
        existing = db.submissions.find_one({
            "project_id": id,
            "team": team_ids
        })

        if existing:
            return "Team already submitted!"

        # ✅ INSERT SUBMISSION
        result = db.submissions.insert_one({
            "project_id": id,
            "leader": enrollment["leader"],  # keep leader info
            "team": team_ids,
            "submitted_by": user_id,  # 🔥 NEW
            "github": request.form["github"],
            "live": request.form["live"],
            "status": "completed",
            "created_at": datetime.utcnow()
        })

        submission_id = str(result.inserted_id)

        # ⚡ GIVE XP TO ALL TEAM MEMBERS
        for member_id in team_ids:
            db.users.update_one(
                {"user_id": member_id},
                {"$inc": {"xp": 20}}
            )

        # 👥 GET TEAM USERNAMES
        team_users = list(db.users.find({
            "user_id": {"$in": team_ids}
        }))
        team_usernames = [u["username"] for u in team_users]

        # 🧑‍⚖️ ASSIGN REVIEWERS
        reviewers = list(db.users.find({
            "can_review": True,
            "username": {"$nin": team_usernames}
        }))

        if reviewers:
            selected = random.sample(reviewers, min(2, len(reviewers)))

            for r in selected:
                db.reviews.insert_one({
                    "project_id": id,
                    "submission_id": submission_id,
                    "reviewer": r["username"],
                    "score": None,
                    "feedback": "",
                    "status": "pending"
                })

        return redirect("/dashboard")

    return render_template("submit.html", project_id=id)

# ---------------- REVIEWS ----------------
@app.route("/reviews")
def reviews():
    if session.get("role") != "reviewer":
        return "Access Denied"

    assigned = list(db.reviews.find({
        "reviewer": session["user"]
    }))

    open_reviews = list(db.reviews.find({
        "status": "pending"
    }))

    return render_template("reviews.html",
                           reviews=assigned,
                           open_reviews=open_reviews)

# ---------------- TAKE REVIEW ----------------
@app.route("/take_review/<id>")
def take_review(id):
    if session.get("role") != "reviewer":
        return "Access Denied"

    db.reviews.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"reviewer": session["user"]}}
    )

    return redirect("/reviews")

# ---------------- REVIEW FORM ----------------
@app.route("/review/<id>", methods=["GET", "POST"])
def review_project(id):
    if session.get("role") != "reviewer":
        return "Access Denied"

    review = db.reviews.find_one({"_id": ObjectId(id)})

    if not review:
        return "Review not found"

    # 🔒 ensure only assigned reviewer can open
    if review["reviewer"] != session["user"]:
        return "This review is not assigned to you!"

    submission = db.submissions.find_one({"_id": ObjectId(review["submission_id"])})
    project = db.projects.find_one({"_id": ObjectId(review["project_id"])})

    if request.method == "POST":

        # ✅ SAVE REVIEW
        db.reviews.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "score": int(request.form["score"]),
                "feedback": request.form["feedback"],
                "status": "done"
            }}
        )

        # 🔥 GET UPDATED SUBMISSION
        submission = db.submissions.find_one({"_id": ObjectId(review["submission_id"])})

        if not submission:
            return redirect("/reviews")

        # ⚡ GIVE XP ONLY ONCE
        if not submission.get("xp_awarded"):

            team_ids = submission.get("team", [])

            for member_id in team_ids:
                db.users.update_one(
                    {"user_id": member_id},
                    {"$inc": {"xp": 20}}
                )

            db.submissions.update_one(
                {"_id": submission["_id"]},
                {"$set": {"xp_awarded": True}}
            )

        return redirect("/reviews")

    return render_template(
        "review_form.html",
        review=review,
        submission=submission,
        project=project
    )

# ---------------- MY PROJECTS ----------------
@app.route("/projects")
def projects_page():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})
    user_id = user["user_id"]

    # 🔍 SEARCH
    query = request.args.get("q", "").strip()

    # 🏷 FILTER
    filter_type = request.args.get("filter", "all")

    # 🔥 BASE FILTER (ONLY APPROVED PROJECTS)
    search_filter = {
    "status": {"$eq": "approved"}
    }

    # 🔍 ADD SEARCH ON TOP
    if query:
        search_filter["title"] = {"$regex": query, "$options": "i"}

    # 🔥 GET ONLY APPROVED PROJECTS
    all_projects = list(db.projects.find(search_filter))

    # 📦 USER STATUS (taken / completed)
    enrollments = list(db.project_enrollments.find({
        "team": {"$in": [user_id]}
    }))

    project_status_map = {}

    for e in enrollments:
        submission = db.submissions.find_one({
            "project_id": e["project_id"],
            "team": e["team"]
        })

        if submission:
            project_status_map[e["project_id"]] = "completed"
        else:
            project_status_map[e["project_id"]] = "in_progress"

    # 🎯 FINAL PROJECT LIST
    projects = []

    for p in all_projects:
        pid = str(p["_id"])
        status = project_status_map.get(pid, "not_taken")

        # 🎯 FILTER (UI filter like completed / in_progress)
        if filter_type != "all" and status != filter_type:
            continue

        projects.append({
            "_id": p["_id"],
            "title": p["title"],
            "description": p.get("content", "")[:120],
            "status": status,
            "creator": p.get("created_by", "BuildHub")
        })

    return render_template(
        "projects.html",
        projects=projects,
        query=query,
        current_filter=filter_type,
        user=user   # 🔥 IMPORTANT (prevents template crash)
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})

    if request.method == "POST":
        db.users.update_one(
            {"username": session["user"]},
            {"$set": {
                "is_public": request.form.get("is_public") == "on",
                "theme": request.form.get("theme")
            }}
        )
        return redirect("/settings")

    return render_template("settings.html", user=user)

@app.route("/docs")
def docs():
    return render_template("docs.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ---------------- STARTER ----------------
@app.route('/starter')
@login_required
def starter():
    content_type = request.args.get("type", "github")

    user = db.users.find_one({"username": session["user"]})

    # 🔥 SAFE FALLBACK
    if "progress" not in user:
        db.users.update_one(
            {"username": session["user"]},
            {"$set": {
                "progress": {
                    "github": False,
                    "project": False,
                    "linkedin": False,
                    "linkedin_link": ""
                }
            }}
        )
        user = db.users.find_one({"username": session["user"]})

    progress = user.get("progress", {})

    github_done = progress.get("github", False)
    project_done = progress.get("project", False)

    # 🔓 UNLOCK
    if content_type == "project" and not github_done:
        return redirect("/starter?type=github")

    if content_type == "linkedin" and not project_done:
        return redirect("/starter?type=project")

    file_map = {
        "github": "templates/content/github.md",
        "linkedin": "templates/content/linkedin.md",
        "project": "templates/content/project.md"
    }

    file_path = file_map.get(content_type)

    html_content = "<p>Content not found</p>"

    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        html_content = markdown.markdown(
            md_content,
            extensions=["fenced_code", "tables"]
        )

    return render_template(
        "starter.html",
        content=html_content,
        current=content_type,
        github_done=github_done,
        project_done=project_done
    )

# ---------------- COMPLETE ----------------
@app.route("/complete/github")
@login_required
def complete_github():
    db.users.update_one(
        {"username": session["user"]},
        {"$set": {"progress.github": True}}
    )
    return redirect("/starter?type=project")

@app.route("/complete/project")
@login_required
def complete_project():
    db.users.update_one(
        {"username": session["user"]},
        {"$set": {"progress.project": True}}
    )
    return redirect("/starter?type=linkedin")

@app.route("/submit/linkedin", methods=["POST"])
@login_required
def submit_linkedin():
    link = request.form.get("link")

    user = db.users.find_one({"username": session["user"]})
    progress = user.get("progress", {})

    db.users.update_one(
        {"username": session["user"]},
        {"$set": {
            "progress.linkedin": True,
            "progress.linkedin_link": link
        }}
    )

    # 🔥 GIVE BADGE (ONLY IF NOT ALREADY)
    if not any(b["name"] == "Starter" for b in user.get("badges", [])):
        db.users.update_one(
            {"username": session["user"]},
            {"$push": {
                "badges": {
                    "name": "Starter",
                    "icon": "starter.png",
                    "description": "Completed Getting Started"
                }
            }}
        )

    return redirect("/dashboard")

@app.route("/update_theme", methods=["POST"])
def update_theme():
    if "user" not in session:
        return {"status": "error"}

    data = request.get_json()

    db.users.update_one(
        {"username": session["user"]},
        {"$set": {"theme": data["theme"]}}
    )

    return {"status": "ok"}


@app.route("/leaderboard")
@login_required
def leaderboard():

    users = list(db.users.find())

    leaderboard_data = []

    for u in users:
        completed = db.submissions.count_documents({
            "leader": u["username"],
            "status": "completed"
        })

        leaderboard_data.append({
            "username": u["username"],
            "xp": u.get("xp", 0),
            "completed": completed
        })

    leaderboard_data.sort(key=lambda x: (-x["xp"], -x["completed"]))

    return render_template("leaderboard.html", users=leaderboard_data)

@app.context_processor
def inject_user():
    if "user" in session:
        user = db.users.find_one({"username": session["user"]})
        return dict(user=user)
    return dict(user=None)
# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/u/<username>")
def public_profile(username):
    # 🔍 find user
    user = db.users.find_one({"username": username})

    if not user:
        return "User not found"

    viewer = session.get("user")

    # 🔒 PRIVACY CHECK
    if not user.get("is_public", False) and viewer != username:
        return "This profile is private"

    user_id = user.get("user_id")

    # 📊 COMPLETED PROJECTS (TEAM BASED FIX)
    completed_count = db.submissions.count_documents({
        "team": {"$in": [user_id]},
        "status": "completed"
    })

    # 🔥 OPTIONAL (GOOD UX): total submissions
    total_submissions = db.submissions.count_documents({
        "team": {"$in": [user_id]}
    })

    # 🏆 badges count
    badges = user.get("badges", [])

    return render_template(
        "public_profile.html",
        user=user,
        completed_count=completed_count,
        total_submissions=total_submissions,
        badges=badges
    )

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

@app.route("/delete_notification/<id>", methods=["POST"])
def delete_notification(id):
    if "user" not in session:
        return {"status": "error"}

    db.notifications.delete_one({"_id": ObjectId(id)})

    return {"status": "ok"}
# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
