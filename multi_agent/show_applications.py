import sqlite3
from rich.console import Console
from rich.table import Table
from rich import box


def fetch_applications():
    """Fetch id, full_name, date_of_birth, address, ssn, income, expenses, and credit_score."""
    conn = sqlite3.connect("credit_applications.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            full_name,
            date_of_birth,
            address,
            ssn,
            income,
            expenses,
            credit_score
        FROM applications
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def render_table(rows):
    """Render a list of sqlite3.Row objects as a Rich Table."""
    console = Console()
    if not rows:
        console.print("[bold yellow]No applications found.[/]")
        return

    table = Table(box=box.MINIMAL_DOUBLE_HEAD, highlight=True, show_lines=True)
    for column in rows[0].keys():
        table.add_column(column, overflow="fold", no_wrap=False)

    for row in rows:
        table.add_row(*(str(row[col]) for col in row.keys()))

    console.print(table)


def main():
    rows = fetch_applications()
    render_table(rows)


if __name__ == "__main__":
    rows = fetch_applications()
    render_table(rows)
