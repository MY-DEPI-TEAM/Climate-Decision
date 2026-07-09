"""Project entry point.

Runs the ingestion orchestrator first, then executes the SQL script that
builds the database objects.
"""

from src.ingestion.orchestrator import main as run_orchestrator
from src.transformation.wiki_transformer import clean_wikipedia_revision_history
from src.database.run_azure_data import run_azure_data_pipeline
from lakehouse.gold.fact_weather import get_fact_weather
from lakehouse.gold.ml import get_ml_ready_df
from ml.prediction import get_prediction_df


def main() -> None:
	"""Run the full pipeline in order."""
	run_orchestrator()
	clean_wikipedia_revision_history()
	run_azure_data_pipeline()
	get_fact_weather()
	get_ml_ready_df()
	get_prediction_df()


if __name__ == "__main__":
	main()