"""Validate that project, manifest, and optional tag versions agree."""

from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "custom_components" / "kapso_whatsapp" / "manifest.json"


def main() -> None:
    """Check the version sources and exit with an error on a mismatch."""
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", nargs="?", help="Optional release tag such as v0.1.0")
    args = parser.parse_args()

    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"][
        "version"
    ]
    manifest_version = json.loads(MANIFEST.read_text())["version"]

    if project_version != manifest_version:
        raise SystemExit(
            "Version mismatch: "
            f"pyproject={project_version}, manifest={manifest_version}"
        )

    if args.tag is not None:
        tag_version = args.tag.removeprefix("v")
        if tag_version != manifest_version:
            raise SystemExit(
                f"Tag mismatch: tag={tag_version}, manifest={manifest_version}"
            )

    print(f"Version {manifest_version} is consistent")


if __name__ == "__main__":
    main()
