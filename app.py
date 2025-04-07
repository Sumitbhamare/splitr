from flask import Flask, render_template, redirect, url_for, flash
from flask import request, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_session import Session

from models import db, User, Group, GroupMember, Expense, ExpenseSplit
from helper import login_required, currency
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = \
    f"sqlite:///{os.path.join(basedir, 'money_split.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # Secret key for sessions
app.config["SESSION_PERMANENT"] = False
app.config['DEFAULT_CURRENCY'] = 'USD'
app.jinja_env.globals.update(currency=currency)
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
    """Homepage of the website"""
    if "user_id" not in session:
        flash("Please log in first!", "warning")
        return redirect("/login")

    user_id = session.get("user_id")
    user = User.query.get(user_id)
    if user is None:
        flash("User not found. Please log in again.", "danger")
        return redirect("/logout")

    net_balance = user.balance()

    return render_template("index.html", net_balance=net_balance)


@app.route("/groups")
@login_required
def groups_page():
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    groups = [g for g in user.groups if not g.is_friend_group]
    entries = [
        {
            "id": g.id,
            "name": g.name,
            "balance": g.get_user_balance(user_id)
        }
        for g in groups
    ]

    return render_template(
        "entities_list.html",
        title="Groups",
        header="Your Groups",
        action_url="/create_group",
        action_text="+ New Group",
        entries=entries,
        is_friend_view=False,
        empty_message="You're not part of any groups yet. \
            Create one to get started!"
    )


