from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_split.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Secret key for sessions

db = SQLAlchemy(app)

# Function to execute raw SQL queries
def execute_query(query, params=()):
    with db.engine.connect() as connection:
        return connection.execute(query, params)

# Home Page (Only accessible if logged in)
@app.route('/')
def index():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect("/login")
    
    return render_template('home.html', username=session["username"])

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Insert user into database
        try:
            execute_query("INSERT INTO users (name, username, password) VALUES (?, ?, ?)",
                          (name, username, hashed_password))
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except:
            flash("Username already exists. Try another one.", "danger")

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = execute_query("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route('/groups')
def groups():
    return redirect("/")


@app.route('/history')
def history():
    return redirect("/")

if __name__ == '__main__':
    app.run(debug=True)


