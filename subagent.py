from anthropic import Anthropic
from config import settings
from utils import calculate_subagent_cost
from rich.console import Console
from rich.panel import Panel
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential
from exceptions import APIError
from typing import Dict, Any, List, Tuple, Optional

console = Console()

class SubAgent:
    def __init__(self, anthropic_client: Anthropic, model: str, tavily_client: TavilyClient):
        self.anthropic_client = anthropic_client
        self.model = model
        self.tavily_client = tavily_client
        self.total_cost = 0.0

    @retry(stop=stop_after_attempt(settings.RETRY_ATTEMPTS), wait=wait_exponential(multiplier=1, min=4, max=60))
    def process_subtask(self, prompt: str, search_query: Optional[str] = None, previous_haiku_tasks: Optional[List[Dict[str, str]]] = None, use_search: bool = False, continuation: bool = False) -> str:
        if previous_haiku_tasks is None:
            previous_haiku_tasks = []

        continuation_prompt = "Continuing from the previous answer, please complete the response."
        system_message = "Previous Haiku tasks:\n" + "\n".join(
            f"Task: {task['task']}\nResult: {task['result']}" for task in previous_haiku_tasks)
        if continuation:
            prompt = continuation_prompt

        qna_response = None
        if search_query and use_search:
            try:
                qna_response = self.tavily_client.qna_search(query=search_query)
                console.print(f"QnA response: {qna_response}", style="yellow")
            except Exception as e:
                console.print(Panel(f"Error in calling Tavily QnA Search: [bold]{str(e)}[/bold]", title="[bold red]QnA Search Error[/bold red]", title_align="left", border_style="red"))
                raise APIError(f"Error in calling Tavily QnA Search: {str(e)}") from e

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        ]

        if qna_response:
            messages[0]["content"].append({"type": "text", "text": f"\nSearch Results:\n{qna_response}"})

        try:
            haiku_response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=messages,
                system=system_message
            )
        except Exception as e:
            console.print(
                Panel(f"Error in calling SubAgent: [bold]{str(e)}[/bold]", title="[bold red]SubAgent Error[/bold red]",
                      title_align="left", border_style="red"))
            raise APIError(f"Error in calling Anthropic API: {str(e)}") from e

        response_text = haiku_response.content[0].text
        console.print(
            f"Input Tokens: {haiku_response.usage.input_tokens}, Output Tokens: {haiku_response.usage.output_tokens}")
        total_cost = calculate_subagent_cost(self.model, haiku_response.usage.input_tokens,
                                             haiku_response.usage.output_tokens)
        self.total_cost += total_cost
        console.print(f"Sub-agent Cost: ${total_cost:.4f}")

        if haiku_response.usage.output_tokens >= 4000:  # Threshold set to 4000 as a precaution
            console.print(
                "[bold yellow]Warning:[/bold yellow] Output may be truncated. Attempting to continue the response.")
            continuation_response_text = self.process_subtask(prompt, search_query, previous_haiku_tasks, use_search,
                                                              continuation=True)
            response_text += continuation_response_text

        console.print(Panel(response_text, title="[bold blue]Haiku Sub-agent Result[/bold blue]", title_align="left",
                            border_style="blue", subtitle="Task completed, sending result to Opus 👇"))
        return response_text