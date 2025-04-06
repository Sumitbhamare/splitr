from flask import Flask, render_template, redirect, url_for, flash
from flask import request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session

from models import (
    db, User, Group, GroupMember, Expense, ExpenseSplit, Friendship)
from helper import login_required
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = \
    f"sqlite:///{os.path.join(basedir, 'money_split.db')}"
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

    # GROUPS SECTION
    groups = user.groups
    net_balance = 0.0
    group_balances = {}

    for group in groups:
        expenses = Expense.query.filter_by(group_id=group.id).all()
        balance = 0.0
        for expense in expenses:
            for split in expense.splits:
                if split.user_id == user_id:
                    balance -= split.amount
            if expense.paid_by_id == user_id:
                balance += expense.amount
        group_balances[group.id] = balance
        net_balance += balance

    # FRIENDS SECTION
    friendships = Friendship.query.filter(
        (Friendship.user1_id == user_id) | (Friendship.user2_id == user_id)
    ).all()

    friends = []
    friend_balances = {}
    friendship_ids = {}

    for friendship in friendships:
        other = friendship.other_user(user_id)
        friends.append(other)
        friendship_ids[other.id] = friendship.id

        # Get personal (non-group) expenses involving both users
        expenses = (
            Expense.query
            .filter_by(group_id=None)
            .filter(
                (Expense.paid_by_id == user_id) |
                (Expense.paid_by_id == other.id)
            )
            .order_by(Expense.timestamp.desc())
            .all()
        )

        # Filter to expenses involving both
        balance = 0.0
        for expense in expenses:
            user_ids = {split.user_id for split in expense.splits}
            if {user_id, other.id}.issubset(user_ids):
                for split in expense.splits:
                    if split.user_id == user_id:
                        balance -= split.amount
                if expense.paid_by_id == user_id:
                    balance += expense.amount

        friend_balances[other.id] = balance
        net_balance += balance

    return render_template(
        "index.html",
        groups=groups,
        net_balance=net_balance,
        group_balances=group_balances,
        friends=friends,
        friend_balances=friend_balances,
        friendship_ids=friendship_ids,
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


@app.route('/create_group', methods=['GET', 'POST'])
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
        membership = GroupMember(
            user_id=current_user_id, group_id=new_group.id)
        db.session.add(membership)
        db.session.commit()

        flash(f'Group "{group_name}" created successfully!', "success")
        return redirect("/")

    return render_template('create_group.html')


@app.route("/create_friend", methods=["GET", "POST"])
@login_required
def create_friend():
    current_user_id = session["user_id"]
    all_users = User.query.filter(User.id != current_user_id).all()

    # Get existing friendships
    existing_friend_ids = set()
    for f in Friendship.query.all():
        if f.user1_id == current_user_id:
            existing_friend_ids.add(f.user2_id)
        elif f.user2_id == current_user_id:
            existing_friend_ids.add(f.user1_id)

    # Filter out already-friends
    available_users = [u for u in all_users if u.id not in existing_friend_ids]

    if request.method == "POST":
        selected_id = int(request.form.get("friend_id"))

        # Prevent duplicate
        already_friends = Friendship.query.filter(
            ((Friendship.user1_id == current_user_id) &
             (Friendship.user2_id == selected_id)) |
            ((Friendship.user1_id == selected_id) &
             (Friendship.user2_id == current_user_id))
        ).first()

        if already_friends:
            flash("You're already friends with this user.", "warning")
            return redirect("/")

        new_friendship = Friendship(
            user1_id=current_user_id, user2_id=selected_id)
        db.session.add(new_friendship)
        db.session.commit()

        flash("Friend added successfully!", "success")
        return redirect(
            url_for('friend_page', friendship_id=new_friendship.id))

    return render_template("create_friend.html", users=available_users)


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

    return render_template(
        'invite_friends.html', group=group, users=users, members=group.users)


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
    expenses = Expense.query.filter_by(group_id=group.id).order_by(
        Expense.timestamp.desc()).all()

    # Calculate outstanding balance in this group
    balance = 0.0
    for expense in expenses:
        for split in expense.splits:
            if split.user_id == current_user_id:
                balance -= split.amount
        if expense.paid_by_id == current_user_id:
            balance += expense.amount

    return render_template(
        "group.html", group=group, expenses=expenses, balance=balance)


@app.route("/friend/<int:friendship_id>")
@login_required
def friend_page(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    current_user_id = session["user_id"]

    # Ensure access
    if not friendship.involves_user(current_user_id):
        flash("You do not have access to this friend.", "danger")
        return redirect("/")
    other_user = friendship.other_user(current_user_id)

    expenses = (
        Expense.query
        .filter_by(group_id=None)
        .filter(
            (Expense.paid_by_id == current_user_id) |
            (Expense.paid_by_id == other_user.id)
        )
        .order_by(Expense.timestamp.desc())
        .all()
    )

    # Filter to expenses involving both users
    filtered_expenses = []
    balance = 0.0

    for expense in expenses:
        user_ids_involved = {split.user_id for split in expense.splits}
        if {current_user_id, other_user.id}.issubset(user_ids_involved):
            filtered_expenses.append(expense)
            for split in expense.splits:
                if split.user_id == current_user_id:
                    balance -= split.amount
            if expense.paid_by_id == current_user_id:
                balance += expense.amount

    return render_template(
        "friend.html",
        friendship=friendship,
        other_user=other_user,
        expenses=filtered_expenses,
        balance=balance,
    )


@app.route("/group/<int:group_id>/add_expense", methods=["GET", "POST"])
def add_group_expense(group_id):
    group = Group.query.get_or_404(group_id)
    members = GroupMember.query.filter_by(group_id=group_id).all()
    users = [db.session.get(User, member.user_id) for member in members]

    if request.method == "POST":
        description = request.form.get("description")
        amount = float(request.form.get("amount"))
        payer_id = int(request.form.get("paid_by"))

        # Create Expense record
        expense = Expense(
            description=description,
            amount=amount,
            paid_by_id=payer_id,
            group_id=group_id,
            )
        db.session.add(expense)
        db.session.flush()

        total_split = 0
        for user in users:
            share = float(request.form.get(f"user_{user.id}", 0))
            if share > 0:
                split = ExpenseSplit(
                    expense_id=expense.id, user_id=user.id, amount=share)
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


@app.route("/friend/<int:friendship_id>/add_expense", methods=["GET", "POST"])
@login_required
def add_friend_expense(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    current_user_id = session["user_id"]

    if not friendship.involves_user(current_user_id):
        flash("Unauthorized", "danger")
        return redirect("/")

    other_user = friendship.other_user(current_user_id)
    users = [db.session.get(User, current_user_id), other_user]

    if request.method == "POST":
        description = request.form.get("description")
        amount = float(request.form.get("amount"))
        payer_id = int(request.form.get("paid_by"))

        expense = Expense(
            description=description,
            amount=amount,
            paid_by_id=payer_id,
            group_id=None
        )
        db.session.add(expense)
        db.session.flush()

        total_split = 0
        for user in users:
            share = float(request.form.get(f"user_{user.id}", 0))
            split = ExpenseSplit(
                expense_id=expense.id, user_id=user.id, amount=share)
            db.session.add(split)
            total_split += share

        if round(total_split, 2) != round(amount, 2):
            db.session.rollback()
            flash("Split must equal total amount", "danger")
            return redirect(request.url)

        db.session.commit()
        flash("Expense added!", "success")
        return redirect(url_for("friend_page", friendship_id=friendship_id))

    return render_template(
        "add_personal_expense.html", users=users, friendship=friendship)


@app.route("/history")
@login_required
def activity():
    user_id = session.get("user_id")

    expenses = Expense.query.filter(
        (Expense.paid_by_id == user_id) |
        (Expense.id.in_(
            db.session.query(ExpenseSplit.expense_id)
            .filter_by(user_id=user_id)
        ))
    ).order_by(Expense.timestamp.desc()).all()

    transactions = []
    for expense in expenses:
        group = Group.query.get(expense.group_id) if expense.group_id else None
        group_name = group.name if group else None

        splits = expense.splits
        user_split = next((s for s in splits if s.user_id == user_id), None)

        if expense.paid_by_id == user_id:
            # You paid, others owe you
            for split in splits:
                if split.user_id != user_id and split.amount > 0:
                    counterparty = User.query.get(split.user_id)
                    transactions.append({
                        "description": expense.description,
                        "owed_amount": split.amount,
                        "counterparty_name": counterparty.name,
                        "group_name": group_name,
                        "timestamp": expense.timestamp
                    })

        elif user_split:
            # You owe someone
            payer = User.query.get(expense.paid_by_id)
            transactions.append({
                "description": expense.description,
                "owed_amount": -user_split.amount,
                "counterparty_name": payer.name,
                "group_name": group_name,
                "timestamp": expense.timestamp
            })

    return render_template("activity.html", transactions=transactions)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
