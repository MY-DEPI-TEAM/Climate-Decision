"""Project entry point.

Runs the ingestion orchestrator first, then executes the SQL script that
builds the database objects.
"""

from src.database.db_loader import run_db_script
from src.ingestion.orchestrator import main as run_orchestrator


def main() -> None:
	"""Run the full pipeline in order."""
	run_orchestrator()
	run_db_script()


if __name__ == "__main__":
	main()
