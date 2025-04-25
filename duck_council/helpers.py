from flask import jsonify
from constants import Constants

def create_server_response(msg: str, data:any, status_code:int, is_jsonify:bool=False):
    response = {
        "status": status_code,
        "message": msg,
        "data": data
        }
    if is_jsonify:
        response = jsonify(response)
    return response, status_code