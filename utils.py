import re
import os
import json
from rich.console import Console
from rich.panel import Panel
from tenacity import retry, stop_after_attempt, wait_fixed
from exceptions import FileIOError
from config import settings
from typing import Dict, Any, List, Tuple, Optional

console = Console()

def calculate_subagent_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = {
        "claude-3-opus-20240229": {"input_cost_per_mtok": 15.00, "output_cost_per_mtok": 75.00},
        "claude-3-haiku-20240307": {"input_cost_per_mtok": 0.25, "output_cost_per_mtok": 1.25},
        "claude-3-sonnet-20240229": {"input_cost_per_mtok": 3.00, "output_cost_per_mtok": 15.00},
    }
    input_cost = (input_tokens / 1_000_000) * pricing[model]["input_cost_per_mtok"]
    output_cost = (output_tokens / 1_000_000) * pricing[model]["output_cost_per_mtok"]
    return input_cost + output_cost

@retry(stop=stop_after_attempt(settings.RETRY_ATTEMPTS), wait=wait_fixed(settings.RETRY_DELAY))
def read_file(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except IOError as e:
        raise FileIOError(f"Error reading file: {file_path}") from e

def create_folder_structure(project_name: str, folder_structure: Dict[str, Any], code_blocks: List[Tuple[str, str]]) -> None:
    try:
        os.makedirs(project_name, exist_ok=True)
        console.print(Panel(f"Created project folder: [bold]{project_name}[/bold]", title="[bold green]Project Folder[/bold green]", title_align="left", border_style="green"))
    except OSError as e:
        console.print(Panel(f"Error creating project folder: [bold]{project_name}[/bold]\nError: {e}", title="[bold red]Project Folder Creation Error[/bold red]", title_align="left", border_style="red"))
        return

    create_folders_and_files(project_name, folder_structure, code_blocks)

def create_folders_and_files(current_path: str, structure: Dict[str, Any], code_blocks: List[Tuple[str, str]]) -> None:
    for key, value in structure.items():
        path = os.path.join(current_path, key)
        if isinstance(value, dict):
            try:
                os.makedirs(path, exist_ok=True)
                console.print(Panel(f"Created folder: [bold]{path}[/bold]", title="[bold blue]Folder Creation[/bold blue]", title_align="left", border_style="blue"))
                create_folders_and_files(path, value, code_blocks)
            except OSError as e:
                console.print(Panel(f"Error creating folder: [bold]{path}[/bold]\nError: {e}", title="[bold red]Folder Creation Error[/bold red]", title_align="left", border_style="red"))
        else:
            code_content = next((code for file, code in code_blocks if file == key), None)
            if code_content:
                try:
                    with open(path, 'w') as file:
                        file.write(code_content)
                    console.print(Panel(f"Created file: [bold]{path}[/bold]", title="[bold green]File Creation[/bold green]", title_align="left", border_style="green"))
                except IOError as e:
                    console.print(Panel(f"Error creating file: [bold]{path}[/bold]\nError: {e}", title="[bold red]File Creation Error[/bold red]", title_align="left", border_style="red"))
            else:
                console.print(Panel(f"Code content not found for file: [bold]{key}[/bold]", title="[bold yellow]Missing Code Content[/bold yellow]", title_align="left", border_style="yellow"))

def extract_file_path(objective: str, file_path: str) -> str:
    return objective.split(file_path)[0].strip() if file_path in objective else objective

def sanitize_objective(objective: str) -> str:
    return re.sub(r'\W+', '_', objective)

def extract_project_name(refined_output: str) -> Optional[str]:
    project_name_match = re.search(r'Project Name: (.*)', refined_output)
    return project_name_match.group(1).strip() if project_name_match else None

def extract_folder_structure_and_code(refined_output: str) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    folder_structure_match = re.search(r'<folder_structure>(.*?)</folder_structure>', refined_output, re.DOTALL)
    folder_structure = json.loads(folder_structure_match.group(1).strip()) if folder_structure_match else {}
    code_blocks = re.findall(r'Filename: (\S+)\s*```[\w]*\n(.*?)\n```', refined_output, re.DOTALL)
    return folder_structure, code_blocks

def save_exchange_log(filename: str, objective: str, task_exchanges: List[Tuple[str, str]], refined_output: str) -> None:
    exchange_log = f"Objective: {objective}\n\n" + "=" * 40 + " Task Breakdown " + "=" * 40 + "\n\n"
    for i, (prompt, result) in enumerate(task_exchanges, start=1):
        exchange_log += f"Task {i}:\nPrompt: {prompt}\nResult: {result}\n\n"
    exchange_log += "=" * 40 + " Refined Final Output " + "=" * 40 + "\n\n" + refined_output

    try:
        with open(filename, 'w') as file:
            file.write(exchange_log)
    except IOError as e:
        console.print(Panel(f"Error saving exchange log: [bold]{filename}[/bold]\nError: {e}", title="[bold red]Exchange Log Save Error[/bold red]", title_align="left", border_style="red"))