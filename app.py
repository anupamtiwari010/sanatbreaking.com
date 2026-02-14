from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

# =====================
# CONFIG
# =====================
DATABASE = "database.db"
UPLOAD_FOLDER = "uploads/news"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =====================
# DB CONNECTION
# =====================
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =====================
# HOME PAGE
# =====================
@app.route("/")
def home():
    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    db = get_db()

    news = db.execute(
        "SELECT * FROM news ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()

    total = db.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    total_pages = (total + per_page - 1) // per_page

    categories = db.execute(
        "SELECT DISTINCT category FROM news"
    ).fetchall()

    recent = db.execute(
        "SELECT id, title, image, video FROM news ORDER BY id DESC LIMIT 5"
    ).fetchall()

    breaking = db.execute(
        "SELECT id, title FROM news WHERE is_breaking=1 ORDER BY id DESC"
    ).fetchall()

    db = get_db()

    # Category with post count
    cat_counts = db.execute("""
    SELECT category, COUNT(*) as total
    FROM news
    GROUP BY category
    ORDER BY total DESC
    """).fetchall()

    return render_template(
        "index.html",
        news=news,
        categories=categories,
        recent=recent,
        breaking=breaking,
        page=page,
        total_pages=total_pages,
        cat_counts=cat_counts
    )

@app.route("/about")
def about():
    return render_template("about.html")



# =====================
# CATEGORY PAGE
# =====================
@app.route("/category/<category>")
def category(category):
    page = request.args.get("page", 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page

    db = get_db()

    news = db.execute(
        "SELECT * FROM news WHERE category=? ORDER BY id DESC LIMIT ? OFFSET ?",
        (category, per_page, offset)
    ).fetchall()

    total = db.execute(
        "SELECT COUNT(*) FROM news WHERE category=?",
        (category,)
    ).fetchone()[0]

    total_pages = (total + per_page - 1) // per_page

    categories = db.execute(
        "SELECT DISTINCT category FROM news"
    ).fetchall()

    recent = db.execute(
        "SELECT id, title, image, video FROM news ORDER BY id DESC LIMIT 5"
    ).fetchall()

    breaking = db.execute(
        "SELECT id, title FROM news WHERE is_breaking=1 ORDER BY id DESC"
    ).fetchall()

    # ✅ ADD THIS (IMPORTANT)
    cat_counts = db.execute("""
        SELECT category, COUNT(*) as total
        FROM news
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    return render_template(
        "index.html",
        news=news,
        categories=categories,
        recent=recent,
        breaking=breaking,
        page=page,
        total_pages=total_pages,
        current_category=category,
        cat_counts=cat_counts   # ✅ ADD THIS
    )



# =====================
# SINGLE NEWS
# =====================
@app.route("/news/<int:id>")
def single(id):
    db = get_db()

    # Single news
    news = db.execute(
        "SELECT * FROM news WHERE id=?",
        (id,)
    ).fetchone()

    # Sidebar data (same as home)
    categories = db.execute(
        "SELECT DISTINCT category FROM news"
    ).fetchall()

    recent = db.execute(
        "SELECT id, title, image, video FROM news ORDER BY id DESC LIMIT 5"
    ).fetchall()

    breaking = db.execute(
        "SELECT id, title FROM news WHERE is_breaking=1 ORDER BY id DESC"
    ).fetchall()

    cat_counts = db.execute("""
        SELECT category, COUNT(*) as total
        FROM news
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    return render_template(
        "single.html",
        news=news,
        categories=categories,
        recent=recent,
        breaking=breaking,
        cat_counts=cat_counts   # ✅ IMPORTANT
    )



# =====================
# NEWSLETTER SUBSCRIBE (FIXED)
# =====================
@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email")

    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO newsletter (email) VALUES (?)",
        (email,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


# =====================
# ADMIN LOGIN
# =====================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        admin = db.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if admin:
            session["admin"] = True
            return redirect(url_for("dashboard"))

    return render_template("admin_login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    db = get_db()
    news = db.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    return render_template("admin.html", news=news)


# =====================
# ADD NEWS
# =====================
@app.route("/add-news", methods=["GET", "POST"])
def add_news():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        video = request.form.get("video")
        is_breaking = 1 if request.form.get("is_breaking") else 0

        # ✅ AUTO CONVERT VIDEO LINKS (FB + YOUTUBE)
        if video:
            import urllib.parse

            # Facebook normal URL → embed
            if "facebook.com" in video and "plugins/video.php" not in video:
                encoded = urllib.parse.quote(video, safe='')
                video = f"https://www.facebook.com/plugins/video.php?href={encoded}"

            # YouTube normal URL → embed
            if "youtube.com/watch" in video:
                vid = video.split("v=")[-1].split("&")[0]
                video = f"https://www.youtube.com/embed/{vid}"

            if "youtu.be/" in video:
                vid = video.split("/")[-1]
                video = f"https://www.youtube.com/embed/{vid}"

        # ✅ IMAGE UPLOAD
        image = None
        file = request.files.get("image")
        if file and "." in file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image = filename

        db = get_db()
        db.execute(
            """INSERT INTO news
               (title, content, category, image, video, is_breaking)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, content, category, image, video, is_breaking)
        )
        db.commit()

        return redirect(url_for("dashboard"))

    return render_template("admin.html")


# =====================
# EDIT NEWS
# =====================
@app.route("/edit-news/<int:id>", methods=["GET", "POST"])
def edit_news(id):
    if not session.get("admin"):
        return redirect(url_for("admin"))

    db = get_db()
    news = db.execute("SELECT * FROM news WHERE id=?", (id,)).fetchone()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form["category"]
        video = request.form.get("video")
        is_breaking = 1 if request.form.get("is_breaking") else 0

        # ✅ AUTO CONVERT VIDEO LINKS (FB + YOUTUBE)
        if video:
            import urllib.parse

            # Facebook normal URL → embed
            if "facebook.com" in video and "plugins/video.php" not in video:
                encoded = urllib.parse.quote(video, safe='')
                video = f"https://www.facebook.com/plugins/video.php?href={encoded}"

            # YouTube normal URL → embed
            if "youtube.com/watch" in video:
                vid = video.split("v=")[-1].split("&")[0]
                video = f"https://www.youtube.com/embed/{vid}"

            if "youtu.be/" in video:
                vid = video.split("/")[-1]
                video = f"https://www.youtube.com/embed/{vid}"

        # ✅ IMAGE UPLOAD
        image = news["image"]
        file = request.files.get("image")

        if file and "." in file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image = filename

        db.execute("""
            UPDATE news SET 
            title=?, content=?, category=?, image=?, video=?, is_breaking=?
            WHERE id=?
        """, (title, content, category, image, video, is_breaking, id))

        db.commit()
        return redirect(url_for("dashboard"))

    return render_template("edit_news.html", news=news)



@app.route("/contact", methods=["GET", "POST"])
def contact():
    success = False

    if request.method == "POST":
        name = request.form["name"]
        mobile = request.form["mobile"]
        message = request.form["message"]

        db = get_db()
        db.execute(
            "INSERT INTO contact (name, mobile, message) VALUES (?, ?, ?)",
            (name, mobile, message)
        )
        db.commit()

        success = True

    return render_template("contact.html", success=success)





@app.route("/delete-news/<int:id>")
def delete_news(id):
    if not session.get("admin"):
        return redirect(url_for("admin"))

    db = get_db()

    # delete image file
    news = db.execute("SELECT image FROM news WHERE id=?", (id,)).fetchone()
    if news and news["image"]:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], news["image"]))
        except:
            pass

    db.execute("DELETE FROM news WHERE id=?", (id,))
    db.commit()

    return redirect(url_for("dashboard"))



@app.route("/videos")
def videos():
    db = get_db()

    videos = db.execute("""
        SELECT id, title, video
        FROM news
        WHERE video IS NOT NULL AND video != ''
        ORDER BY id DESC
        LIMIT 3
    """).fetchall()

    return render_template("video.html", videos=videos)




# =====================
# UPLOADED IMAGE ROUTE
# =====================
@app.route("/uploads/news/<filename>")
def uploaded_image(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# =====================
# LOGOUT
# =====================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =====================
# RUN
# =====================
if __name__ == "__main__":
    app.run(debug=True)



