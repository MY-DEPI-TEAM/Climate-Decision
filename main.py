"""Project entry point.

Runs the ingestion orchestrator first, then executes the SQL script that
builds the database objects.
"""

from src.database.db_loader import run_db_script
from src.ingestion.orchestrator import main as run_orchestrator
from src.transformation.wiki_transformer import main as clean_wikipedia_revision_history
from warehouse.gold.ml import get_ml_ready_df


def main() -> None:
	"""Run the full pipeline in order."""
	run_orchestrator()
	clean_wikipedia_revision_history()
	run_db_script()
	get_ml_ready_df()


if __name__ == "__main__":
	main()
