import requests
from urllib.parse import quote
import os
import json as j
from datetime import datetime

GOOGLE_FORM_MESSAGE="""
Dear {guest_name},

As we prepare for your arrival on {check_in_date}, the Aquatika Homeowners Association 🏡 requires the following information for all guests included in your reservation:

1. Full name of each guest
2. Your phone number
3. Email address

Please use the link below to submit the required information. Be sure to include every guest, regardless of age, to ensure a smooth and expedited check-in at the security gate.

{link}

If you have any questions or need assistance, please don't hesitate to reach out. We look forward to hosting you!

Best regards,

STR MANAGEMENT
"""

def get_conversation(reservation_code:str):
    url = f"https://api.hostex.io/v3/reservations?reservation_code={reservation_code}"

    headers = {
        "accept": "application/json",
        "Hostex-Access-Token": os.getenv("HOSTEX_API_TOKEN")
    }

    response = requests.get(url, headers=headers)

    result = j.loads(response.text)

    convo = result["data"]["reservations"][0]["conversation_id"]
    guest = result["data"]["reservations"][0]["guest_name"]
    check_in_date = datetime.strptime(result["data"]["reservations"][0]["check_in_date"],"%Y-%m-%d").strftime("%m-%d-%Y")

    return (convo,guest,check_in_date)

def send_hostex_message(conversation_id:str,url:str,guest:str,check_in_date:str):
    hostex_url = f"https://api.hostex.io/v3/conversations/{conversation_id}"

    payload = { "message": GOOGLE_FORM_MESSAGE.format(link=url,guest_name=guest,check_in_date=check_in_date) }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Hostex-Access-Token": os.getenv("HOSTEX_API_TOKEN")
    }

    response = requests.post(hostex_url, json=payload, headers=headers)

    return 

def lambda_handler(event,context):
    try:
        reservation_code = event["reservation_code"]

        form = f"https://str-automation.vercel.app/form/{reservation_code}"

        convo_and_guest = get_conversation(reservation_code)

        convo = convo_and_guest[0]
        guest = convo_and_guest[1].split()[0]
        check_in_date = convo_and_guest[2]

        send_hostex_message(convo,form,guest,check_in_date)

        return {"statusCode":200}

    except Exception as e:

        print(e)

        return {"statusCode":500}

