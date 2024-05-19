from anthropic import Anthropic
from config import settings
from utils import calculate_subagent_cost
from rich.console import Console
from rich.panel import Panel
import re
import json
from tenacity import retry, stop_after_attempt, wait_exponential
from exceptions import APIError
from typing import Dict, Any, List, Tuple, Optional

console = Console()

class Orchestrator:
    def __init__(self, anthropic_client: Anthropic, model: str):
        self.anthropic_client = anthropic_client
        self.model = model
        self.total_cost = 0.0

    @retry(stop=stop_after_attempt(settings.RETRY_ATTEMPTS), wait=wait_exponential(multiplier=1, min=5, max=60))
    def generate_subtask(self, objective: str, file_content: Optional[str] = None, previous_results: Optional[List[str]] = None, use_search: bool = False) -> Tuple[str, Optional[str], Optional[str]]:
        console.print(f"\n[bold]Calling Orchestrator for your objective[/bold]")
        previous_results_text = "\n".join(previous_results) if previous_results else "None"
        if file_content:
            console.print(
                Panel(f"File content:\n{file_content}", title="[bold blue]File Content[/bold blue]", title_align="left",
                      border_style="blue"))

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text",
                     "text": f"Based on the following objective{' and file content' if file_content else ''}, and the previous sub-task results (if any), please break down the objective into the next sub-task, and create a concise and detailed prompt for a subagent so it can execute that task. IMPORTANT!!! when dealing with code tasks make sure you check the code for errors and provide fixes and support as part of the next sub-task. If you find any bugs or have suggestions for better code, please include them in the next sub-task prompt. Please assess if the objective has been fully achieved. If the previous sub-task results comprehensively address all aspects of the objective, include the phrase 'The task is complete:' at the beginning of your response. If the objective is not yet fully achieved, break it down into the next sub-task and create a concise and detailed prompt for a subagent to execute that task.:\n\nObjective: {objective}" + (
                         '\\nFile content:\\n' + file_content if file_content else '') + f"\n\nPrevious sub-task results:\n{previous_results_text}"}
                ]
            }
        ]
        if use_search:
            messages[0]["content"].append({"type": "text",
                                           "text": "Please also generate a JSON object containing a single 'search_query' key, which represents a question that, when asked online, would yield important information for solving the subtask. The question should be specific and targeted to elicit the most relevant and helpful resources. Format your JSON like this, with no additional text before or after:\n{\"search_query\": \"<question>\"}\n"})

        try:
            opus_response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=messages
            )
        except Exception as e:
            console.print(Panel(f"Error in calling Orchestrator: [bold]{str(e)}[/bold]",
                                title="[bold red]Orchestrator Error[/bold red]", title_align="left",
                                border_style="red"))
            raise APIError(f"Error in calling Anthropic API: {str(e)}") from e

        response_text = opus_response.content[0].text
        console.print(
            f"Input Tokens: {opus_response.usage.input_tokens}, Output Tokens: {opus_response.usage.output_tokens}")
        total_cost = calculate_subagent_cost(self.model, opus_response.usage.input_tokens,
                                             opus_response.usage.output_tokens)
        self.total_cost += total_cost
        console.print(f"Orchestrator Cost: ${total_cost:.4f}")

        search_query = None
        if use_search:
            json_match = re.search(r'{.*}', response_text, re.DOTALL)
            if json_match:
                json_string = json_match.group()
                try:
                    search_query = json.loads(json_string)["search_query"]
                    console.print(Panel(f"Search Query: {search_query}", title="[bold blue]Search Query[/bold blue]",
                                        title_align="left", border_style="blue"))
                    response_text = response_text.replace(json_string, "").strip()
                except json.JSONDecodeError as e:
                    console.print(Panel(f"Error parsing JSON: {e}", title="[bold red]JSON Parsing Error[/bold red]",
                                        title_align="left", border_style="red"))
                    console.print(Panel(f"Skipping search query extraction.",
                                        title="[bold yellow]Search Query Extraction Skipped[/bold yellow]",
                                        title_align="left", border_style="yellow"))

        console.print(Panel(response_text, title=f"[bold green]Opus Orchestrator[/bold green]", title_align="left",
                            border_style="green", subtitle="Sending task to Haiku 👇"))
        return response_text, file_content, search_query