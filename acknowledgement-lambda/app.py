import boto3
import json
import os

lambda_client = boto3.client("lambda")

def lambda_handler(event, context):
    body = event.get("body")

    lambda_client.invoke(
        FunctionName=os.getenv("CRON_LAMBDA"),
        InvocationType="Event",
        Payload=body.encode("utf-8")  # boto3 expects bytes or a file-like object
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Accepted"})
    }