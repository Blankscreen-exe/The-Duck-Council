from .crew import DuckCouncil

def evaluate_action(situation: str, action: str):
    prompt = f"Situation: {situation}\nAction: {action}"
    crew = DuckCouncil().crew()
    result = crew.kickoff(inputs={"task": prompt})
    return result
    # Normalize result
    if isinstance(result, list):
        return {"reflections": result}
    else:
        return {"reflections": [result]}
    