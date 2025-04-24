from flask import jsonify
from constants import Constants

def create_server_response(msg: str, data:any, status_code:int):
    return jsonify({
            "status": status_code,
            "message": msg,
            "data": data
         }), status_code