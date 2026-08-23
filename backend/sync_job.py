"""Cloud Run Job entry point for reliable, single-run OTA collection."""

import argparse

from scheduler import scheduled_scraping_job


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("refresh", "future"), default="refresh")
    args = parser.parse_args()
    scheduled_scraping_job(mode=args.mode)


if __name__ == "__main__":
    main()
