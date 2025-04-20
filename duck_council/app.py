from flask import Flask, request, jsonify
from src.duck_council.api import evaluate_action
import json

app = Flask(__name__)

@app.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.json
    situation = data.get("situation")
    action = data.get("action")

    if not situation or not action:
        return jsonify({"error": "Missing 'situation' or 'action'"}), 400

    reflections = evaluate_action(situation, action)
    print('---------- THUIS INFO RIGHT HERE ----------------')
    print(type(reflections))
    print(reflections)
    
    return jsonify({"reflections": json.loads(reflections)})

if __name__ == "__main__":
    app.run(debug=True)