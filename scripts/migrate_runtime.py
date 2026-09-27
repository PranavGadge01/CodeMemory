"""Copy and verify an existing installation without deleting its original data."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb
from codememory.core.runtime import app_directory, migrate_runtime
from codememory.storage.duckdb_repository import DuckDBStorage


def fingerprint(database, columns=None):
    connection = duckdb.connect(str(database), read_only=True)
    result, selected = {}, {}
    try:
        for table in ("problems", "attempts", "submissions", "notes"):
            fields = columns[table] if columns else [r[0] for r in connection.execute(f"DESCRIBE {table}").fetchall()]
            selected[table] = fields
            names = ",".join('"' + field + '"' for field in fields)
            rows = connection.execute(f"SELECT {names} FROM {table} ORDER BY id").fetchall()
            result[table] = {"rows": len(rows), "sha256": hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()}
    finally:
        connection.close()
    return result, selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Legacy folder containing data/ and knowledge/")
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    target = args.target or app_directory()
    before, columns = fingerprint(args.source / "data/codememory.duckdb")
    if args.check_only:
        print(json.dumps({"source": str(args.source), "target": str(target), "tables": before}, indent=2))
        return
    copied = migrate_runtime(args.source, target)
    store = DuckDBStorage(target / "codememory.duckdb", shared=False)
    store.close()
    after, _ = fingerprint(target / "codememory.duckdb", columns)
    report = {"copy_status": copied["status"], "source": str(args.source), "target": str(target),
              "before": before, "after": after, "historical_rows_unchanged": before == after}
    (target / "ownership-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if before != after:
        raise RuntimeError("Historical fingerprints differ. Keep using the original data and inspect the migration report.")


if __name__ == "__main__":
    main()
