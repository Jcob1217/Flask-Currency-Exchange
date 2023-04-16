# Importing necessary modules and packages
from flask import Blueprint, render_template, redirect, url_for, request, flash
from . import db
from .models import User
from flask_login import login_manager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import re


# Creating a Blueprint object
auth = Blueprint("auth", __name__)

# Route to sign-up page
@auth.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    # Handling POST request
    if request.method == "POST":
        # Getting user details from form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        # Validating password pattern
        password_pattern = "^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[#?!@$%^&*-]).{6,}$"

        # Checking if email already exists in database
        email_exists = User.query.filter_by(email=email).first()

        # Handling various error scenarios
        if email_exists:
            flash("Email is already used", category="error")
        elif password1 != password2:
            flash("Passwords are not the same", category="error")
        elif not re.match(password_pattern, password1):
            flash("Password ha be at least 6 characters long, have at least one uppercase and lowercase, at least one digit and special character", category="error")
        else:
            # Creating user and adding to database
            user = User(first_name=first_name, last_name=last_name, email=email, password=generate_password_hash(password1, method='sha256'))
            db.session.add(user)
            db.session.commit()
            flash("Account Created!", category="success")
            
            # Logging in the user
            login_user(user, remember=True)

            # Redirecting to home page
            return redirect(url_for("views.home"))

    # Rendering sign-up page
    return render_template("signup.html", user=current_user)


# Route to login page
@auth.route("/login", methods=["GET", "POST"])
def login():
    # Handling POST request
    if request.method == "POST":
        # Getting user details from form
        email = request.form.get("email")
        password = request.form.get("password")
    
        # Querying user from database
        user = User.query.filter_by(email=email).first()
        if user:
            # Checking if password is correct
            if check_password_hash(user.password, password):
                flash(f"Hello, {user.first_name}!", category="success")
                # Logging in the user
                login_user(user, remember=True)
                # Redirecting to home page
                return redirect(url_for("views.home"))
            else:
                # Handling incorrect password
                flash("Password is incorrect", category="error")
        else:
            # Handling non-existent user
            flash("User does not exist", category="error")

    # Rendering login page
    return render_template("login.html", user=current_user)


# Route to logout the user
@auth.route("/logout")
@login_required
def logout():
    # Logging out the user
    logout_user()
    # Redirecting to login page
    return redirect(url_for("auth.login"))