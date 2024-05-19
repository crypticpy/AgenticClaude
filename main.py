import argparse
import logging
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from config import settings
from utils import (
    calculate_subagent_cost,
    read_file,
    create_folder_structure,
    extract_file_path,
    sanitize_objective,
    save_exchange_log,
    extract_project_name,
    extract_folder_structure_and_code
)
from orchestrator import Orchestrator
from subagent import SubAgent
from refiner import Refiner
from exceptions import APIError, FileIOError, ConfigurationError
from dependencies import get_anthropic_client, get_tavily_client
from anthropic import Anthropic
from tavily import TavilyClient

# Initialize the Rich Console
console = Console()

# Configure logging using structlog
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def main(anthropic_client: Anthropic, tavily_client: TavilyClient, objective: str, file_path: str, use_search: bool, model: str, cost_limit: float):
    file_content = None
    if file_path:
        try:
            file_content = read_file(file_path)
            objective = extract_file_path(objective, file_path)
        except FileIOError as e:
            logger.error(f"File read error: {str(e)}")
            console.print(Panel(f"File read error: [bold]{str(e)}[/bold]", title="[bold red]Error[/bold red]", title_align="left", border_style="red"))
            return

    task_exchanges = []
    haiku_tasks = []

    try:
        orchestrator = Orchestrator(anthropic_client, model)
        sub_agent = SubAgent(anthropic_client, model, tavily_client)
        refiner = Refiner(anthropic_client, model)

        while True:
            previous_results = [result for _, result in task_exchanges]
            if not task_exchanges:
                opus_result, file_content_for_haiku, search_query = orchestrator.generate_subtask(objective, file_content, previous_results, use_search)
            else:
                opus_result, _, search_query = orchestrator.generate_subtask(objective, previous_results=previous_results, use_search=use_search)

            if "The task is complete:" in opus_result:
                final_output = opus_result.replace("The task is complete:", "").strip()
                break
            else:
                sub_task_prompt = opus_result
                if file_content_for_haiku and not haiku_tasks:
                    sub_task_prompt = f"{sub_task_prompt}\n\nFile content:\n{file_content_for_haiku}"
                sub_task_result = sub_agent.process_subtask(sub_task_prompt, search_query, haiku_tasks, use_search)
                haiku_tasks.append({"task": sub_task_prompt, "result": sub_task_result})
                task_exchanges.append((sub_task_prompt, sub_task_result))
                file_content_for_haiku = None

            total_cost = orchestrator.total_cost + sub_agent.total_cost
            if cost_limit > 0.0 and total_cost > cost_limit:
                logger.warning(f"Cost limit of ${cost_limit:.4f} exceeded. Stopping task processing.")
                console.print(Panel(f"Cost limit of [bold]${cost_limit:.4f}[/bold] exceeded. Stopping task processing.",
                                    title="[bold yellow]Cost Limit Exceeded[/bold yellow]", title_align="left", border_style="yellow"))
                break

        sanitized_objective = sanitize_objective(objective)
        timestamp = datetime.now().strftime(settings.TIMESTAMP_FORMAT)
        refined_output = refiner.refine_output(objective, [result for _, result in task_exchanges], timestamp, sanitized_objective)

        project_name = extract_project_name(refined_output) or sanitized_objective
        folder_structure, code_blocks = extract_folder_structure_and_code(refined_output)
        create_folder_structure(project_name, folder_structure, code_blocks)

        truncated_objective = sanitized_objective[:settings.MAX_OBJECTIVE_LENGTH]
        filename = f"{timestamp}_{truncated_objective}.md"
        save_exchange_log(filename, objective, task_exchanges, refined_output)

        console.print(f"\n[bold]Refined Final output:[/bold]\n{refined_output}")
        console.print(f"\nFull exchange log saved to {filename}")
        console.print(f"\nTotal Cost: ${orchestrator.total_cost + sub_agent.total_cost + refiner.total_cost:.4f}")

    except (APIError, ConfigurationError) as e:
        logger.error(f"Error in processing task: {str(e)}")
        console.print(Panel(f"Error in processing task: [bold]{str(e)}[/bold]", title="[bold red]Error[/bold red]", title_align="left", border_style="red"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Assisted Task Completion")
    parser.add_argument("objective", help="The objective or goal to achieve")
    parser.add_argument("--file", help="Path to the input file (optional)")
    parser.add_argument("--search", action="store_true", help="Enable search functionality")
    parser.add_argument("--model", choices=["claude-3-opus-20240229", "claude-3-haiku-20240307", "claude-3-sonnet-20240229"],
                        default="claude-3-opus-20240229", help="Choose the AI model for processing")
    parser.add_argument("--cost-limit", type=float, default=0.0,
                        help="Set a cost limit for the task (0.0 for no limit)")
    args = parser.parse_args()

    anthropic_client = get_anthropic_client()
    tavily_client = get_tavily_client()

    main(anthropic_client, tavily_client, args.objective, args.file, args.search, args.model, args.cost_limit)