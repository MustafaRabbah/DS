#!/usr/bin/env python3
"""Generate arabic-overrides.json from mcqs.json using Google Translate (via deep-translator)."""
import json
import sys
import time
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Install deep-translator in a venv: python3 -m venv .venv && .venv/bin/pip install deep-translator", file=sys.stderr)
    sys.exit(1)


def main():
    root = Path(__file__).resolve().parent
    mcqs_path = root / "mcqs.json"
    out_path = root / "arabic-overrides.json"
    if not mcqs_path.is_file():
        print(f"Run build_mcqs.py first. Missing {mcqs_path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(mcqs_path.read_text(encoding="utf-8"))
    questions = data.get("questions") or []
    t = GoogleTranslator(source="en", target="ar")
    ar_map: dict[str, dict] = {}
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.35

    def tr(text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        out = t.translate(text)
        time.sleep(delay)
        return out

    total = len(questions)
    for i, q in enumerate(questions, 1):
        qid = str(q["id"])
        print(f"Translating {i}/{total} (id={qid})...", flush=True)
        entry: dict = {
            "question_ar": tr(q["question"]),
        }
        opts_ar = {}
        for opt in q["options"]:
            letter = opt["letter"]
            opts_ar[letter] = tr(opt["text"])
        entry["options_ar"] = opts_ar
        entry["correct_text_ar"] = tr(q["correct_text"])
        entry["explanation_ar"] = tr(q["explanation"])
        ar_map[qid] = entry

    out_path.write_text(json.dumps(ar_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
