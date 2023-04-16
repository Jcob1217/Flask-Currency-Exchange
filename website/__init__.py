from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import requests, csv

# Initialize the database
db = SQLAlchemy()
DB_NAME = "database.db"

# Function to add currencies to the database
def add_currencies():
    # Import the Rates model from the models module
    from .models import Rates

    # Get the currency rates from an API
    response = requests.get("http://api.nbp.pl/api/exchangerates/tables/A").json()
    rates = response[0]["rates"]

    # Sort the rates by their mid value (the average of the bid and ask price) in descending order
    rates = sorted(rates, key=lambda x:x["mid"], reverse=True)

    # Open the currencies.csv file and add the corresponding currency name to each rate
    with open("instance/currencies.csv") as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            for rate in rates:
                if rate["code"] == row[0]:
                    rate["currency"] = row[1]

    # Delete all existing rates from the database
    Rates.query.delete()

    # Add each rate to the database as a new Rates object
    for rate in rates:
        rate = Rates(currency_code=rate["code"], 
                     currency=rate["currency"], 
                     amount=round(rate["mid"], 4), 
                     buy=round(rate["mid"]*0.98, 4), 
                     sell=round(rate["mid"]*1.02, 4)
                     )
        
        db.session.add(rate)
        db.session.commit()

    # Add a rate for the Polish Zloty to the database with a fixed exchange rate of 1
    pln_rate = Rates(currency_code="PLN", currency="Polish Zloty", amount=1, buy=1, sell=1)
    db.session.add(pln_rate)
    db.session.commit()

# Create the Flask app
def create_app():
    app = Flask(__name__)

    # Set the app configuration
    app.config['SECRET_KEY'] = "helloworld"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    # Register the views and auth blueprints
    from .views import views
    from .auth import auth
    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    # Import the User model from the models module and initialize the login manager
    from .models import User
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    # Load the user with the given ID from the database
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Create the database tables and add the currency rates to the database
    with app.app_context():
        db.create_all()
        print("Database Created")
        add_currencies()

    return app