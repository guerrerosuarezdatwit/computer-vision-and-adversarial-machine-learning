"""Create a versioned Rerun recording from canonical artifacts, without running SfM."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rerun_reconstruction import export_recording, load_reconstruction, validate_recording


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=ROOT / "results/canonical_reconstruction/v1")
    parser.add_argument("--output", type=Path, default=ROOT / "results/rerun_reconstruction/v1")
    parser.add_argument("--validate-only", type=Path, help="Read back an existing .rrd; do not write outputs.")
    args = parser.parse_args()
    if args.validate_only:
        print(json.dumps(validate_recording(args.validate_only, load_reconstruction(args.canonical, ROOT)), indent=2))
    else:
        if args.output.exists():
            parser.error("Output already exists; choose a fresh version directory.")
        print(json.dumps(export_recording(args.canonical, ROOT, args.output), indent=2))


if __name__ == "__main__":
    main()
