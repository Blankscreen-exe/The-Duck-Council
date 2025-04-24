from flask import Flask, request, jsonify
from duck_council.api import evaluate_action

app = Flask(__name__)

# Health check
@app.route('/')
def index():
    return 'Duck Council is live!'

@app.route('/prompt', methods=['POST'])
def handle_prompt():
    data = request.get_json()
    situation = data.get('situation')
    action = data.get('action')

    if not situation or not action:
        return jsonify({"error": "Missing prompt"}), 400

    responses = evaluate_action(situation=situation, action=action)

    return jsonify({
            "status": 200,
            "message": "Data fetched successfully",
            "data": responses
         }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)