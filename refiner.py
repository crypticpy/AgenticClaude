from anthropic import Anthropic
from config import settings
from utils import calculate_subagent_cost
from rich.console import Console
from rich.panel import Panel
from tenacity import retry, stop_after_attempt, wait_exponential
from exceptions import APIError
from typing import Dict, Any, List, Tuple, Optional

console = Console()

class Refiner:
    def __init__(self, anthropic_client: Anthropic, model: str):
        self.anthropic_client = anthropic_client
        self.model = model
        self.total_cost = 0.0

    @retry(stop=stop_after_attempt(settings.RETRY_ATTEMPTS), wait=wait_exponential(multiplier=1, min=4, max=60))
    def refine_output(self, objective: str, sub_task_results: List[str], filename: str, projectname: str, continuation: bool = False) -> str:
        console.print("\nCalling Opus to provide the refined final output for your objective:")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Objective: " + objective + "\n\nSub-task results:\n" + "\n".join(
                        sub_task_results) + "\n\nPlease review and refine the sub-task results into a cohesive final output. Add any missing information or details as needed. When working on code projects, ONLY AND ONLY IF THE PROJECT IS CLEARLY A CODING ONE please provide the following:\n1. Project Name: Create a concise and appropriate project name that fits the project based on what it's creating. The project name should be no more than 20 characters long.\n2. Folder Structure: Provide the folder structure as a valid JSON object, where each key represents a folder or file, and nested keys represent subfolders. Use null values for files. Ensure the JSON is properly formatted without any syntax errors. Please make sure all keys are enclosed in double quotes, and ensure objects are correctly encapsulated with braces, separating items with commas as necessary.\nWrap the JSON object in <folder_structure> tags.\n3. Code Files: For each code file, include ONLY the file name NEVER EVER USE THE FILE PATH OR ANY OTHER FORMATTING YOU ONLY USE THE FOLLOWING format 'Filename: <filename>' followed by the code block enclosed in triple backticks, with the language identifier after the opening backticks, like this:\n\n​python\n<code>\n​"}
                ]
            }
        ]

        try:
            opus_response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=messages
            )
        except Exception as e:
            console.print(
                Panel(f"Error in calling Refiner: [bold]{str(e)}[/bold]", title="[bold red]Refiner Error[/bold red]",
                      title_align="left", border_style="red"))
            raise APIError(f"Error in calling Anthropic API: {str(e)}") from e

        response_text = opus_response.content[0].text.strip()
        console.print(
            f"Input Tokens: {opus_response.usage.input_tokens}, Output Tokens: {opus_response.usage.output_tokens}")
        total_cost = calculate_subagent_cost(self.model, opus_response.usage.input_tokens,
                                             opus_response.usage.output_tokens)
        self.total_cost += total_cost
        console.print(f"Refine Cost: ${total_cost:.4f}")

        if opus_response.usage.output_tokens >= 4000 and not continuation:
            console.print(
                "[bold yellow]Warning:[/bold yellow] Output may be truncated. Attempting to continue the response.")
            continuation_response_text = self.refine_output(objective, sub_task_results + [response_text], filename,
                                                            projectname, continuation=True)
            response_text += "\n" + continuation_response_text

        console.print(Panel(response_text, title="[bold green]Final Output[/bold green]", title_align="left",
                            border_style="green"))
        return response_text