import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

from src.agent.agent import WeatherAgent

load_dotenv()

console = Console()
SESSION_ID = "cli-session"

WELCOME = """
[bold cyan]🌦️  Weather AI Assistant[/bold cyan]
Ask me about weather anywhere in the world. I detect your language automatically!
Type [bold]/quit[/bold] to exit, [bold]/clear[/bold] to reset, [bold]/history[/bold] to see past messages.
"""


def print_user_message(msg: str):
    console.print(Panel(f"[green]{msg}[/green]", title="You", border_style="green", box=box.ROUNDED))


def print_assistant_message(msg: str):
    console.print(Panel(f"[cyan]{msg}[/cyan]", title="Assistant", border_style="cyan", box=box.ROUNDED))


def print_history(messages: list[dict]):
    if not messages:
        console.print("[yellow]No conversation history yet.[/yellow]")
        return
    console.print("\n[bold underline]Conversation History[/bold underline]\n")
    for m in messages:
        role = "You" if m["role"] == "user" else "Assistant"
        style = "green" if m["role"] == "user" else "cyan"
        console.print(Panel(f"[{style}]{m['content']}[/{style}]", title=role, border_style=style, box=box.ROUNDED))
    console.print()


async def main():
    console.print(WELCOME)
    try:
        async with WeatherAgent() as agent:
            while True:
                user_input = Prompt.ask("[bold green]You[/bold green]").strip()
                if not user_input:
                    continue
                if user_input.startswith("/"):
                    cmd = user_input.lower()
                    if cmd == "/quit":
                        console.print("[bold red]Goodbye![/bold red]")
                        break
                    elif cmd == "/clear":
                        agent.memory.clear_session(SESSION_ID)
                        console.print("[yellow]Conversation cleared.[/yellow]")
                        continue
                    elif cmd == "/history":
                        history = agent.memory.get_history(SESSION_ID)
                        print_history(history)
                        continue
                    else:
                        console.print(f"[red]Unknown command: {user_input}[/red]")
                        continue
                print_user_message(user_input)
                with console.status("[bold yellow]Thinking...", spinner="dots"):
                    response = await agent.chat(SESSION_ID, user_input)
                print_assistant_message(response)
    except KeyboardInterrupt:
        console.print("\n[bold red]Goodbye![/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")


if __name__ == "__main__":
    asyncio.run(main())
