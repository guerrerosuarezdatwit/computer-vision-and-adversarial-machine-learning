"""Export or validate a versioned linked-inspection RRD without running SfM."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rerun_inspection import export_inspection, validate_inspection
from src.rerun_reconstruction import load_reconstruction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=ROOT / "results/canonical_reconstruction/v1")
    parser.add_argument("--output", type=Path, default=ROOT / "results/rerun_reconstruction/v2")
    parser.add_argument("--validate-only", type=Path)
    args = parser.parse_args()
    if args.validate_only:
        result = validate_inspection(args.validate_only, load_reconstruction(args.canonical, ROOT))
    else:
        if args.output.exists():
            parser.error("Output already exists; choose a fresh version directory.")
        result = export_inspection(args.canonical, ROOT, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
