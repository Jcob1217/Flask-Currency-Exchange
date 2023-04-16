# import necessary packages
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

# import the necessary classes and functions from models file
from .models import Rates, User, User_currencies
from . import db
import csv

# create a new Blueprint named 'views'
views = Blueprint("views", __name__)

# Define a route '/' and '/home'
@views.route("/")
@views.route("/home")
def home():
    # create a list of dictionaries that include the foreign rates for different currencies
    rates = Rates().rates_all_foreign()

    # render the home template along with the rates and user's details
    return render_template("home.html", rates=rates, user=current_user)

# Define a route '/calculator' for currency conversion
@views.route("/calculator", methods=["GET", "POST"])
def calculator():
    outcome = False # set outcome as false by default
    out_amount = 0 # set out_amount as 0 by default
    rates = Rates().rates_all() # create a list of dictionaries that include the rates for different currencies
    
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount"))
        except Exception as e:
            amount = 0
            
        from_currency = request.form.get("from")
        to_currency = request.form.get("to")

        # check whether the amount is greater than zero
        if amount > 0:
            try:
                from_currency_rate = Rates.query.filter_by(currency_code=from_currency).first().buy
                to_currency_rate = Rates.query.filter_by(currency_code=to_currency).first().sell
                
                # calculate the converted amount 
                out_amount = round(float(amount) * float(from_currency_rate) / float(to_currency_rate), 2)
                outcome = True # set outcome as true after successful conversion

            except Exception as e:
                from_currency = '' # reset from_currency 
                to_currency = '' # reset to_currency
                flash("Both currencies have to be chosen", category="error")
        else:
            flash("Amount has to be bigger than 0", category="error")

        # render the calculator template along with the rates, user's details, and the outcomes
        return render_template("calculator.html", rates=rates, user=current_user, outcome=outcome, amount=amount, from_currency=from_currency, to_currency=to_currency, out_amount=out_amount)

    # render the calculator template along with the rates and user's details
    return render_template("calculator.html", rates=rates, user=current_user)

# Define a route '/account' for user's account balance
@views.route("account")
@login_required # the user must be authenticated to access this page
def account():    
    # join User_currencies and Rates tables and filter the rows for the current user
    # and then sort the rows by the amounts in descending order
    result = (db.session.query(User_currencies, Rates)
              .join(Rates)
              .filter(User_currencies.user_id == current_user.id)
              .order_by(User_currencies.amount.desc())
              .all()
              )
    
    # calculate the total account balance in Euro based on the user's currencies and rates
    total = 0
    for uc, rt in result:
        total += uc.amount * rt.amount

    # render the account template along with the user's details, total account balance, and currencies
    return render_template("account.html", user=current_user, total=round(total,2), currencies=result)


@views.route("add-funds", methods=["GET", "POST"])
@login_required
def add_funds():
    # Fetch all currency rates
    rates = Rates().rates_all()

    # Check if request is POST, i.e., if the user submitted a form
    if request.method == "POST":
        # Get the currency code and amount submitted by the user
        code = request.form.get("currency")
        try:
            amount = float(request.form.get("amount"))
        except Exception as e:
            # If the amount is not a valid float, set it to 0
            amount = 0

        # If the user didn't select a currency, flash an error message
        if code == "":
            flash("Pick currency", category="error")
        # If the amount is less than or equal to 0, flash an error message
        elif amount <= 0:
            flash("Amount has to be bigger than 0", category="error")
        else:
            # Get the ID of the selected currency
            currency_id = Rates().currency_id(code)
            
            # Check if the user already has the selected currency in their account
            deposit = User_currencies.query.filter_by(user_id=current_user.id, currency_id=currency_id).first()

            # If the user already has the currency, add the deposited amount to their existing balance
            if deposit:
                deposit.amount += amount
            # If the user doesn't have the currency, create a new record with the deposited amount
            else:
                deposit = User_currencies(user_id=current_user.id, currency_id=currency_id, amount=amount)
            
            # Format the amount to be displayed in the flash message
            if str(amount)[-2:] == ".0":
                amount = int(amount)
            else:
                amount = format(amount, '.2f')

            # Flash a success message with the deposited amount and currency
            flash(f"{amount} {code} has been succesfully added to account balance", category="success")
            
            # Add the deposit record to the database and commit the transaction
            db.session.add(deposit)
            db.session.commit()

            # Redirect the user to the add funds page
            return redirect(url_for("views.add_funds"))

    # If the request is not POST, i.e., the user is accessing the add funds page
    # Render the add funds page with the user's information and the currency rates
    return render_template("add-funds.html", user=current_user, rates=rates)