@app.route("/friends")
@login_required
def friends_page():
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    friend_groups = [
        g for g in user.groups if g.is_friend_group and len(g.users) == 2
    ]

    entries = []
    for group in friend_groups:
        friend = next(u for u in group.users if u.id != user_id)
        entries.append({
            "id": group.id,
            "name": friend.name,
            "balance": group.get_user_balance(user_id)
        })

    return render_template(
        "entities_list.html",
        title="Friends",
        header="Your Friends",
        action_url="/create_friend",
        action_text="+ Add New Friend",
        entries=entries,
        is_friend_view=True,
        empty_message="You don't have any friends added yet. \
            Add one to get started!"
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user"""
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page for existing users"""
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
            session["name"] = user.name
            flash("Login successful!", "success")
            return redirect("/")
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout the user"""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    """User profile page. Allows password change."""
    if "user_id" not in session:
        flash("You must be logged in to access this page.", "warning")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")

        # Validate current password
        if not check_password_hash(user.password, current_password):
            flash("Current password is incorrect.", "danger")
            return render_template("profile.html")

        # Check if new password matches confirmation
        if new_password != confirmation:
            flash("New password and confirmation do not match.", "danger")
            return render_template("profile.html")

        # Check if new password is not empty
        if not new_password:
            flash("New password cannot be empty.", "danger")
            return render_template("profile.html")

        # Update password
        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash("Password updated successfully.", "success")
        return redirect("/")

    return render_template("profile.html", user=user)


@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    """Create a new group"""
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        current_user_id = session.get('user_id')

        if not group_name:
            flash("Group name cannot be empty.", "danger")
            return redirect('/create_group')

        # Check duplicate
        existing_group = (
            db.session.query(Group)
            .join(GroupMember, Group.id == GroupMember.group_id)
            .filter(Group.name == group_name,
                    GroupMember.user_id == current_user_id,
                    not Group.is_friend_group)
            .first()
        )

        if existing_group:
            flash("You already have a group with this name.", "warning")
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
        return redirect("/groups")

    return render_template(
        'create_entity.html',
        title="Create Group",
        header="Create a New Group",
        label="Group Name",
        field_name="group_name",
        button_text="Create Group",
        cancel_url="/groups"
    )


@app.route('/create_friend', methods=['GET', 'POST'])
@login_required
def create_friend():
    """Create a friend connection (friend group with just two users)"""
    if request.method == 'POST':
        username = request.form.get('friend_id')
        current_user_id = session.get('user_id')

        if not username:
            flash("Please enter a friend's username.", "danger")
            return redirect('/create_friend')

        # Check if the user exists
        friend = User.query.filter_by(username=username).first()
        if not friend:
            flash("No user with that username found.", "danger")
            return redirect('/create_friend')

        if friend.id == current_user_id:
            flash("You cannot add yourself as a friend.", "danger")
            return redirect('/create_friend')

        # Check if a friend group already exists between the two users
        existing_friend_group = (
            db.session.query(Group)
            .join(Group.users)
            .filter(Group.is_friend_group)
            .filter(Group.users.any(id=current_user_id))
            .filter(Group.users.any(id=friend.id))
            .first()
        )

        if existing_friend_group:
            flash("You're already friends with this user.", "info")
            return redirect('/friends')

        # Create a new friend group
        new_friend_group = Group(name=None, is_friend_group=True)
        db.session.add(new_friend_group)
        db.session.commit()

        # Add both users to the group
        db.session.add_all([
            GroupMember(user_id=current_user_id, group_id=new_friend_group.id),
            GroupMember(user_id=friend.id, group_id=new_friend_group.id)
        ])
        db.session.commit()

        flash(f"You are now friends with {friend.name}!", "success")
        return redirect('/friends')

    # For GET request: get all users except current one
    current_user_id = session.get("user_id")
    all_users = User.query.filter(User.id != current_user_id).all()

    return render_template(
        "create_entity.html",
        title="Add Friend",
        header="Add a New Friend",
        label="Select a Friend",
        field_name="friend_id",
        button_text="Add Friend",
        cancel_url="/friends",
        users=all_users
    )


@app.route('/invite-friends/<int:group_id>', methods=['GET', 'POST'])
@login_required
def invite_friends(group_id):
    """Invite friends to a group"""
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
        return redirect("/groups")

    return render_template(
        'invite_friends.html', group=group, users=users, members=group.users)


@app.route('/group/<int:group_id>')
@login_required
def group_page(group_id):
    """Group page showing expenses and balance"""
    group = Group.query.get_or_404(group_id)
    current_user_id = session.get("user_id")

    # Ensure current user is a member
    if not group.user_is_member(current_user_id):
        flash("You do not have access to this group.", "danger")
        return redirect("/groups")

    expenses = group.get_group_expenses()
    balance = group.get_user_balance(current_user_id)

    return render_template(
        "group.html", group=group, expenses=expenses, balance=balance)


@app.route('/friend/<int:group_id>')
@login_required
def friend_page(group_id):
    """Page showing expenses and balance with a specific friend"""
    group = Group.query.get_or_404(group_id)
    current_user_id = session.get("user_id")

    if not group.user_is_member(current_user_id) or not group.is_friend_group:
        flash("You do not have access to this friend view.", "danger")
        return redirect("/friends")

    expenses = group.get_group_expenses()
    balance = group.get_user_balance(current_user_id)
    friend = next(user for user in group.users if user.id != current_user_id)

    return render_template(
        "friend.html",
        group=group,
        friend=friend,
        expenses=expenses,
        balance=balance
    )


@app.route("/group/<int:group_id>/add_expense", methods=["GET", "POST"])
def add_group_expense(group_id):
    """Add an expense to a group"""
    group = Group.query.get_or_404(group_id)
    users = group.users

    if request.method == "POST":
        try:
            description = request.form["description"]
            amount = round(float(request.form["amount"]), 2)
            payer_id = int(request.form["paid_by"])
        except (KeyError, ValueError):
            flash("Invalid input for expense fields.", "danger")
            return redirect(request.url)

        # Create Expense record
        expense = Expense(
            description=description,
            amount=amount,
            paid_by_id=payer_id,
            group_id=group_id,
        )
        db.session.add(expense)
        db.session.flush()

        total_split = expense.add_splits_from_form(request.form, users)

        if round(total_split, 2) != amount:
            db.session.rollback()
            flash("Split amounts must add up to the total expense.", "danger")
            return redirect(request.url)

        db.session.commit()
        flash("Expense added successfully!", "success")
        # Redirect based on group type
        if group.is_friend_group:
            return redirect(url_for("friend_page", group_id=group.id))
        return redirect(url_for("group_page", group_id=group.id))

    return render_template("add_expense.html", group=group, users=users)


@app.route("/history")
@login_required
def activity():
    """View all transactions (both paid and owed)"""
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


@app.route("/group/<int:group_id>/edit_expense/<int:expense_id>",
           methods=["GET", "POST"])
@login_required
def edit_group_expense(group_id, expense_id):
    """Edit an existing group or friend expense"""
    group = Group.query.get_or_404(group_id)
    expense = Expense.query.get_or_404(expense_id)

    # Ensure expense belongs to the group
    if expense.group_id != group.id:
        flash("Expense does not belong to this group.", "danger")
        return redirect(url_for("group_page", group_id=group.id))

    members = group.users

    if request.method == "POST":
        expense.description = request.form.get("description")
        expense.amount = float(request.form.get("amount"))
        expense.paid_by_id = int(request.form.get("paid_by"))

        total_split = expense.update_splits_from_form(request.form, members)

        if round(total_split, 2) != round(expense.amount, 2):
            db.session.rollback()
            flash("Split amounts must equal the total expense.", "danger")
            return redirect(request.url)

        db.session.commit()
        flash("Expense updated successfully!", "success")

        # Redirect based on group type
        if group.is_friend_group:
            return redirect(url_for("friend_page", group_id=group.id))
        return redirect(url_for("group_page", group_id=group.id))

    user_splits = {split.user_id: split.amount for split in expense.splits}

    return render_template(
        "add_expense.html",
        group=group,
        users=members,
        expense=expense,
        user_splits=user_splits
    )


@app.route("/group/<int:group_id>/delete_expense/<int:expense_id>",
           methods=["POST"])
@login_required
def delete_group_expense(group_id, expense_id):
    """Delete an expense from a group"""
    group = Group.query.get_or_404(group_id)
    expense = Expense.query.get_or_404(expense_id)

    if expense.group_id != group_id:
        flash("Expense does not belong to this group.", "danger")
        return redirect(url_for("group_page", group_id=group_id))

    ExpenseSplit.query.filter_by(expense_id=expense.id).delete()
    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted successfully!", "success")
    # Redirect based on group type
    if group.is_friend_group:
        return redirect(url_for("friend_page", group_id=group.id))
    return redirect(url_for("group_page", group_id=group.id))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
