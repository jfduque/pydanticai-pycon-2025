import argparse
import sqlite3
import os
from rich.console import Console
from rich.table import Table
from rich import box


def fetch_requests(db_path: str, table: str = "requests"):
    """Fetch id, request_body, summary, and response from the table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Only select the columns we want
    cur.execute(f"""
        SELECT
            id,
            request_body,
            summary,
            response
        FROM {table}
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def render_table(rows):
    """Render a list of sqlite3.Row objects as a Rich Table."""
    console = Console()
    if not rows:
        console.print("[bold yellow]No rows found.[/]")
        return

    table = Table(box=box.MINIMAL_DOUBLE_HEAD, highlight=True, show_lines=True)
    # Use only the selected columns
    for column in rows[0].keys():
        table.add_column(column, overflow="fold", no_wrap=False)

    for row in rows:
        table.add_row(*(str(row[col]) for col in row.keys()))

    console.print(table)


def main():
    parser = argparse.ArgumentParser(
        description="Display selected columns of a SQLite table in a pretty terminal table."
    )
    parser.add_argument(
        "db",
        nargs="?",
        default=os.path.join(os.path.dirname(__file__), "requests.db"),
        help="Path to the SQLite database file (default: requests.db)",
    )
    parser.add_argument(
        "-t",
        "--table",
        default="requests",
        help="Name of the table to display (default: requests)",
    )
    args = parser.parse_args()

    rows = fetch_requests(args.db, args.table)
    render_table(rows)


if __name__ == "__main__":
    main()
