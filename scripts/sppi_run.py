"""Collect SPPI H & J prices from the sources in config/sppi_sources.json.

    python scripts/sppi_run.py                      # all sources, today's date
    python scripts/sppi_run.py --only rta_nol,j1 --out /tmp/try   # page ids or company serials
    python scripts/sppi_run.py --date 2026-10-29

Writes data/sppi/runs/<date>/: products_availability.csv, prices.csv, pages.csv, fetch_log.csv,
price_mentions.csv, SPPI_HJ_prices_<date>.xlsx and snapshots/ (every fetched page, PDF, JSON and image, gzipped).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sppi.run import run  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--date", help="run date YYYY-MM-DD (also the folder name), default today")
    ap.add_argument("--out", help="parent folder for the run, default data/sppi/runs")
    args = ap.parse_args()
    run_dir = run(args.date, args.only.split(",") if args.only else None, Path(args.out) if args.out else None)
    print(f"\nwritten to {run_dir}")


if __name__ == "__main__":
    main()
