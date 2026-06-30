"""
Clean Wikipedia revision history for bulk insert.

This module reads the raw CSV file with UTF-8 BOM handling, preserves the header,
and writes a cleaned CSV with normalized CRLF line endings suitable for BULK INSERT.
"""

import argparse
import csv
import logging
from pathlib import Path
from typing import List

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
BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PARSE_DIR = BASE_DIR / "data" / "parsed"
DEFAULT_INPUT_FILE = RAW_DIR / "wikipedia_revision_history.csv"
DEFAULT_OUTPUT_FILE = PARSE_DIR / "wikipedia_revision_history_clean.csv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean wikipedia_revision_history.csv and write a normalized CSV output."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help="Path to the raw wikipedia revision history CSV file.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help="Path to the cleaned CSV file to write.",
    )
    return parser.parse_args()


def read_csv(input_file: Path) -> List[List[str]]:
    if not input_file.exists():
        log.error("Input file not found: %s", input_file)
        raise FileNotFoundError(input_file)

    with input_file.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    log.info("Loaded %d rows from %s", len(rows), input_file)
    return rows


def write_csv(rows: List[List[str]], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerows(rows)

    log.info("Clean file written to: %s", output_file)


def clean_wikipedia_revision_history(input_file: Path, output_file: Path) -> None:
    rows = read_csv(input_file)

    if len(rows) < 2:
        log.warning("Input file contains %d row(s); expected a header and at least one data row.", len(rows))

    if len(rows) >= 2:
        log.info("Header: %s", rows[0])
        log.info("Sample row: %s", rows[1])

    write_csv(rows, output_file)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    if args.output_file.exists():
        log.info("Output already exists, skipping: %s", args.output_file)
        return

    clean_wikipedia_revision_history(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
