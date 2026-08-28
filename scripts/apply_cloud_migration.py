"""Apply one reviewed SQL migration without exposing the database secret.

The connection string is read from Google Secret Manager directly into this
process. It is never accepted as a command-line argument, written to disk, or
printed. The migration and its audit record commit in one transaction.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess

import psycopg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--secret", default="revenavi-database-url")
    parser.add_argument("--migration", required=True, type=pathlib.Path)
    parser.add_argument("--gcloud", required=True)
    args = parser.parse_args()

    migration_path = args.migration.resolve()
    migration_id = migration_path.stem
    sql = migration_path.read_text(encoding="utf-8")
    if not sql.strip():
        raise SystemExit("Migration is empty.")

    database_url = subprocess.check_output(
        [
            args.gcloud,
            "secrets", "versions", "access", "latest",
            f"--secret={args.secret}", f"--project={args.project}",
        ],
        text=True,
    ).strip()
    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise SystemExit("Secret does not contain a PostgreSQL connection string.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select pg_advisory_xact_lock(hashtext(%s))", ("revenavi-schema-migrations",))
            cursor.execute(
                """
                create table if not exists public.revenavi_schema_migrations (
                  migration_id text primary key,
                  applied_at timestamptz not null default now()
                )
                """
            )
            cursor.execute(
                "select 1 from public.revenavi_schema_migrations where migration_id = %s",
                (migration_id,),
            )
            if cursor.fetchone():
                print(f"Already applied: {migration_id}")
                return
            cursor.execute(sql)
            cursor.execute(
                "insert into public.revenavi_schema_migrations (migration_id) values (%s)",
                (migration_id,),
            )
        connection.commit()
    print(f"Applied: {migration_id}")


if __name__ == "__main__":
    main()
