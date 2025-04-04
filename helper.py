from functools import wraps
from flask import redirect, session, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to view this page.", "danger")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function
