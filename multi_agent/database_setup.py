import sqlite3
from faker import Faker


def setup_database(num_applicants=10):
    """Creates and populates the SQLite database with more realistic mock data."""
    conn = sqlite3.connect("credit_applications.db")
    cursor = conn.cursor()
    fake = Faker()

    # Create table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY,
        full_name TEXT,
        date_of_birth TEXT,
        address TEXT,
        ssn TEXT,
        income REAL,
        expenses REAL,
        credit_score INTEGER
    )
    """
    )

    # Clear existing data
    cursor.execute("DELETE FROM applications")

    # Insert mock data
    applicants = []
    for i in range(1, num_applicants + 1):
        applicant = (
            i,
            fake.name(),
            fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            fake.address(),
            fake.ssn(),
            fake.random_int(min=25000, max=150000),  # Random income
            fake.random_int(min=15000, max=80000),  # Random expenses
            fake.random_int(min=300, max=850),  # Random credit score
        )
        applicants.append(applicant)

    cursor.executemany(
        "INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?, ?)", applicants
    )

    conn.commit()
    conn.close()
    print(
        f"Database 'credit_applications.db' created and populated successfully with {num_applicants} applicants."
    )


if __name__ == "__main__":
    setup_database()
