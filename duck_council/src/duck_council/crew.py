from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff
from constants import Constants
from pprint import pprint as pp
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
        agent_task = {
            Constants.agent_names.LAWYER: (self.lawyer_duck(), self.lawyer_reflection_task),
            Constants.agent_names.WITCH: (self.witch_duck(), self.witch_reflection_task),
            Constants.agent_names.DOCTOR: (self.doctor_duck(), self.doctor_reflection_task),
            Constants.agent_names.RICH: (self.rich_duck(), self.rich_reflection_task),
            Constants.agent_names.GAMER: (self.gamer_duck(), self.gamer_reflection_task),
            Constants.agent_names.GANGSTA: (self.gangsta_duck(), self.gangsta_reflection_task),
            Constants.agent_names.SERIAL_KILLER: (self.serial_killer_duck(), self.serial_killer_reflection_task),
            Constants.agent_names.DIPLOMAT: (self.diplomat_duck(), self.diplomat_reflection_task),
            Constants.agent_names.TECHNO: (self.techno_duck(), self.techno_reflection_task),
            Constants.agent_names.KING: (self.king_duck(), self.king_reflection_task),
            Constants.agent_names.SPIRITUAL_MEDIUM: (self.spiritual_medium_duck(), self.spiritual_medium_reflection_task),
            Constants.agent_names.DETECTIVE: (self.detective_duck(), self.detective_reflection_task),
            Constants.agent_names.REBEL: (self.rebel_duck(), self.rebel_reflection_task),
        }
        return agent_task

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
    def lawyer_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['lawyer_duck'],
            verbose=True
        )

    @agent
    def witch_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['witch_duck'],
            verbose=True
        )
    
    @agent
    def doctor_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['doctor_duck'],
            verbose=True
        )
    
    @agent
    def rich_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['rich_duck'],
            verbose=True
        )
    
    @agent
    def gamer_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['gamer_duck'],
            verbose=True
        )
    
    @agent
    def serial_killer_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['serial_killer_duck'],
            verbose=True
        )
    
    @agent
    def diplomat_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['diplomat_duck'],
            verbose=True
        )
    
    @agent
    def techno_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['techno_duck'],
            verbose=True
        )
    
    @agent
    def king_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['king_duck'],
            verbose=True
        )
    
    @agent
    def spiritual_medium_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['spiritual_medium_duck'],
            verbose=True
        )
    
    @agent
    def detective_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['detective_duck'],
            verbose=True
        )
    
    @agent
    def rebel_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['rebel_duck'],
            verbose=True
        )
    
    @agent
    def gangsta_duck(self) -> Agent:
        return Agent(
            config=self.agents_config['gangsta_duck'],
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def lawyer_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['lawyer_reflection'],
        )
    
    @task
    def witch_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['witch_reflection'],
        )
    
    @task
    def doctor_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['doctor_reflection'],
        )

    @task
    def rich_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['rich_reflection'],
        )
    
    @task
    def gamer_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['gamer_reflection'],
        )
    
    @task
    def gangsta_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['gangsta_reflection'],
        )

    @task
    def serial_killer_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['serial_killer_reflection'],
        )
    
    @task
    def diplomat_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['diplomat_reflection'],
        )
    
    @task
    def techno_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['techno_reflection'],
        )

    @task
    def king_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['king_reflection'],
        )
    
    @task
    def spiritual_medium_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['spiritual_medium_reflection'],
        )
    
    @task
    def detective_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['detective_reflection'],
        )
    
    @task
    def rebel_reflection_task(self) -> Task:
        return Task(
            config=self.tasks_config['rebel_reflection'],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the DuckCouncil crew"""

        # return Crew(
        #     agents=self.agents, 
        #     tasks=self.tasks, 
        #     process=Process.sequential,
        #     verbose=True,
        #     # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        # )
 