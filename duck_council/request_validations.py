from constants import Constants 
from helpers import create_server_response

def prompt_request_validation(request):
    data = request.get_json()
    situation = data.get('situation')
    action = data.get('action')

    if not situation:
        return create_server_response(
            msg="Missing situation key",
            data=None,
            status_code=Constants.http_status_codes.BAD_REQUEST
        ) 

    if not action:
        return create_server_response(
            msg="Missing action key",
            data=None,
            status_code=Constants.http_status_codes.BAD_REQUEST
        )