from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # Relationships
    expenses_paid = db.relationship(
        "Expense",
        backref="payer",
        foreign_keys="Expense.paid_by_id",
        )
    splits = db.relationship(
        "ExpenseSplit",
        backref="user",
        foreign_keys="ExpenseSplit.user_id",
        )

    def balance(self):
        paid = sum(e.amount for e in self.expenses_paid)
        owed = sum(split.amount for split in self.splits)
        return paid - owed

    def get_friends(self):
        return [
            g for g in getattr(self, "groups", [])
            if g.is_friend_group and len(g.users) == 2
        ]


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
    is_friend_group = db.Column(db.Boolean, default=False)

    users = db.relationship(
        "User", secondary="group_members", backref="groups")
    expenses = db.relationship("Expense", backref="group", lazy=True)

    def user_is_member(self, user_id):
        return any(user.id == user_id for user in self.users)

    def get_group_expenses(self):
        return (
            Expense.query.filter_by(group_id=self.id)
            .order_by(Expense.timestamp.desc())
            .all()
        )

    def get_group_balance(self):
        return sum(e.amount for e in self.expenses)

    def get_user_balance(self, user_id):
        balance = 0.0
        for expense in self.expenses:
            for split in expense.splits:
                if split.user_id == user_id:
                    balance -= split.amount
            if expense.paid_by_id == user_id:
                balance += expense.amount
        return balance


class GroupMember(db.Model):
    __tablename__ = "group_members"
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        primary_key=True,
        )
    group_id = db.Column(
        db.Integer,
        db.ForeignKey("groups.id"),
        primary_key=True,
        )


class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120))
    amount = db.Column(db.Float)
    paid_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    splits = db.relationship("ExpenseSplit", backref="expense", lazy=True)

    def add_splits_from_form(self, form_data, users):
        total_split = 0.0
        for user in users:
            try:
                share = round(float(form_data.get(f"user_{user.id}", 0)), 2)
                if share > 0:
                    split = ExpenseSplit(
                        expense_id=self.id,
                        user_id=user.id,
                        amount=share
                    )
                    db.session.add(split)
                    total_split += share
            except ValueError:
                continue
        return total_split

    def update_splits_from_form(self, form, users):
        existing_splits = {split.user_id: split for split in self.splits}
        total_split = 0

        for user in users:
            key = f"user_{user.id}"
            if key in form:
                share = float(form.get(key, 0))
                total_split += share

                if share == 0 and user.id in existing_splits:
                    db.session.delete(existing_splits[user.id])
                elif user.id in existing_splits:
                    existing_splits[user.id].amount = share
                else:
                    new_split = ExpenseSplit(
                        expense_id=self.id,
                        user_id=user.id,
                        amount=share,
                        )
                    db.session.add(new_split)

        return round(total_split, 2)


class ExpenseSplit(db.Model):
    __tablename__ = "expense_split"
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Float)
