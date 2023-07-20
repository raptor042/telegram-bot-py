import requests
import logging

def init_payment(email, plan):
    try:
        response = requests.get(f"http://localhost:3000/init/{email}/{plan}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()
    
def verify_payment(ref):
    try:
        response = requests.get(f"http://localhost:3000/verify/{ref}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.text)
        return response.text
    
def get_sub(email):
    try:
        response = requests.get(f"http://localhost:3000/subscription/{email}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()
    
def cancel(code, token):
    try:
        response = requests.get(f"http://localhost:3000/cancel/{code}/{token}")
    except:
        logging.error("Unable to send request to payment gateway")
    else:
        print(response.json())
        return response.json()