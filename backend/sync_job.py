"""Cloud Run Job entry point for reliable, single-run OTA collection."""

import argparse

from scheduler import scheduled_scraping_job


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("refresh", "future"), default="refresh")
    args = parser.parse_args()
    # Cloud Run Jobs must fail visibly when any facility fails. Otherwise the
    # platform reports a green execution even though no market data arrived.
    scheduled_scraping_job(mode=args.mode, raise_on_failure=True)


if __name__ == "__main__":
    main()
