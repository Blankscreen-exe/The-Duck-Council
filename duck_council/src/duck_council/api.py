from .crew import DuckCouncil
import json

def evaluate_action(situation: str, action: str):
    agents = ['winner','pragmatic','ethical']

    result = []
    for agent in agents:
        response = DuckCouncil().run_duck(duck_name=agent, situation=situation, action=action)
        response_dict = json.loads(str(response))
        response_dict['duck_name'] = agent
        result.append(response_dict)

    return result