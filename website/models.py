# import necessary modules
from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func
import json
import requests

# create a Rates class which inherits from the db.Model class
class Rates(db.Model):
    # define class variables which represent columns in the Rates table
    id = db.Column(db.Integer, primary_key=True)
    currency_code = db.Column(db.String(4), unique=True)
    currency = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False)
    buy = db.Column(db.Float, nullable=False)
    sell = db.Column(db.Float, nullable=False)
    currencies = db.relationship("User_currencies", backref="rates", passive_deletes=True)

    # define methods to query the Rates table
    def rates_all(self):
        return Rates.query.all()
    
    def rates_all_foreign(self):
        return Rates.query.limit(33).all()
    
    def currency_id(self, currency_code):
        return Rates.query.filter_by(currency_code=currency_code).first().id

# create a User class which inherits from the db.Model and UserMixin classes
class User(db.Model, UserMixin):
    # define class variables which represent columns in the User table
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), unique=False)
    last_name = db.Column(db.String(150), unique=False)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    balance = db.Column(db.Float, default=0)
    user_currencies = db.relationship("User_currencies", backref="user", passive_deletes=True)

    # define a method to add balance to a user's account
    def add_balance(self, amount):
        self.balance += amount

# create a User_currencies class which inherits from the db.Model class
class User_currencies(db.Model):
    # define class variables which represent columns in the User_currencies table
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    currency_id = db.Column(db.Integer, db.ForeignKey("rates.id", ondelete="CASCADE"), nullable=False)
    amount = db.Column(db.Float, default=0)
    
    # define a method to check if a user has a certain currency
    def user_has_currency(self, user_id, currency_id):
        return User_currencies.query.filter_by(user_id=user_id, currency_id=currency_id)