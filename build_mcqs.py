#!/usr/bin/env python3
"""Parse MCQ text file and emit mcqs.json for static GitHub Pages."""
import json
import re
import sys
from pathlib import Path

HEADER_PATTERNS = (
    "Database Security — Practical MCQ Examination",
    "Database Security MCQ Bank",
)


def strip_headers(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        if any(p in line for p in HEADER_PATTERNS):
            continue
        lines.append(line)
    return "\n".join(lines)


def split_answer_and_explanation(body: str) -> tuple[str | None, str | None, str | None]:
    """Handle ANSWER lines split across lines (e.g. '... quantum computing' / 'matures')."""
    lines = body.splitlines()
    ans_i = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("ANSWER "):
            ans_i = i
            break
    if ans_i is None:
        return None, None, None
    m = re.match(r"^ANSWER\s+([A-D])\.\s*(.*)$", lines[ans_i].strip())
    if not m:
        return None, None, None
    letter = m.group(1)
    parts = [m.group(2).strip()]
    j = ans_i + 1
    while j < len(lines):
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if s[0].islower():
            parts.append(s)
            j += 1
            continue
        break
    correct_text = " ".join(parts)
    expl_parts: list[str] = []
    while j < len(lines):
        t = lines[j].strip()
        if t:
            expl_parts.append(t)
        j += 1
    explanation = " ".join(expl_parts)
    return letter, correct_text, explanation


def merge_arabic(mcqs: list[dict], root: Path) -> list[dict]:
    path = root / "arabic-overrides.json"
    if not path.is_file():
        return mcqs
    ar_map = json.loads(path.read_text(encoding="utf-8"))
    for q in mcqs:
        key = str(q["id"])
        if key not in ar_map:
            continue
        ar = ar_map[key]
        if ar.get("question_ar"):
            q["question_ar"] = ar["question_ar"].lstrip("- ").strip()
        opts_ar = ar.get("options_ar") or {}
        for opt in q["options"]:
            lt = opt["letter"]
            if lt in opts_ar:
                opt["text_ar"] = opts_ar[lt].lstrip("- ").strip()
        if ar.get("correct_text_ar"):
            q["correct_text_ar"] = ar["correct_text_ar"].lstrip("- ").strip()
        if ar.get("explanation_ar"):
            q["explanation_ar"] = ar["explanation_ar"]
        if ar.get("explanation_ar"):
            q["explanation_ar"] = ar["explanation_ar"]
    return mcqs


def parse_mcqs(text: str) -> list[dict]:
    text = strip_headers(text.strip())
    # One block per question: Q<id> <category>\n ... until next Q<id> or EOF
    pattern = re.compile(
        r"^Q(\d+)\s+([^\n]+)\n(.*?)(?=^Q\d+\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    out = []
    for m in pattern.finditer(text):
        qid, category, body = m.group(1), m.group(2).strip(), m.group(3).strip()
        opt_lines = re.findall(r"^([A-D])\.\s*(.+)$", body, re.MULTILINE)
        if len(opt_lines) < 4:
            continue
        options = {k: v.strip() for k, v in opt_lines[:4]}
        letter, answer_text, explanation = split_answer_and_explanation(body)
        if letter is None:
            continue
        explanation = re.sub(r"\s+", " ", explanation)
        # Question text: everything before first option line
        first_opt = re.search(r"^[A-D]\.\s", body, re.MULTILINE)
        q_text = body[: first_opt.start()].strip() if first_opt else ""
        q_text = re.sub(r"\s+", " ", q_text)
        item = {
            "id": int(qid),
            "category": category,
            "question": q_text,
            "options": [{"letter": L, "text": options[L]} for L in "ABCD"],
            "correct_letter": letter,
            "correct_text": answer_text,
            "explanation": explanation,
        }
        out.append(item)
    out.sort(key=lambda x: x["id"])
    return out


def main():
    root = Path(__file__).resolve().parent
    src = root / "Text File.txt"
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    if not src.is_file():
        print(f"Missing source file: {src}", file=sys.stderr)
        sys.exit(1)
    raw = src.read_text(encoding="utf-8", errors="replace")
    mcqs = merge_arabic(parse_mcqs(raw), root)
    out_path = root / "mcqs.json"
    out_path.write_text(
        json.dumps({"title": "Database Security MCQ Bank", "questions": mcqs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(mcqs)} questions to {out_path}")


if __name__ == "__main__":
    main()
