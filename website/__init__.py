from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import requests, csv

db = SQLAlchemy()
DB_NAME = "database.db"


def add_currencies():
    from .models import Rates
    response = requests.get("http://api.nbp.pl/api/exchangerates/tables/A").json()
    rates = response[0]["rates"]
    rates = sorted(rates, key=lambda x:x["mid"], reverse=True)

    with open("instance/currencies.csv") as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            for rate in rates:
                if rate["code"] == row[0]:
                    rate["currency"] = row[1]
    
    Rates.query.delete()
    for rate in rates:
        rate = Rates(currency_code=rate["code"], 
                     currency=rate["currency"], 
                     amount=round(rate["mid"], 4), 
                     buy=round(rate["mid"]*0.98, 4), 
                     sell=round(rate["mid"]*1.02, 4)
                     )
        
        db.session.add(rate)
        db.session.commit()
    
    pln_rate = Rates(currency_code="PLN", currency="Polish Zloty", amount=1, buy=1, sell=1)
    db.session.add(pln_rate)
    db.session.commit()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "helloworld"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    from .models import User
    
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    with app.app_context():
        db.create_all()
        print("Database Created")
        add_currencies()
        

    return app

