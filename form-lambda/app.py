import fitz
import resend
import boto3
import os
import json
import requests
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import base64

s3 = boto3.client("s3")

APARTMENT_MAPPING={
    "12664173":"303",
    "12664174":"4702",
    "12664175":"6002",
    "12664176":"1301"
}

def _get_pdf():

    s3.download_file(
        os.getenv("PDF_BUCKET_NAME"),
        "RegistroAquatika.pdf",
        "/tmp/RegistroAquatika.pdf"
    )
def _save_pdf(reservation_code:str):

    s3.upload_file(
        f"/tmp/RegistroAquatika-{reservation_code}.pdf",
        os.getenv("PDF_BUCKET_NAME"),
        f"Reservations/RegistroAquatika-{reservation_code}.pdf"
    )
def _get_signature():

    s3.download_file(
        os.getenv("PDF_BUCKET_NAME"),
        "firma.png",
        "/tmp/firma.png"
    )

def _sign_pdf(page:fitz.Page):

    rect = fitz.Rect(261.04998779296875 + 2, 727.3233642578125-25, 290.3943176269531+120, 739.5446166992188+28)

    x = 160
    y = 216.31362915039062 - 28

    rect2 = fitz.Rect(
        x,
        y,
        x + rect.width,
        y + rect.height,
    )

    page.insert_image(rect,filename="/tmp/firma.png")
    page.insert_image(rect2,filename="/tmp/firma.png")

    timestamp = datetime.now(ZoneInfo("America/Puerto_Rico")).strftime("%m/%d/%Y %I:%M:%S %p AST")

    text = (
            f"Digitally signed by\n"
            f"Edwin Corujo\n"
            f"Date: {timestamp}"
        )

    text_rect = fitz.Rect(
        rect.x1 - 6,
        rect.y0 + 18,
        rect.x1 + 120,
        rect.y1 + 25,
    )

    text_rect2 = fitz.Rect(
        rect2.x1 - 6,
        rect2.y0 + 18,
        rect2.x1 + 100,  # was +120
        rect2.y1 + 18,   # was +25
    )

    page.insert_textbox(
        text_rect,
        text,
        fontsize=6.5,
        color=(0.35, 0.35, 0.35),
        align=fitz.TEXT_ALIGN_LEFT,
    )

    page.insert_textbox(
        text_rect2,
        text,
        fontsize=4.0,
        color=(0.35, 0.35, 0.35),
        align=fitz.TEXT_ALIGN_LEFT,
    )

def _fix_date(page:fitz.Page):

    compdatewidget = next((widget for widget in page.widgets() if widget.field_name == "Date1_af_date"),None)

    if compdatewidget is None:
        raise ValueError("Could not find PDF widget 'Date1_af_date'.")

    rect = compdatewidget.rect

    page.delete_widget(compdatewidget)

    page.draw_rect(
        rect,
        color=(1,1,1),
        fill=(1,1,1)
    )

    page.insert_text(
        (rect.x0 + 2, rect.y1 - 2),
        str(datetime.now(ZoneInfo("America/Puerto_Rico")).strftime("%m/%d/%y")),
        fontsize=12
    )

def _fix_guest_count(page:fitz.Page,count:str):
    widget = next((i for i in page.widgets() if i.field_name == "Dropdown5"),None)

    if widget is None:
        raise ValueError("Could not find PDF widget 'Dropdown5'.")

    rect = widget.rect

    page.delete_widget(widget)

    page.draw_rect(
        rect,
        color=(1,1,1),
        fill=(1,1,1)
    )

    page.insert_text(
        (rect.x0 + 2, rect.y1 - 2),
        count,
        fontsize=12
    )

