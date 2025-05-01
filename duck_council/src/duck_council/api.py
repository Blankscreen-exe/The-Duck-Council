from .crew import DuckCouncil
from config import ALLOWED_AGENT_LIST
import json
from helpers import get_image_url

def evaluate_action(situation: str, action: str):
    agents = ALLOWED_AGENT_LIST

    result = []
    for agent in agents:
        response = DuckCouncil().run_duck(duck_name=agent, situation=situation, action=action)
        response_dict = json.loads(str(response))
        response_dict['duck_name'] = agent
        response_dict['image'] = get_image_url(agent)
        result.append(response_dict)

    return result