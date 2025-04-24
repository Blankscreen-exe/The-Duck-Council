from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from constants import Constants

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class DuckCouncil():
    """DuckCouncil crew"""

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @before_kickoff
    def before_kickoff_function(self, inputs):
        return inputs

    @after_kickoff
    def after_kickoff_function(self, result):
        return result
    
    def get_task_map(self):
        return {
            Constants.agent_names.PRAGMATIC: (self.pragmatic_duck(), self.pragmatic_reflection_task),
            Constants.agent_names.ETHICAL: (self.ethical_duck(), self.ethical_reflection_task),
            Constants.agent_names.WINNER: (self.winner_duck(), self.winner_reflection_task),
        }

    def run_duck(self, duck_name: str, situation: str, action: str):
        task_map = self.get_task_map()
        
        if duck_name not in task_map:
            raise ValueError(f"Invalid duck name '{duck_name}'. Choose from: {list(task_map.keys())}")

        agent, task_func = task_map[duck_name]
        task = task_func()

        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=True,
        )
        
        prompt = f"Situation: {situation}\nAction: {action}"
        return crew.kickoff(inputs={"task": prompt})

    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def pragmatic_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['pragmatic_duck'],
            verbose=True
        )

    @agent
    def ethical_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['ethical_duck'],
            verbose=True
        )
    
    @agent
    def winner_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['winner_duck'],
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def pragmatic_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['pragmatic_reflection'],
        )
    
    @task
    def ethical_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['ethical_reflection'],
        )
    
    @task
    def winner_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['winner_reflection'],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the DuckCouncil crew"""

        return Crew(
            agents=self.agents, 
            tasks=self.tasks, 
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
 