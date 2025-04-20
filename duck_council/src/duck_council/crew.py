from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, before_kickoff, after_kickoff

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class DuckCouncil():
    """DuckCouncil crew"""

    @before_kickoff
    def before_kickoff_function(self, inputs):
        print(f"Before kickoff function with inputs: {inputs}")
        return inputs # You can return the inputs or modify them as needed

    @after_kickoff
    def after_kickoff_function(self, result):
        print(f"After kickoff function with result: {result}")
        return result # You can return the result or modify it as needed

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

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
    def reflection_task(self) -> Task:
        print('----------------------------------------')
        print(self.tasks_config)
        print('----------------------------------------')
        return Task(
            config=self.tasks_config['reflection'],
        )

    # @task
    # def reporting_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['reporting_task'],
    #         output_file='report.md'
    #     )

    @crew
    def crew(self) -> Crew:
        """Creates the DuckCouncil crew"""
        prompt_template = "Given a situation and a proposed action, evaluate its suitability. {task}"

        agent_list = [
                ("pragmatic duck", self.pragmatic_duck()),
                ("ethical duck", self.ethical_duck()),
                ("winner duck", self.winner_duck()),
            ]
        
        tasks = []

        for name, agent in agent_list:
            task = Task(
                config=self.tasks_config['reflection'],
                agent=agent,
                output_format='raw'
            )
            # Task(
            #     output_format='raw',
            #     description=prompt_template,
            #     expected_output='The duck gives a suitability score (0-100) and their reasoning. The output should strictly be in the form of a json string like: {"score":<float>, "reasoning":"..." }',
            # )
            tasks.append(task)

        return Crew(
            agents=[agent for _, agent in agent_list], 
            tasks=tasks, 
            # process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
