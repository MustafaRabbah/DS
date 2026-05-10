#!/usr/bin/env python3
"""Generate arabic-overrides-final.json from final_mcqs.json (Google Translate via deep-translator)."""
import json
import sys
import time
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print(
        "Install deep-translator: python3 -m venv .venv && .venv/bin/pip install deep-translator",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    root = Path(__file__).resolve().parent
    mcqs_path = root / "final_mcqs.json"
    out_path = root / "arabic-overrides-final.json"
    if not mcqs_path.is_file():
        print(f"Run build_final_bank.py first. Missing {mcqs_path}", file=sys.stderr)
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
        if q.get("type") == "true_false":
            ar_map[qid] = {"statement_ar": tr(q.get("statement") or "")}
            continue
        entry: dict = {"question_ar": tr(q.get("question") or "")}
        opts_ar = {}
        for opt in q.get("options") or []:
            letter = opt["letter"]
            opts_ar[letter] = tr(opt.get("text") or "")
        entry["options_ar"] = opts_ar
        if q.get("correct_text"):
            entry["correct_text_ar"] = tr(q["correct_text"])
        if q.get("explanation"):
            entry["explanation_ar"] = tr(q["explanation"])
        ar_map[qid] = entry

    out_path.write_text(json.dumps(ar_map, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
