from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
from bson.objectid import ObjectId
import uuid
import os
import markdown
import random

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DB ----------------
client = MongoClient("mongodb+srv://charanachanta2:Charan1114@cluster0.ysxk5ry.mongodb.net/")
db = client["buildhub"]

# ---------------- CREATE ADMIN ----------------
if not db.users.find_one({"username": "admin"}):
    db.users.insert_one({
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "user_id": "BHADMIN",
        "github": "",
        "bio": "",
        "can_review": True
    })

# ---------------- HOME ----------------
@app.route("/")
def landing():
    return render_template("index.html")

@app.route("/home")
def home():
    return redirect("/login")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db.users.insert_one({
            "username": request.form["username"],
            "password": request.form["password"],
            "user_id": "BH" + str(uuid.uuid4())[:6],
            "github": "",
            "bio": "",
            "role": "user",
            "can_review": False
        })
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # REVIEWER LOGIN
        if username.endswith(".rev"):
            base = username.replace(".rev", "")
            user = db.users.find_one({"username": base, "password": password})

            if user and user.get("can_review", False):
                session["user"] = base
                session["role"] = "reviewer"
                return redirect("/reviews")
            else:
                return "Not eligible for reviewer!"

        user = db.users.find_one({"username": username, "password": password})
        if user:
            session["user"] = username
            session["role"] = user.get("role", "user")
            return redirect("/dashboard")

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})

    if "user_id" not in user:
        new_id = "BH" + str(uuid.uuid4())[:6]
        db.users.update_one({"_id": user["_id"]}, {"$set": {"user_id": new_id}})
        user["user_id"] = new_id

    notifications = list(db.notifications.find({
        "user_id": user["user_id"],
        "seen": False
    }))

    projects = list(db.projects.find())

    return render_template("dashboard.html", projects=projects, notifications=notifications)

# ---------------- NOTIFICATIONS ----------------
@app.route("/get_notifications")
def get_notifications():
    if "user" not in session:
        return {"notifications": []}

    user = db.users.find_one({"username": session["user"]})

    notes = list(db.notifications.find({
        "user_id": user["user_id"],
        "seen": False
    }))

    for n in notes:
        n["_id"] = str(n["_id"])

    return {"notifications": notes}

# ---------------- PROJECT ----------------
@app.route("/project/<id>")
def project(id):
    project = db.projects.find_one({"_id": ObjectId(id)})

    html_content = markdown.markdown(
        project.get("content", ""),
        extensions=["fenced_code", "tables"]
    )

    reviews = list(db.reviews.find({
        "project_id": id,
        "status": "done"
    }))

    scores = [r["score"] for r in reviews if r.get("score")]
    avg_score = sum(scores)/len(scores) if scores else 0

    return render_template("project.html",
                           project=project,
                           content=html_content,
                           reviews=reviews,
                           avg_score=avg_score)

# ---------------- PROFILE ----------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})

    if request.method == "POST":
        db.users.update_one(
            {"username": session["user"]},
            {"$set": {
                "github": request.form["github"],
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

    if request.method == "POST":
        title = request.form["title"]
        file = request.files.get("mdfile")

        content = ""
        if file and file.filename:
            content = file.read().decode("utf-8")

        db.projects.insert_one({
            "title": title,
            "content": content
        })

        return redirect("/admin")

    projects = list(db.projects.find())
    return render_template("admin.html", projects=projects)

# ---------------- TAKE PROJECT ----------------
@app.route("/take/<id>", methods=["GET", "POST"])
def take_project(id):
    if "user" not in session:
        return redirect("/login")

    project = db.projects.find_one({"_id": ObjectId(id)})

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

                if tid != current_user_id:
                    db.notifications.insert_one({
                        "user_id": tid,
                        "message": f"{session['user']} added you to a project",
                        "project_id": id,
                        "seen": False
                    })

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

        enrollment = db.project_enrollments.find_one({
            "project_id": id,
            "leader": session["user"]
        })

        team_ids = enrollment.get("team", [])

        # prevent duplicate submission
        existing = db.submissions.find_one({
            "project_id": id,
            "team": team_ids
        })

        if existing:
            return "Team already submitted!"

        result = db.submissions.insert_one({
            "project_id": id,
            "leader": session["user"],
            "team": team_ids,
            "github": request.form["github"],
            "live": request.form["live"]
        })

        submission_id = str(result.inserted_id)

        # team usernames
        team_users = list(db.users.find({
            "user_id": {"$in": team_ids}
        }))
        team_usernames = [u["username"] for u in team_users]

        # valid reviewers
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
    submission = db.submissions.find_one({"_id": ObjectId(review["submission_id"])})
    project = db.projects.find_one({"_id": ObjectId(review["project_id"])})

    if request.method == "POST":
        db.reviews.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "score": int(request.form["score"]),
                "feedback": request.form["feedback"],
                "status": "done"
            }}
        )
        return redirect("/reviews")

    return render_template("review_form.html",
                           review=review,
                           submission=submission,
                           project=project)

# ---------------- MY PROJECTS ----------------
@app.route("/my_projects")
def my_projects():
    if "user" not in session:
        return redirect("/login")

    user = db.users.find_one({"username": session["user"]})
    user_id = user["user_id"]

    enrollments = list(db.project_enrollments.find({
        "team": {"$in": [user_id]}
    }))

    projects = []
    for e in enrollments:
        proj = db.projects.find_one({"_id": ObjectId(e["project_id"])})
        if proj:
            proj["status"] = e["status"]
            projects.append(proj)

    return render_template("my_projects.html", projects=projects)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
