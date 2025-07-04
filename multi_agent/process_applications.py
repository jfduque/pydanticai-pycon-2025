import argparse
import asyncio
import random
import sqlite3
from dataclasses import dataclass
from typing import Literal
import os

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

from pydantic_ai import Agent, RunContext

# Initialize Rich console
console = Console()


# Define Pydantic models for data structures
class CreditApplication(BaseModel):
    id: int
    full_name: str
    date_of_birth: str
    address: str
    ssn: str
    income: float
    expenses: float
    credit_score: int


class FeasibilityResult(BaseModel):
    decision: Literal["Approved", "Denied"]
    reason: str


# --- Dependencies ---
class Database:
    @staticmethod
    def get_application_by_id(db_path: str, app_id: int) -> CreditApplication:
        """Connects to the database and retrieves a credit application."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return CreditApplication(
                id=row[0],
                full_name=row[1],
                date_of_birth=row[2],
                address=row[3],
                ssn=row[4],
                income=row[5],
                expenses=row[6],
                credit_score=row[7],
            )
        raise ValueError("Application not found")


@dataclass
class AppContext:
    credit_application: CreditApplication


# --- Specialized Agents ---
data_validator = Agent(
    "anthropic:claude-sonnet-4-0",
    output_type=bool,
    system_prompt="Evaluate if the applicant's data is complete. Return true or false.",
)

financial_evaluator = Agent(
    "anthropic:claude-sonnet-4-0",
    output_type=bool,
    system_prompt="Assess the applicant's financial capacity. If income is at least twice the expenses and credit score is above 650, return true. Otherwise, return false.",
)

background_checker = Agent(
    "anthropic:claude-sonnet-4-0",
    output_type=bool,
    system_prompt="Perform a background check. For this demo, assume everyone passes unless their name contains 'fraud'. Return true for a pass, false otherwise.",
)

# --- Coordinator Agent ---
coordinator = Agent[AppContext, FeasibilityResult](
    "anthropic:claude-sonnet-4-0",
    output_type=FeasibilityResult,
    deps_type=AppContext,
    system_prompt="You are a credit coordinator. Use the provided tools to evaluate the credit application and make a final decision.",
    end_strategy="exhaustive",
)


@coordinator.tool
async def validate_data(ctx: RunContext[AppContext]) -> bool:
    """Check if the applicant's data is complete."""
    result = await data_validator.run(ctx.deps.credit_application.model_dump_json())
    console.print(f"[bold blue]Data validation agent veredict:[/] {result.output}")
    return result.output


@coordinator.tool
async def evaluate_financials(ctx: RunContext[AppContext]) -> bool:
    """Evaluate the applicant's financial capacity."""
    result = await financial_evaluator.run(
        ctx.deps.credit_application.model_dump_json()
    )

    console.print(f"[bold blue]Financial evaluation agent veredict:[/] {result.output}")
    return result.output


@coordinator.tool
async def check_background(ctx: RunContext[AppContext]) -> bool:
    """Perform a background check on the applicant."""
    result = await background_checker.run(ctx.deps.credit_application.full_name)
    console.print(f"[bold blue]Background check agent veredict:[/] {result.output}")
    return result.output


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process credit applications")
    parser.add_argument(
        "--app-id",
        type=int,
        help="Force a specific application ID instead of random selection",
    )
    args = parser.parse_args()

    # --- Database Setup ---
    db_path = os.path.join(os.path.dirname(__file__), "credit_applications.db")

    # --- Run Credit Feasibility ---
    if args.app_id:
        application_id = args.app_id
        console.print(f"Using specified application ID: {application_id}")
    else:
        application_id = random.randint(1, 10)
        console.print(f"Randomly selected application ID: {application_id}")

    try:
        application = Database.get_application_by_id(db_path, application_id)
        console.print(
            f"Evaluating application for: [bold cyan]{application.full_name}[/]"
        )

        app_context = AppContext(credit_application=application)
        result = await coordinator.run(
            f"Evaluate credit application {application.id}", deps=app_context
        )

        decision_color = "green" if result.output.decision == "Approved" else "red"
        panel_content = f"[bold]Decision:[/] [{decision_color}]{result.output.decision}[/{decision_color}]\n[bold]Reason:[/] {result.output.reason}"
        console.print(
            Panel(
                panel_content,
                title="Credit Feasibility Result",
                expand=False,
                border_style="bold magenta",
            )
        )

    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")


if __name__ == "__main__":
    asyncio.run(main())
