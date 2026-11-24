"""Pin Databricks notebooks (.ipynb) to a serverless environment version.

Notebooks without an explicit version run on serverless environment v1 (Python 3.10),
where `%pip install mlflow==3.12.0` can backtrack for 25+ minutes. This writes
`environmentMetadata.environment_version` into each notebook's Databricks metadata.

Usage:
    python scripts/set_serverless_env.py week1            # pin to version 5
    python scripts/set_serverless_env.py week1 --version 4
"""

import argparse
import json
from pathlib import Path

DATABRICKS_KEY = "application/vnd.databricks.v1+notebook"


def pin(path: Path, version: str) -> bool:
    nb = json.loads(path.read_text(encoding="utf-8"))
    meta = nb.setdefault("metadata", {}).setdefault(DATABRICKS_KEY, {})
    env = meta.get("environmentMetadata") or {}
    if env.get("environment_version") == version:
        return False
    meta["environmentMetadata"] = {"base_environment": "", "environment_version": version}
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="Folder to scan recursively for .ipynb files")
    parser.add_argument("--version", default="5", help="Serverless environment version (default: 5)")
    args = parser.parse_args()

    for path in sorted(args.folder.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in path.parts:
            continue
        print(f"{'updated' if pin(path, args.version) else 'ok     '}  {path}")


if __name__ == "__main__":
    main()
