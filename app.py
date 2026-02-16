from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

# =====================
# CONFIG
# =====================
UPLOAD_FOLDER = "uploads/news"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =====================
# DB CONNECTION (PostgreSQL)
# =====================
def get_db():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


# =====================
# HOME PAGE
# =====================
@app.route("/")
def home():
    page = request.args.get("page", 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM news ORDER BY id DESC LIMIT %s OFFSET %s", (per_page, offset))
    news = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM news")
    total = cur.fetchone()["count"]
    total_pages = (total + per_page - 1) // per_page

    cur.execute("SELECT id, title, image, video FROM news ORDER BY id DESC LIMIT 5")
    recent = cur.fetchall()

    cur.execute("SELECT id, title FROM news WHERE is_breaking=1 ORDER BY id DESC")
    breaking = cur.fetchall()

    cur.execute("""
        SELECT category, COUNT(*) as total
        FROM news
        GROUP BY category
        ORDER BY total DESC
    """)
    cat_counts = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "index.html",
        news=news,
        recent=recent,
        breaking=breaking,
        page=page,
        total_pages=total_pages,
        cat_counts=cat_counts
    )


# =====================
# CATEGORY PAGE
# =====================
@app.route("/category/<category>")
def category(category):
    page = request.args.get("page", 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM news WHERE category=%s ORDER BY id DESC LIMIT %s OFFSET %s",
                (category, per_page, offset))
    news = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM news WHERE category=%s", (category,))
    total = cur.fetchone()["count"]
    total_pages = (total + per_page - 1) // per_page

    cur.execute("""
        SELECT category, COUNT(*) as total
        FROM news
        GROUP BY category
        ORDER BY total DESC
    """)
    cat_counts = cur.fetchall()

    cur.execute("SELECT id, title FROM news WHERE is_breaking=1 ORDER BY id DESC")
    breaking = cur.fetchall()

    cur.execute("SELECT id, title, image, video FROM news ORDER BY id DESC LIMIT 5")
    recent = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "index.html",
        news=news,
        page=page,
        total_pages=total_pages,
        current_category=category,
        cat_counts=cat_counts,
        breaking=breaking,
        recent=recent
    )


# =====================
# SINGLE NEWS
# =====================
@app.route("/news/<int:id>")
def single(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM news WHERE id=%s", (id,))
    news = cur.fetchone()

    cur.execute("SELECT id, title, image, video FROM news ORDER BY id DESC LIMIT 5")
    recent = cur.fetchall()

    cur.execute("SELECT id, title FROM news WHERE is_breaking=1 ORDER BY id DESC")
    breaking = cur.fetchall()

    cur.execute("""
        SELECT category, COUNT(*) as total
        FROM news
        GROUP BY category
        ORDER BY total DESC
    """)
    cat_counts = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("single.html",
                           news=news,
                           recent=recent,
                           breaking=breaking,
                           cat_counts=cat_counts)


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

        image = None
        file = request.files.get("image")
        if file and "." in file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image = filename

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO news (title, content, category, image, video, is_breaking)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, content, category, image, video, is_breaking))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("dashboard"))

    return render_template("admin.html")


# =====================
# ADMIN LOGIN
# =====================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s",
                    (username, password))
        admin_user = cur.fetchone()

        cur.close()
        conn.close()

        if admin_user:
            session["admin"] = True
            return redirect(url_for("dashboard"))

    return render_template("admin_login.html")


# =====================
# DASHBOARD
# =====================
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM news ORDER BY id DESC")
    news = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("admin.html", news=news)


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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
