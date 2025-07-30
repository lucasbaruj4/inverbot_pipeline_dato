from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
from crewai_tools import (
    SerperDevTool,
    FirecrawlScrapeWebsiteTool,
    FirecrawlCrawlWebsiteTool
)

serper_dev_tool = SerperDevTool()
firecrawl_search_tool = FirecrawlCrawlWebsiteTool()
firecrawl_search_scrape_tool = FirecrawlScrapeWebsiteTool()

@CrewBase
class InverbotPipelineDato():
    """InverbotPipelineDato crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    model_llm = os.environ['MODEL']
    model_embedder = os.environ['EMBEDDER']
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def extractor(self) -> Agent:
        return Agent(
            config=self.agents_config['extractor'],
            verbose=True,
            llm=self.model_llm,
            tools=[
                serper_dev_tool,
                firecrawl_search_scrape_tool,
                firecrawl_search_tool
            ]
        )

    @agent
    def processor(self) -> Agent:
        return Agent(
            config=self.agents_config['processor'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm
        )
        
    @agent
    def vector(self) -> Agent:
        return Agent(
            config=self.agents_config['vector'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm
        )

    @agent
    def loader(self) -> Agent:
        return Agent(
            config=self.agents_config['loader'], # type: ignore[index]
            verbose=True,
            llm=self.model_llm
        )

    @task
    def extract_task(self) -> Task:
        return Task(
            config=self.tasks_config['extract_task'], 
            
        )

    @task
    def process_task(self) -> Task:
        return Task(
            config=self.tasks_config['process_task'], 
            context=[self.extract_task()]
        )
        
    @task
    def vectorize_task(self) -> Task:
        return Task(
            config=self.tasks_config['vectorize_task'], 
            context=[self.process_task(), self.extract_task()]
            
        )
        
    @task
    def load_task(self) -> Task:
        return Task(
            config=self.tasks_config['load_task'], 
            context=[self.process_task(), self.vectorize_task()]
        )
        
    @crew
    def crew(self) -> Crew:
        """Creates the InverbotPipelineDato crew"""

        return Crew(
            agents=self.agents, 
            tasks=self.tasks, 
            process=Process.sequential,
            verbose=True,
            max_rpm=5
        )
