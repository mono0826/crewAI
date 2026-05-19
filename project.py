import warnings
warnings.filterwarnings('ignore')

import os
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
def load_env() -> None:
    """加载 .env：先读与 mini_claude 包同级的项目目录（含 pyproject 的 python/），再由 cwd 下 .env 覆盖。"""

    pkg_root = Path(__file__).resolve().parent
    pkg_env = pkg_root / ".env"
    cwd_env = Path.cwd() / ".env"

    if pkg_env.is_file():
        load_dotenv(pkg_env)
    if cwd_env.is_file():
        load_dotenv(cwd_env, override=True)

# load api keys
load_env()


from crewai import Agent, Task, Crew, agents
from crewai.process import Process
from crewai_tools import FileWriterTool

file_writer = FileWriterTool()

planner = Agent(
    role="项目负责人",
    goal="完成对当前目录下的项目crewai的完整说明文档，并保存在docs/crewai文件夹下，文件名为project_specification.md",
    backstory="你作为一个项目负责人，需要仔细查看当前项目，并制定一个项目说明书，"
    "需要包含整个项目的执行流程，agents几个核心模块的实现流程，"
    "比如memory是怎么实现长短期记忆的；"
    "tool是怎么调用的，在调用失败时怎么处理的，在调用时如果陷入循环怎么处理的；在执行复杂任务时是怎么规划的；"
    "多agent之间是怎么统一通信协议的以及调用方式，等等；"
    "这些需要你这个项目负责人去详细阅读代码，并将其保存为md文件，必要时需绘制流程图作补充说明",
    verbose=True
)

reviewer = Agent(
    role="审查员",
    goal="审查项目负责人制定的项目说明书，并提出修改意见",
    backstory="你作为一个审查员，需要仔细审查项目负责人制定的项目说明书，并根据项目实际情况提出修改意见，"
    "并将其保存为docs/crewai/audit_report.md文件",
    verbose=True
)

writer = Agent(
    role="项目文档编写者",
    goal="根据审查员提出的修改意见，修改项目说明书，并保存在docs/crewai文件夹下",
    backstory="你作为一个项目文档编写者，需要根据审查员提出的修改意见，修改项目说明书，"
    "注意在最后保存的时候，需要一个模块保存为一个md文件，方便查阅"
    "注意在编写过程中，需要根据当前项目实现",
    verbose=True
)

plan_task = Task(
    description="完成当前目录下的项目crewai的完整说明文档",
    expected_output="一份完整的项目说明文档，保存在docs/crewai文件夹下，文件名为project_specification.md",
    agent=planner,
    tools=[file_writer]
)

review_task = Task(
    description="审查项目负责人制定的项目说明书，并提出修改意见",
    expected_output="一份完整的审查报告，保存在docs/crewai文件夹下，文件名为audit_report.md",
    agent=reviewer,
    tools=[file_writer],
)

write_task = Task(
    description="根据审查员提出的修改意见，修改项目说明书，需要将每一个模块点进行详细的补充说明，并保存在docs/crewai文件夹下",
    expected_output="一系列完整的项目说明文档，保存在docs/crewai文件夹下",
    agent=writer,   
    tools=[file_writer]
)

crew = Crew(
    agents=[planner, reviewer, writer],
    tasks=[plan_task, review_task, write_task],
    process=Process.sequential,
    verbose=True
)

# run the crew
crew.kickoff()