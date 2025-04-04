from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    users = db.relationship("User", secondary="group_members", backref="groups")

class GroupMember(db.Model):
    __tablename__ = "group_members"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), primary_key=True)

class Expense(db.Model):
    __tablename__ = "expenses"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120))
    amount = db.Column(db.Float)
    paid_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)  # Optional
    timestamp = db.Column(db.DateTime, default=datetime.now)
    splits = db.relationship("ExpenseSplit", backref="expense", lazy=True)

class ExpenseSplit(db.Model):
    __tablename__ = "expense_split"
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    amount = db.Column(db.Float)


