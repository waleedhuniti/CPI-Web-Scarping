"""Collect SPPI H & J prices from the sources in config/sppi_sources.json.

    python scripts/sppi_run.py                      # all sources, today's date
    python scripts/sppi_run.py --only rta_nol,ups_tariff
    python scripts/sppi_run.py --date 2026-10-29    # name of the run folder

Writes data/sppi/runs/<date>/: prices.csv, price_mentions.csv, sources.csv, fetch_log.csv,
SPPI_HJ_prices_<date>.xlsx and snapshots/ (every fetched page, PDF, JSON and image, gzipped).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sppi.run import run  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--date", help="run date (folder name), default today")
    args = ap.parse_args()
    run_dir = run(args.date, args.only.split(",") if args.only else None)
    print(f"\nwritten to {run_dir}")


if __name__ == "__main__":
    main()
