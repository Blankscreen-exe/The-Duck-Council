from .crew import DuckCouncil
import json

def evaluate_action(situation: str, action: str):
    # prompt = f"Situation: {situation}\nAction: {action}"
    # crew = DuckCouncil().crew()
    # result = crew.kickoff(inputs={"task": prompt})
    # return result

    prompt = f"Situation: {situation}\nAction: {action}"
    crew_instance = DuckCouncil().crew()
    result = crew_instance.kickoff(inputs={"task": prompt})
    print('=========RESULT==============')
    print(result)
    parsed_results = []

    for task_output in result.tasks_output:
        try:
            raw = json.loads(task_output.raw)
        except Exception as e:
            raw = {"score": None, "reasoning": f"Failed to parse response: {str(e)}"}

        parsed_results.append({
            "name": task_output.agent.strip(),
            "score": raw.get("score"),
            "reasoning": raw.get("reasoning")
        })
