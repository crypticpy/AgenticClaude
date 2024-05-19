Welcome to the Agentic Framework for Claude! This project is designed to streamline AI-assisted task completion, leveraging the powerful capabilities of Anthropic's Claude models. Whether you're working on code tasks, document processing, or data analysis, this framework provides a robust and flexible solution to break down and automate your objectives.

## Overview

The Agentic Framework for Claude orchestrates multiple AI models to handle complex tasks efficiently. It divides objectives into manageable subtasks, processes them using Claude sub-agents, refines the results, and assembles a cohesive final output. With built-in logging, error handling, and cost management, this framework is designed to be both powerful and user-friendly.

## Features

- **Anthropic Integration**: Utilizes Claude-3 Opus, Sonnet, and Haiku models for diverse task handling.
- **Task Orchestration**: Breaks down objectives into subtasks and processes them iteratively.
- **Cost Management**: Monitors and controls the cost of AI operations.
- **Logging and Error Handling**: Comprehensive logging and custom error classes ensure smooth operation.
- **Extensible Design**: Easily extendable to include additional models and functionality.

## Enviorment Variables 
Configure Environment Variables:
Create a .env file in the root directory and add your API keys.

ANTHROPIC_API_KEY=your_anthropic_api_key

TAVILY_API_KEY=your_tavily_api_key

LOG_LEVEL=INFO

LOG_FILE=app.log

TIMESTAMP_FORMAT=%Y-%m-%d_%H-%M-%S

MAX_OBJECTIVE_LENGTH=50

RETRY_ATTEMPTS=5

RETRY_DELAY=10

## Usage
To use the framework, run the main script with the desired objective:

python main.py "Your objective here" --file path/to/input/file --search --model claude-3-opus-20240229 --cost-limit 10.0

## Command-Line Arguments
objective (str): The objective or goal to achieve.

--file (optional, str): Path to the input file.

--search (optional): Enable search functionality.

--model (optional, str): Choose the AI model for processing (claude-3-opus-20240229, claude-3-haiku-20240307, claude-3-sonnet-20240229).

--cost-limit (optional, float): Set a cost limit for the task (default is 0.0 for no limit).
