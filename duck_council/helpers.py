from flask import jsonify
from constants import Constants
from config import BASE_URL, ALLOWED_AGENT_LIST
from src.duck_council.config.duck_names import duck_names

def create_server_response(msg: str, data:any, status_code:int, is_jsonify:bool=False):
    response = {
        "status": status_code,
        "message": msg,
        "data": data
        }
    if is_jsonify:
        response = jsonify(response)
    return response, status_code

def get_image_url(duck_generic_name):
    return BASE_URL + '/images/' + str(duck_generic_name) + '.jpg'

def is_available(duck_generic_name):
    return True if duck_generic_name in ALLOWED_AGENT_LIST else False

def get_duck_name(duck_generic_name):
    return duck_names[duck_generic_name]