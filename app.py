import os
import sqlite3 
from pathlib import Path
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "local-classroom-demo-key"
)

BASE_DIR = Path(__file__).resolve().parent

DATABASE = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "instance" / "events.db")
    )
)

EVENTS = [
    "Code Sprint",
    "AI Innovative",
    "Cyber Challenges",
    "Project pitch",
    "Robo creative"
]

def get_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row 
    return connection

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS registration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                department TEXT NOT NULL,
                year TEXT NOT NULL,
                event TEXT NOT NULL,
                status TEXT DEFAULT 'Registered',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email, event)
            )
        """)

init_db()

@app.route('/')
def home():
    with get_db() as db:
        total = db.execute(
            "SELECT COUNT(*) FROM registration"
        ).fetchone()[0]

        event_count = db.execute(
            "SELECT COUNT(DISTINCT event) FROM registration"
        ).fetchone()[0]

    return render_template(
        "index.html",
        total=total,
        event_count=event_count,
        events=EVENTS
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "").strip()
        event = request.form.get("event", "").strip()

        print(f"DEBUG DATA -> Name: '{name}', Email: '{email}', Dept: '{department}', Year: '{year}', Event: '{event}'", flush=True)

        if not all([name, email, department, year, event]):
            flash("All fields are required!")
            return redirect(url_for('register'))

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address containing '@' and '.'.")
            return redirect(url_for('register'))

        valid_years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
        if year not in valid_years:
            flash("Invalid academic year. Please select 1st, 2nd, 3rd, or 4th.")
            return redirect(url_for('register'))

        if event not in EVENTS:
            flash("Invalid event selected. Please choose from the official list.")
            return redirect(url_for('register'))

        try:
            with get_db() as db:
                db.execute("""
                    INSERT INTO registration (name, email, department, year, event)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, email, department, year, event))
                db.commit()
            
            flash(f"Successfully registered for {event}!")
            return redirect(url_for('home'))
            
        except sqlite3.IntegrityError:
            flash(f"Error: {email} is already registered for {event}.")
            return redirect(url_for('register'))
    
    return render_template('register.html', events=EVENTS)

@app.route('/admin')
def admin():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')

    with get_db() as db:
        # 1. Top Stats Cards
        total = db.execute("SELECT COUNT(*) FROM registration").fetchone()[0]
        registered = db.execute("SELECT COUNT(*) FROM registration WHERE status = 'Registered'").fetchone()[0]
        attended = db.execute("SELECT COUNT(*) FROM registration WHERE status = 'Attended'").fetchone()[0]

        # 2. Event Summary List
        event_stats = db.execute("""
            SELECT event, COUNT(*) as count 
            FROM registration GROUP BY event
        """).fetchall()

        # 3. Main Table Search & Filter Logic
        query = "SELECT * FROM registration WHERE 1=1"
        params = []

        if search_query:
            query += " AND (name LIKE ? OR email LIKE ? OR department LIKE ? OR event LIKE ?)"
            search_param = f"%{search_query}%"
            params.extend([search_param, search_param, search_param, search_param])
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
            
        query += " ORDER BY registered_at DESC"
        
        registrations = db.execute(query, params).fetchall()

    return render_template(
        'admin.html',
        total=total,
        registered=registered,
        attended=attended,
        event_stats=event_stats,
        registrations=registrations,
        search=search_query,
        status_filter=status_filter
    )



@app.route("/health")
def health():
    try:
        with get_db() as db:
            db.execute("SELECT 1")
            
        return jsonify(
            status="ok",
            application="management"
        )
    except Exception as e:
        return jsonify(
            status="error",
            application="management",
            message=str(e)
        ), 500

# ... your other routes above ...

@app.route('/admin/update_status/<int:registration_id>', methods=['POST'])
def update_status(registration_id):
    new_status = request.form.get('status')
    if new_status in ['Registered', 'Attended', 'Cancelled']:
        with get_db() as db:
            db.execute("UPDATE registration SET status = ? WHERE id = ?", (new_status, registration_id))
            db.commit()
        flash(f"Status updated to {new_status}.", "success")
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:registration_id>', methods=['POST'])
def delete_registration(registration_id):
    with get_db() as db:
        db.execute("DELETE FROM registration WHERE id = ?", (registration_id,))
        db.commit()
    flash("Registration deleted.", "success")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
        

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
