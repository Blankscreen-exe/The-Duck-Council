from flask import jsonify
from constants import Constants
from config import BASE_URL, ALLOWED_AGENT_LIST

def create_server_response(msg: str, data:any, status_code:int, is_jsonify:bool=False):
    response = {
        "status": status_code,
        "message": msg,
        "data": data
        }
    if is_jsonify:
        response = jsonify(response)
    return response, status_code

def get_image_url(duck_name):
    return BASE_URL + '/images/' + str(duck_name) + '.jpg'

def is_available(duck_name):
    return True if duck_name in ALLOWED_AGENT_LIST else False