def fill_aquatika_pdf(
        guest_names:list[str],
        reservation_guest:str,
        guest_phone:str,
        check_in_date:str,
        check_out_date:str,
        apartment:str,
        reservation_code:str
        ):

    fields = {
        "Apartment":apartment,
        "Guest name":reservation_guest,
        "Contact":guest_phone,
        "Desde":check_in_date,
        "Hasta":check_out_date
    }

    for index,name in enumerate(guest_names,start=1):
        fields[f"Huesped 1.{index}"] = name

    doc = fitz.open("/tmp/RegistroAquatika.pdf")

    try:
        page = doc[0]

        widgets = [widget for widget in page.widgets() if widget.field_name in fields.keys()]

        for widget in widgets:

            if widget.field_name == "Contact":
                rect = widget.rect
                point = fitz.Point(
                    rect.x0,
                    rect.y0 + 10  # move down 3 points
                )
                page.insert_text(
                    point,          # top-left corner
                    fields["Contact"],
                    fontsize=10
                )
                continue

            if widget.field_name == "Apartment":
                rect = widget.rect
                page.delete_widget(widget)
                point = fitz.Point(
                    rect.x0,
                    rect.y0 + 15  # move down 3 points
                )
                page.insert_text(
                    point,          # top-left corner
                    fields["Apartment"],
                    fontsize=10
                )

                continue

            widget.field_value = fields[widget.field_name]
            widget.update()

        _sign_pdf(page)
        _fix_date(page)
        _fix_guest_count(page,str(len(guest_names)+1))

        doc.need_appearances = True

        doc.save(f"/tmp/RegistroAquatika-{reservation_code}.pdf")
    finally:
        doc.close()

    return

def clean_event_body(event_body:str):
    obj = json.loads(event_body)
    questions = obj["submission"]
    result = {}
    result["primary_guest"] = questions["Primary Guest Full Name"]
    result["phone_nummber"] = questions["Phone number"]
    result["reservation_code"] = questions["Reservation ID"]
    result["guests"] = [questions[f"Guest {i} Full Name"] for i in range(2,11) if questions[f"Guest {i} Full Name"] not in [""," ","n/a","na","none"]]

    return result

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
        "checkin":datetime.strptime(deets["check_in_date"], "%Y-%m-%d").strftime("%m-%d-%Y"),
        "checkout":datetime.strptime(deets["check_out_date"], "%Y-%m-%d").strftime("%m-%d-%Y"),
        "apartment":deets["property_id"]
    }

    return result

def schedule_email(checkin_date:datetime,checkout_date:datetime,reservation_code:str,apt:str,main_guest:str):

    resend.api_key = os.getenv("RESEND_API_KEY")

    dt = datetime.strptime(checkin_date,"%m-%d-%Y").replace(tzinfo=ZoneInfo("America/Puerto_Rico")) - timedelta(days=2)
    dt = dt.replace(hour=9)

    with open(f"/tmp/RegistroAquatika-{reservation_code}.pdf","rb") as f:
        file_content = base64.b64encode(f.read()).decode("utf-8")

        email_payload = {
            "from": "edwincorujo@strmanagementpr.com",
            "to": os.getenv("TO_EMAIL"),
            "cc": [email.strip() for email in os.getenv("CC_EMAIL").split(",") if email.strip()],
            "subject": f"Registro de prestado para el APT {apt} - {main_guest}",
            "html": f"""
            <p>Saludos:</p>

            <p>
            Adjunto el registro de prestado para el APT
            <strong>{apt}</strong> asignado a <strong>{main_guest}</strong>
            del <strong>{checkin_date}</strong> al
            <strong>{checkout_date}</strong>.
            </p>

            <p>Favor de confirmar recibo.</p>
            <p>Gracias, EC</p>
            """,
            "attachments": [
                {
                    "filename": f"APT {apt} - {main_guest} {checkin_date} a {checkout_date}.pdf",
                    "content": file_content
                }
            ]
        }

        if dt > datetime.now(ZoneInfo("America/Puerto_Rico")):
            email_payload["scheduled_at"] = dt.isoformat()

        resend.Emails.send(email_payload)

        email_payload["to"] = email_payload["cc"][0]
        email_payload.pop('cc')
        email_payload.pop('scheduled_at',None)
        email_payload["subject"] = f"Email schedule confirmation for {apt} on {dt}"

        resend.Emails.send(email_payload)

        return


def lambda_handler(event,context):

    clean_event = clean_event_body(event["body"])

    try:

        deets = get_reservation_details(clean_event["reservation_code"])

        _get_pdf()

        _get_signature()

        fill_aquatika_pdf(
            guest_names=clean_event["guests"],
            reservation_guest=clean_event["primary_guest"],
            guest_phone=clean_event["phone_nummber"],
            check_in_date=deets["checkin"],
            check_out_date=deets["checkout"],
            apartment=APARTMENT_MAPPING[str(deets["apartment"])],
            reservation_code=clean_event["reservation_code"]
            )

        _save_pdf(clean_event["reservation_code"])

        schedule_email(deets["checkin"],deets["checkout"],clean_event["reservation_code"],APARTMENT_MAPPING[str(deets["apartment"])],clean_event["primary_guest"])

    except Exception as e:

        print(e)

        return {"statusCode":500}

    return {"statusCode":200}