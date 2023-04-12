import requests
import json
import csv

response = requests.get("http://api.nbp.pl/api/exchangerates/tables/A").json()
rates = response[0]["rates"]
rates = sorted(rates, key=lambda x:x["mid"], reverse=True)



with open("instance/currencies.csv") as csvfile:
    reader = csv.reader(csvfile)

    for row in reader:
        for rate in rates:
            if rate["code"] == row[0]:
                rate["currency"] = row[1]



for r in rates:
    print(r)