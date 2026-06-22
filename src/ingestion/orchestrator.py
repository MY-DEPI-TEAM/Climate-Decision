"""
Main entry point for the Egypt Weather Data Pipeline
=====================================================

Orchestrates data collection in one workflow.

Usage:
    python main.py
    python main.py --skip-collection  # Skip API calls if data already exists
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(r"D:\VS_code\VS_code_WorkSpace\python_projects\Climate-Decision")
RAW_DIR = BASE_DIR / "data" / "raw"
SCRIPTS_DIR = BASE_DIR / "src" / "ingestion"

COLLECTOR_SCRIPTS = [
    SCRIPTS_DIR / "weather_data_collector.py",
    SCRIPTS_DIR / "weather_wikipedia_data.py",
    SCRIPTS_DIR / "weather_wikipedia_scrapping.py",
    SCRIPTS_DIR / "wunderground.py",
]

RAW_DATA_CSV = [
    RAW_DIR / "Egypt_Weather_2022_2025_Final.csv",
    RAW_DIR / "wikipedia_revision_history.csv",
    RAW_DIR / "scraped_climate_insights.csv",
    RAW_DIR / "egypt_governorates_weather.csv"
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_script(script_path: Path, *args: str) -> int:
    """Run a Python script and return its exit code."""
    cmd = [sys.executable, str(script_path), *args]
    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=BASE_DIR)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Egypt Weather Data Pipeline")
    parser.add_argument(
        "--skip-collection",
        action="store_true",
        help="Skip data collection (assume raw data already exists)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    
    all_files_exist = all(csv_file.exists() for csv_file in RAW_DATA_CSV)

    # If the files already exist and skipping or normal execution was requested
    if all_files_exist:
        log.info("Raw data already exists: %s", RAW_DATA_CSV)
        log.info("=" * 50)
        log.info("Pipeline complete!")
        log.info("=" * 50)
        return

    # If skipping was requested but the files do not actually exist
    if args.skip_collection and not all_files_exist:
        log.error("Raw data not found. Cannot skip collection.")
        sys.exit(1)
        
    # Data collection stage
    log.info("=" * 50)
    log.info("STAGE 1: Collecting weather data")
    log.info("=" * 50)

    for script_path in COLLECTOR_SCRIPTS:
        exit_code = run_script(script_path)
        if exit_code != 0:
            log.error("Data collection failed for %s with exit code %d", script_path.name, exit_code)
            sys.exit(exit_code)

    if not all(csv_file.exists() for csv_file in RAW_DATA_CSV):
        log.error("Data collection completed but some output files are missing: %s", RAW_DATA_CSV)
        sys.exit(1)

    # --- Done ---
    log.info("=" * 50)
    log.info("Pipeline complete!")
    log.info("  Raw data    : %s", RAW_DIR)
    log.info("=" * 50)


if __name__ == "__main__":
    main()