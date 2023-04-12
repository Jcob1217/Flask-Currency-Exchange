from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from .models import Rates, User, User_currencies
from . import db
import csv


views = Blueprint("views", __name__)


@views.route("/")
@views.route("/home")
def home():
    rates = Rates().rates_all_foreign()

    return render_template("home.html", rates=rates, user=current_user)


@views.route("/calculator", methods=["GET", "POST"])
def calculator():
    outcome = False
    out_amount = 0
    rates = Rates().rates_all()

    if request.method == "POST":
        try:
            amount = float(request.form.get("amount"))
        except Exception as e:
            amount = 0
            
        from_currency = request.form.get("from")
        to_currency = request.form.get("to")

        if amount > 0:
            try:
                from_currency_rate = Rates.query.filter_by(currency_code=from_currency).first().buy
                to_currency_rate = Rates.query.filter_by(currency_code=to_currency).first().sell
                out_amount = round(float(amount) * float(from_currency_rate) / float(to_currency_rate), 2)
                outcome = True

            except Exception as e:
                from_currency = ''
                to_currency = ''
                flash("Both currencies have to be chosen", category="error")
        else:
            flash("Amount has to be bigger than 0", category="error")

        return render_template("calculator.html", rates=rates, user=current_user, outcome=outcome, amount=amount, from_currency=from_currency, to_currency=to_currency, out_amount=out_amount)

    return render_template("calculator.html", rates=rates, user=current_user)


@views.route("account")
@login_required
def account():    
    result = (db.session.query(User_currencies, Rates)
              .join(Rates)
              .filter(User_currencies.user_id == current_user.id)
              .order_by(User_currencies.amount.desc())
              .all()
              )
    
    total = 0
    for uc, rt in result:
        total += uc.amount * rt.amount

    return render_template("account.html", user=current_user, total=round(total,2), currencies=result)


@views.route("add-funds", methods=["GET", "POST"])
@login_required
def add_funds():
    rates = Rates().rates_all()

    if request.method == "POST":
        code = request.form.get("currency")
        try:
            amount = float(request.form.get("amount"))
        except Exception as e:
            amount = 0

        if code == "":
            flash("Pick currency", category="error")
        elif amount <= 0:
            flash("Amount has to be bigger than 0", category="error")
        else:
            currency_id = Rates().currency_id(code)
            
            deposit = User_currencies.query.filter_by(user_id=current_user.id, currency_id=currency_id).first()

            if deposit:
                deposit.amount += amount
            else:
                deposit = User_currencies(user_id=current_user.id, currency_id=currency_id, amount=amount)
            
            if str(amount)[-2:] == ".0":
                amount = int(amount)
            else:
                amount = format(amount, '.2f')

            flash(f"{amount} {code} has been succesfully added to account balance", category="success")
            db.session.add(deposit)
            db.session.commit()

            return redirect(url_for("views.add_funds"))


    return render_template("add-funds.html", user=current_user, rates=rates)


@views.route("exchange-currencies", methods=["GET", "POST"])
@login_required
def exchange_currencies():
    currency_rates = Rates().rates_all()
    user_rates = (db.session.query(User_currencies, Rates)
              .join(Rates)
              .filter(User_currencies.user_id == current_user.id)
              .order_by(User_currencies.amount.desc())
              .all()
              )
    
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount"))
        except Exception as e:
            amount = 0

        from_currency = request.form.get("from")
        to_currency = request.form.get("to")
        to_currency_id = Rates().currency_id(to_currency)
        from_currency_id = Rates().currency_id(from_currency)
        user_currencies = User_currencies.query.filter_by(user_id=current_user.id, currency_id=from_currency_id).first()

        if amount <= 0:
            flash("Amount has to be bigger than 0", category="error")
        elif amount > user_currencies.amount:
            flash(f"Not enough {from_currency} in your account balance to proceed transaction", category="error")
        elif from_currency == to_currency:
            flash("Currencies have to be different", category="error")
        else:
            from_currency_rate = Rates.query.filter_by(currency_code=from_currency).first().buy
            to_currency_rate = Rates.query.filter_by(currency_code=to_currency).first().sell
            out_amount = round(float(amount) * float(from_currency_rate) / float(to_currency_rate), 2)

            user_has_currency = (db.session.query(User_currencies, Rates)
              .join(Rates)
              .filter(User_currencies.user_id == current_user.id, Rates.currency_code == to_currency)
              .all()
              )

            if user_has_currency:
                for user_currencies, rates in user_rates:
                    if rates.currency_code == to_currency:
                        user_currencies.amount += round(out_amount, 2)
                        db.session.commit()
                    elif rates.currency_code == from_currency:
                        user_currencies.amount -= round(amount, 2)
                        db.session.commit()
            else:
                deposit = User_currencies(user_id=current_user.id, currency_id=to_currency_id, amount=round(out_amount, 2))
                db.session.add(deposit)
                db.session.commit()

                for user_currencies, rates in user_rates:
                    if rates.currency_code == from_currency:
                        user_currencies.amount -= amount
                        db.session.commit()

            flash(f"Succesfully exchanged {amount} {from_currency} to {out_amount} {to_currency}", category="success")
            
            return redirect(url_for("views.exchange_currencies"))

        return render_template("exchange-currencies.html", user=current_user, user_rates=user_rates, rates=currency_rates, from_currency=from_currency, to_currency=to_currency)

    return render_template("exchange-currencies.html", user=current_user, user_rates=user_rates, rates=currency_rates)