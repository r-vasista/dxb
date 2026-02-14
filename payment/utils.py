import requests
from rest_framework.serializers import ValidationError

def convert_currency(amount, from_currency, to_currency):
    """
    Convert amount from one currency to another using exchangerate.host.
    """
    if from_currency == to_currency:
        return amount

    try:
        url = f"https://api.exchangerate.host/convert?from={from_currency}&to={to_currency}&amount={amount}"
        response = requests.get(url)
        data = response.json()
        return round(data["result"], 2)
    except Exception:
        raise ValidationError("Currency conversion failed. Please try again later.")
