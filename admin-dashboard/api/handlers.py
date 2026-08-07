import boto3
import os
import json as j
from datetime import datetime,timedelta
import requests
from zoneinfo import ZoneInfo
import resend
import requests
from dotenv import load_dotenv
load_dotenv()

HOSTEX_API=os.getenv("HOSTEX_API_TOKEN")

s3 = boto3.client("s3")
cron = boto3.client("scheduler")

APARTMENT_MAPPING={
    "303":"12664173",
    "4702":"12664174",
    "6002":"12664175",
    "1301":"12664176"
}

APARTMENT_MAPPING_INVERSE = {
    "12664173":"303",
    "12664174":"4702",
    "12664175":"6002",
    "12664176":"1301"
}

def get_reservations(
                    apt: str,
                    start_date: str | None = None,
                    end_date: str | None = None,
                ):

    if start_date:
        if start_date and not end_date:
            return {"statusCode":400,"body":j.dumps({"message":"End date is required if start date is provided."})}

        delta = datetime.strptime(end_date,'%Y-%m-%d') - datetime.strptime(start_date,'%Y-%m-%d')

        if delta.days >= 180:
            return {"statusCode":400,"body":j.dumps({"message":"Filter dates cannot be 180 days or more appart."})}

    if start_date is None:
        start_date = datetime.now(ZoneInfo("America/Puerto_Rico"))
        end_date = start_date + timedelta(days=60)

    url = f"https://api.hostex.io/v3/reservations?property_id={APARTMENT_MAPPING[apt]}&start_check_in_date={start_date.strftime('%Y-%m-%d')}&end_check_in_date={end_date.strftime('%Y-%m-%d')}"

    headers = {
        "accept": "application/json",
        "Hostex-Access-Token": HOSTEX_API
    }

    response_obj = requests.get(url, headers=headers).json()

    return {"statusCode":200,"body":j.dumps({"reservations":response_obj["data"]["reservations"]})}

def get_pdfs(apt:str=None):

    response = s3.list_objects_v2(
            Bucket=os.getenv("PDF_BUCKET_NAME"),
            Prefix="Reservations/"
        )

    if apt:
        pdfs = [obj["Key"] for obj in response.get("Contents", []) if apt in obj["Key"]]
    else:
        pdfs = [obj["Key"] for obj in response.get("Contents", [])]

    urls = [s3.generate_presigned_url("get_object",Params={
        "Bucket": os.getenv("PDF_BUCKET_NAME"),
        "Key": pdf,
    },ExpiresIn=3600,) for pdf in pdfs]

    return urls

def get_cron_details(reservation_id:str):
     
     cron_details = cron.get_schedule(Name=f"{reservation_id}-cronjob")

     return cron_details

def get_reservation_details(reservation_code:str)->dict:

    url = f"https://api.hostex.io/v3/reservations?reservation_code={reservation_code}"

    headers = {
        "accept": "application/json",
        "Hostex-Access-Token": HOSTEX_API
    }

    response = requests.get(url, headers=headers)

    deets = j.loads(response.text)["data"]["reservations"][0]

    result = {
        "reservation_code":reservation_code,
        "checkin":datetime.strptime(deets["check_in_date"],"%Y-%m-%d").strftime("%m-%d-%Y"),
        "checkout":datetime.strptime(deets["check_out_date"],"%Y-%m-%d").strftime("%m-%d-%Y"),
        "apartment":APARTMENT_MAPPING_INVERSE[str(deets["property_id"])],
        "conversation_id":deets["conversation_id"]
    }

    return result

def check_scheduled_email(reservation_id:str=None):
    resend.api_key = os.getenv("RESEND_API_KEY")
    emails = resend.Emails.list()
    reservation_details = get_reservation_details(reservation_id)
    print([email for email in emails["data"]])
    emails = [email for email in emails["data"] 
            if email["scheduled_at"] is not None 
            and reservation_details["apartment"] in email["html"] 
            and reservation_details["checkin"] in email["html"] 
            and reservation_details["checkout"] in email["html"]]
    
    if len(subs) != 0:
        return {
            "scheduled_to_send":subs[0]["scheduled_at"],
            "status":subs[0]["last_event"]
        }
    
    else:
        return None

def check_form_message(reservation_id: str) -> bool:
    reservation_details = get_reservation_details(reservation_id)

    hostex_url = f"https://api.hostex.io/v3/conversations/{reservation_details['conversation_id']}"

    headers = {
        "accept": "application/json",
        "Hostex-Access-Token": HOSTEX_API,
    }

    response = requests.get(
        hostex_url,
        headers=headers,
        timeout=10,
    )

    response.raise_for_status()

    messages = response.json()["data"]["messages"]

    for message in messages:
        if "https://docs.google.com/forms" in message["content"]:
            return True

    return False


def get_registration_status(reservation_id: str) -> dict:

    response = {
        "status": "good",
        "gform": {
            "scheduled": False,
            "scheduled_at": None,
            "sent": False,
        },
        "pdf": {
            "filled": False,
            "scheduled_at": None,
            "sent_to_aquatika": False,
            "status": None,
        },
    }

    try:
        cron_details = get_cron_details(reservation_id)

        response["gform"]["scheduled"] = True
        response["gform"]["scheduled_at"] = (cron_details["StartDate"].strftime("%m-%d-%Y"))

        return response

    except cron.exceptions.ResourceNotFoundException:
        pass

    if check_form_message(reservation_id):
        response["gform"]["sent"] = True
    else:
        response["status"] = "bad"
        return response

    email = check_scheduled_email(reservation_id)

    if email:
        response["gform"]["sent"] = True

        response["pdf"]["filled"] = True
        response["pdf"]["scheduled_at"] = email["scheduled_to_send"]
        response["pdf"]["status"] = email["status"]

        return response

    return response

print(check_scheduled_email("0-HMWN9ZP2QJ-ieyf2y4kkt"))