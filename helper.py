from functools import wraps
from flask import redirect, session, flash, current_app


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to view this page.", "danger")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def currency(amount, currency_code=None):
    symbols = {
        "USD": "$",
        "EUR": "€",
        "INR": "₹",
        "GBP": "£",
        "JPY": "¥",
    }
    currency_code = (currency_code or 
                     current_app.config.get("DEFAULT_CURRENCY", "USD")).upper()
    symbol = symbols.get(currency_code, "")
  
    return f"{symbol}{amount:,.2f}"
