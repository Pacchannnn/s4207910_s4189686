"""Fingerprint original tables and verify the project copy without changing either."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ("Antigen", "Country", "CountryPopulation", "Economy", "InfectionData",
          "Infection_Type", "Region", "Vaccination", "YearDate")


def fingerprint(path):
    result = {}
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for table in TABLES:
            rows = db.execute(f'SELECT * FROM "{table}"').fetchall()
            encoded = sorted(json.dumps(row, ensure_ascii=True, separators=(",", ":")) for row in rows)
            result[table] = {"rows": len(rows),
                            "sha256": hashlib.sha256("\n".join(encoded).encode()).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    tables = fingerprint(args.source)
    if tables != fingerprint(ROOT / "database/immunisation.db"):
        raise SystemExit("ERROR: source table contents differ")
    report = {"source_file_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
              "tables": tables}
    manifest = ROOT / "docs/source_manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != report:
        raise SystemExit("ERROR: existing source manifest differs; it was not overwritten")
    manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("All 9 source-table content hashes match the original database.")


if __name__ == "__main__":
    main()
