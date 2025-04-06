from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session

from models import db, User, Group, GroupMember, Expense, ExpenseSplit
from helper import login_required
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'money_split.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Secret key for sessions
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db.init_app(app)

# Function to execute raw SQL queries
def execute_query(query, params=()):
    with db.engine.connect() as connection:
        return connection.execute(query, params)


@app.route('/')
@login_required
def index():
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect("/login")

    user_id = session.get("user_id")
    user = User.query.get(user_id)

    groups = user.groups

    # Calculate overall balance
    all_splits = ExpenseSplit.query.join(Expense).filter(ExpenseSplit.user_id == user_id).all()
    net_balance = sum(split.paid_share - split.owed_share for split in all_splits)

    # Per-group balances
    group_balances = {}
    for group in groups:
        group_splits = ExpenseSplit.query \
            .join(Expense) \
            .filter(Expense.group_id == group.id, ExpenseSplit.user_id == user_id) \
            .all()

        balance = sum(split.paid_share - split.owed_share for split in group_splits)
        group_balances[group.id] = balance

    return render_template(
        "index.html",
        groups=groups,
        net_balance=net_balance,
        group_balances=group_balances
    )


# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('fullname')
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # Check if username exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists. Try another one.", "danger")
            return redirect("/register")

        if password != confirmation:
            flash("Passwords do not match.", "danger")
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        new_user = User(name=name, username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect("/login")

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username:
            flash("Please enter username", "danger")
            return redirect("/login")
        if not password:
            flash("Please enter password", "danger")
            return redirect("/login")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Login successful!", "success")
            return redirect("/")
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')

# Logout Route
@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route('/create-group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        current_user_id = session.get('user_id')

        if not group_name:
            flash("Group name cannot be empty.", "danger")
            return redirect('/create_group')

        # Create new group
        new_group = Group(name=group_name)
        db.session.add(new_group)
        db.session.commit()

        # Add current user as a member
        membership = GroupMember(user_id=current_user_id, group_id=new_group.id)
        db.session.add(membership)
        db.session.commit()

        flash(f'Group "{group_name}" created successfully!', "success")
        return redirect("/")

    return render_template('create_group.html')


@app.route('/invite-friends/<int:group_id>', methods=['GET', 'POST'])
@login_required
def invite_friends(group_id):
    group = Group.query.get_or_404(group_id)

    # Get current members (so they aren't re-added)
    current_members_ids = [member.id for member in group.users]

    # Get all users except current members
    users = User.query.filter(User.id.notin_(current_members_ids)).all()

    if request.method == 'POST':
        selected_user_ids = request.form.getlist('user_ids')

        for user_id in selected_user_ids:
            new_member = GroupMember(user_id=int(user_id), group_id=group.id)
            db.session.add(new_member)

        db.session.commit()
        flash("Friends successfully invited!", "success")
        return redirect("/")

    return render_template('invite_friends.html', group=group, users=users, members=group.users)


@app.route('/group/<int:group_id>')
@login_required
def group_page(group_id):
    group = Group.query.get_or_404(group_id)

    # Ensure current user is a member
    current_user_id = session.get("user_id")
    if current_user_id not in [u.id for u in group.users]:
        flash("You do not have access to this group.", "danger")
        return redirect("/")

    # List of expenses
    expenses = Expense.query.filter_by(group_id=group.id).order_by(Expense.timestamp.desc()).all()

    # Calculate outstanding balance in this group
    balance = 0.0
    for expense in expenses:
        for split in expense.splits:
            if split.user_id == current_user_id:
                balance -= split.amount
        if expense.paid_by_id == current_user_id:
            balance += expense.amount

    return render_template("group.html", group=group, expenses=expenses, balance=balance)


@app.route("/group/<int:group_id>/add_expense", methods=["GET", "POST"])
def add_group_expense(group_id):
    group = Group.query.get_or_404(group_id)
    members = GroupMember.query.filter_by(group_id=group_id).all()
    users = [db.session.get(User, member.user_id) for member in members]

    if request.method == "POST":
        description = request.form.get("description")
        amount = float(request.form.get("amount"))
        payer_id = session["user_id"]

        # Create Expense record
        expense = Expense(description=description, amount=amount, paid_by_id=payer_id, group_id=group_id)
        db.session.add(expense)
        db.session.flush() 

        total_split = 0
        for user in users:
            share = float(request.form.get(f"user_{user.id}", 0))
            if share > 0:
                split = ExpenseSplit(expense_id=expense.id, user_id=user.id, amount=share)
                db.session.add(split)
                total_split += share

        if round(total_split, 2) != round(amount, 2):
            db.session.rollback()
            flash("Split amounts must add up to the total expense.", "danger")
            return redirect(request.url)

        db.session.commit()
        flash("Expense added successfully!", "success")
        return redirect(url_for("group_page", group_id=group_id))

    return render_template("add_group_expense.html", group=group, users=users)


@app.route("/add_personal_expense", methods=["GET", "POST"])
def add_personal_expense():
    current_user_id = session.get("user_id")
    if not current_user_id:
        flash("Please log in first.", "danger")
        return redirect("/login")

    users = User.query.filter(User.id != current_user_id).all()

    if request.method == "POST":
        description = request.form.get("description")
        amount = float(request.form.get("amount"))
        other_user_id = int(request.form.get("other_user_id"))
        payer_id = current_user_id

        try:
            payer_share = float(request.form.get("payer_share"))
            other_share = float(request.form.get("other_share"))
        except (ValueError, TypeError):
            flash("Please enter valid share values.", "danger")
            return redirect(request.url)

        if round(payer_share + other_share, 2) != round(amount, 2):
            flash("The split amounts must total the expense amount.", "danger")
            return redirect(request.url)

        # Create personal expense (no group_id)
        expense = Expense(description=description, amount=amount, payer_id=payer_id, group_id=None)
        db.session.add(expense)
        db.session.flush()

        db.session.add(ExpenseSplit(expense_id=expense.id, user_id=payer_id, amount_owed=payer_share))
        db.session.add(ExpenseSplit(expense_id=expense.id, user_id=other_user_id, amount_owed=other_share))

        db.session.commit()
        flash("Personal expense added!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_personal_expense.html", users=users)


@app.route('/history')
@login_required
def activity():
    user_id = session["user_id"]

    # Expenses paid by user
    paid_expenses = Expense.query.filter_by(paid_by_id=user_id).all()

    # Expenses where user owes (in splits)
    split_ids = db.session.query(ExpenseSplit.expense_id).filter_by(user_id=user_id).distinct()
    split_expenses = Expense.query.filter(Expense.id.in_(split_ids)).all()

    # Combine and remove duplicates
    all_expenses = {exp.id: exp for exp in paid_expenses + split_expenses}.values()

    # Sort by timestamp descending
    sorted_expenses = sorted(all_expenses, key=lambda e: e.timestamp, reverse=True)

    return render_template("activity.html", expenses=sorted_expenses, user_id=user_id)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)


