import json
import boto3 
import os
import requests
from datetime import datetime, timedelta

scheduler = boto3.client("scheduler")

def get_reservation_details(reservation_code:str)->dict:

    HOSTEX_API_KEY=os.getenv("HOSTEX_API_TOKEN")

    url = f"https://api.hostex.io/v3/reservations?reservation_code={reservation_code}"

    headers = {
        "accept": "application/json",
        "Hostex-Access-Token": HOSTEX_API_KEY
    }

    response = requests.get(url, headers=headers)

    deets = json.loads(response.text)["data"]["reservations"][0]

    result = {
        "reservation_code":reservation_code,
        "checkin":deets["check_in_date"],
        "checkout":deets["check_out_date"],
        "apartment":deets["property_id"],
        "status":deets["status"]
    }

    return result

def handle_updated_reservation(details:str):

    if details["status"] in  ["cancelled","check_in_details_updated"]:
        try:
            scheduler.delete_schedule(
                Name=f"{details['reservation_code']}-cronjob"
            )

            print(f"Deleted cron job for {details['reservation_code']}")

            if details["status"] == "check_in_details_updated":
                create_cronjob(details)

            return

        except Exception as e:
            print(f"Error deleting cron job for {details['reservation_code']}: {e}")
            raise
    else:
        return


def create_cronjob(deets:dict)->bool:

    deets.pop("status",None)

    runat = datetime.strptime(deets["checkin"], "%Y-%m-%d") 
    runat -= timedelta(days=int(os.getenv("DAYS_BEFORE")))
    runat = runat.replace(hour=17, minute=30)

    now = datetime.now()

    if runat <= now:
        runat = now + timedelta(minutes=15)
        runat = runat.replace(microsecond=0)

    scheduler.create_schedule(
        Name=f"{deets['reservation_code']}-cronjob",
        ScheduleExpression=f"at({runat.isoformat()})",
        FlexibleTimeWindow={
            "Mode": "OFF"
        },
        Target={
            "Arn": os.getenv("GFORM_LAMBDA_ARN"),
            "RoleArn": "arn:aws:iam::471354727816:role/str-automation-cron-role",
            "Input": json.dumps(deets)
        },
        ActionAfterCompletion="DELETE"
    )

    print(f"cron scheduled for {deets['reservation_code']} at {runat}")

    return True

def lambda_handler(event,context):

    reservation_code = event["reservation_code"]

    try:
        details = get_reservation_details(reservation_code)

        if event["event"] == "reservation_updated":
            handle_updated_reservation(details)
            return {"statusCode":200}

        else:
            create_cronjob(details)
            return {"statusCode":200}

    except Exception as e:
        print(e)
        return {"statusCode":200}


