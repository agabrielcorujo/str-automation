from handlers import *
import json as j

ROUTE_METHOD_MAPPING = {
    "/default/reservations":"GET",
    "/default/pdfs":"GET",
    "/default/registration-status":"GET"
}
    
ROUTE_HANDLER_MAPPING = {
    "/default/reservations":get_reservations,
    "/default/pdfs":get_pdfs,
    "/default/registration-status":get_registration_status
    }

def lambda_handler(event,context):

    route = event["rawPath"]
    method = event["requestContext"]["http"]["method"]
    params = event.get("queryStringParameters") or None

    if route not in ROUTE_HANDLER_MAPPING or method != ROUTE_METHOD_MAPPING[route]:
        return {"statusCode":405,"body":j.dumps({"message":"Method not allowed."})}

    if params:
        return ROUTE_HANDLER_MAPPING[route](**params)

    else:
        
        body = j.loads(event["body"]) if event.get("body") else {}
        return ROUTE_HANDLER_MAPPING[route](**body)