@views.route("exchange-currencies", methods=["GET", "POST"])
@login_required
def exchange_currencies():
    # Get all currency rates
    currency_rates = Rates().rates_all()

    # Retrieving user currencies with their rates using a query
    user_rates = (db.session.query(User_currencies, Rates)
            .join(Rates)
            .filter(User_currencies.user_id == current_user.id)
            .order_by(User_currencies.amount.desc())
            .all()
            )

    # Handling POST request
    if request.method == "POST":
        try:
            # Get the amount entered by the user from the form and convert it to a float.
            amount = float(request.form.get("amount"))
        except Exception as e:
            # If there was an error while converting the amount, set it to 0.
            amount = 0

        # Get the currency codes for the currencies being exchanged from the form.
        from_currency = request.form.get("from")
        to_currency = request.form.get("to")

        # Get the currency IDs for the currencies being exchanged.
        to_currency_id = Rates().currency_id(to_currency)
        from_currency_id = Rates().currency_id(from_currency)

        # Get the User_currencies object for the currency being exchanged from.
        user_currencies = User_currencies.query.filter_by(user_id=current_user.id, currency_id=from_currency_id).first()

        # Check if the amount is valid and there is enough currency in the user's account.
        if amount <= 0:
            flash("Amount has to be bigger than 0", category="error")
        elif amount > user_currencies.amount:
            flash(f"Not enough {from_currency} in your account balance to proceed transaction", category="error")
        elif from_currency == to_currency:
            flash("Currencies have to be different", category="error")
        else:
            # Get the buy and sell rates for the currencies being exchanged.
            from_currency_rate = Rates.query.filter_by(currency_code=from_currency).first().buy
            to_currency_rate = Rates.query.filter_by(currency_code=to_currency).first().sell

            # Calculate the amount of currency being exchanged to.
            out_amount = round(float(amount) * float(from_currency_rate) / float(to_currency_rate), 2)

            # Check if the user already has some of the currency being exchanged to.
            user_has_currency = (db.session.query(User_currencies, Rates)
            .join(Rates)
            .filter(User_currencies.user_id == current_user.id, Rates.currency_code == to_currency)
            .all()
            )

            if user_has_currency:
                # If the user already has some of the currency being exchanged to, update their balance.
                for user_currencies, rates in user_rates:
                    if rates.currency_code == to_currency:
                        user_currencies.amount += round(out_amount, 2)
                        db.session.commit()
                    elif rates.currency_code == from_currency:
                        user_currencies.amount -= round(amount, 2)
                        db.session.commit()
            else:
                # If the user does not have any of the currency being exchanged to, add it to their account.
                deposit = User_currencies(user_id=current_user.id, currency_id=to_currency_id, amount=round(out_amount, 2))
                db.session.add(deposit)
                db.session.commit()

                # Subtract the amount being exchanged from the user's account.
                for user_currencies, rates in user_rates:
                    if rates.currency_code == from_currency:
                        user_currencies.amount -= amount
                        db.session.commit()

            # Flash a success message and redirect the user back to the exchange page.
            flash(f"Succesfully exchanged {amount} {from_currency} to {out_amount} {to_currency}", category="success")
            return redirect(url_for("views.exchange_currencies"))

        # If there was an error with the form submission, render the exchange-currencies template with the appropriate data.
        return render_template("exchange-currencies.html", user=current_user, user_rates=user_rates, rates=currency_rates, from_currency=from_currency, to_currency=to_currency)

    # Rendering template if GET was a request method 
    return render_template("exchange-currencies.html", user=current_user, user_rates=user_rates, rates=currency_rates)