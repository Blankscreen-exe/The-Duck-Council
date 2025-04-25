from flask import Flask, request
from duck_council.api import evaluate_action
from constants import Constants
from config import APP_HOST, APP_PORT, DEBUG
from helpers import create_server_response
from request_validations import prompt_request_validation
from src.duck_council.config.duck_data import duck_data
app = Flask(__name__)

@app.route(Constants.routes.health, methods=[Constants.http_methods.GET])
def index():
    return '<h1>Duck Council is live!</h1>'

@app.route(Constants.routes.duck_data, methods=[Constants.http_methods.GET])
def duck_profiles():
    return create_server_response(
        msg=str(len(duck_data))+' records fetched successfully',
        data=duck_data,
        status_code=Constants.http_status_codes.OK)

@app.route(Constants.routes.prompt, methods=[Constants.http_methods.POST])
def handle_prompt():

    prompt_request_validation(request)
    
    data = request.get_json()
    situation = data.get('situation')
    action = data.get('action')
    
    try:
        responses = evaluate_action(situation=situation, action=action)
    except Exception as e:
        return create_server_response(
            msg="There was a problem with CrewAI response",
            data=e,
            status_code=Constants.http_status_codes.SERVER_ERROR,
            is_jsonify=True
        )    

    return create_server_response(
        msg="Data fetched successfully",
        data=responses,
        status_code=Constants.http_status_codes.OK,
        is_jsonify=True
    ) 

if __name__ == '__main__':
    app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG)