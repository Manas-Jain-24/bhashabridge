"""Run a real IndicTrans2 translation and check target-script routing."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

if __name__ == "__main__":
    from app.core.languages import LANGUAGES, has_native
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=list(LANGUAGES))
    parser.add_argument("--target", required=True, choices=list(LANGUAGES))
    parser.add_argument("--text", required=True)
    parser.add_argument("--offline", action="store_true", help="Use already cached weights only")
    args = parser.parse_args()
    if args.source == args.target:
        parser.error("Choose distinct languages")
    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from app.services.translation.indictrans2 import IndicTrans2Adapter
    result = IndicTrans2Adapter().translate(args.text, args.source, args.target, "native")
    if result["engine"] != "indictrans2-320m-neural" or not has_native(result["translation_native"], args.target):
        raise SystemExit("Neural smoke check failed: fallback or missing target script")
    print(json.dumps(result, ensure_ascii=True, indent=2))
