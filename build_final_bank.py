#!/usr/bin/env python3
"""Parse final.txt (MCQ + True/False) and emit final_mcqs.json."""
import json
import re
import sys
from pathlib import Path

SECTION_TF = "Section 2: True / False Questions"
HEADER_LINE = "Database Security — Question Bank"
PAGE_RE = re.compile(r"^Page\s+\d+\s+of\s+\d+\s*$")


def strip_mcq_noise(s: str) -> str:
    lines = []
    for line in s.splitlines():
        t = line.strip()
        if HEADER_LINE in line:
            continue
        if PAGE_RE.match(t):
            continue
        lines.append(line)
    return "\n".join(lines)


def merge_arabic(items: list[dict], root: Path) -> list[dict]:
    path = root / "arabic-overrides-final.json"
    if not path.is_file():
        return items
    ar_map = json.loads(path.read_text(encoding="utf-8"))
    for q in items:
        key = str(q["id"])
        if key not in ar_map:
            continue
        ar = ar_map[key]
        if q["type"] == "mcq":
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
        else:
            if ar.get("statement_ar"):
                q["statement_ar"] = ar["statement_ar"].lstrip("- ").strip()
    return items


def parse_mcq_part(text: str) -> list[dict]:
    text = strip_mcq_noise(text).strip()
    if SECTION_TF in text:
        text = text.split(SECTION_TF, 1)[0]
    pattern = re.compile(
        r"^Q(\d+)\.\s*(.*?)(?=^Q\d+\.|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    out: list[dict] = []
    for m in pattern.finditer(text):
        qid = m.group(1)
        body = m.group(2).strip()
        opt_re = re.compile(r"^([A-D])\)\s*(.+)$", re.MULTILINE)
        opts: list[tuple[str, str, bool]] = []
        for om in opt_re.finditer(body):
            letter, raw = om.group(1), om.group(2).strip()
            mark = "✓" in raw or "\u2713" in raw
            text_clean = raw.replace("✓", "").replace("\u2713", "").strip()
            opts.append((letter, text_clean, mark))
        correct = next((L for L, _, mk in opts if mk), None)
        if correct is None or len(opts) < 4:
            continue
        first_opt = opt_re.search(body)
        q_text = body[: first_opt.start()].strip() if first_opt else ""
        q_text = re.sub(r"\s+", " ", q_text)
        cor_opt = next(((L, t) for L, t, mk in opts if mk), None)
        correct_text = cor_opt[1] if cor_opt else ""
        item = {
            "id": f"m{qid}",
            "type": "mcq",
            "category": "Multiple Choice",
            "question": q_text,
            "options": [{"letter": L, "text": t} for L, t, _ in sorted(opts, key=lambda x: x[0])],
            "correct_letter": correct,
            "correct_text": correct_text,
            "explanation": "",
        }
        out.append(item)
    out.sort(key=lambda x: int(x["id"][1:]))
    return out


def parse_tf_part(raw_full: str) -> list[dict]:
    idx = raw_full.find(SECTION_TF)
    if idx < 0:
        return []
    sub = raw_full[idx + len(SECTION_TF) :]
    lines = sub.splitlines()
    out: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        t = line.strip()
        if (
            not t
            or t.startswith("#")
            or "Statement Answer" in t
            or "Total Questions" in t
            or HEADER_LINE in line
            or PAGE_RE.match(t)
        ):
            i += 1
            continue
        m = re.match(r"^(\d+)\s+(.*)$", t)
        if not m:
            i += 1
            continue
        num = m.group(1)
        rest = m.group(2).strip()
        verdict: bool | None = None
        statement: str

        end_m = re.search(r"\s+(True|False)\s*$", rest)
        if end_m and end_m.start() > 0:
            statement = rest[: end_m.start()].strip()
            verdict = end_m.group(1) == "True"
            i += 1
        else:
            parts = [rest]
            i += 1
            while i < len(lines):
                u = lines[i].strip()
                if HEADER_LINE in lines[i] or PAGE_RE.match(u):
                    i += 1
                    continue
                if u in ("True", "False"):
                    verdict = u == "True"
                    i += 1
                    break
                parts.append(lines[i].strip())
                i += 1
            statement = re.sub(r"\s+", " ", " ".join(parts)).strip()

        if verdict is None:
            continue
        out.append(
            {
                "id": f"t{num}",
                "type": "true_false",
                "category": "True / False",
                "statement": statement,
                "correct_bool": verdict,
            }
        )
    return out


def main():
    root = Path(__file__).resolve().parent
    src = root / "final.txt"
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    if not src.is_file():
        print(f"Missing source file: {src}", file=sys.stderr)
        sys.exit(1)
    raw = src.read_text(encoding="utf-8", errors="replace")
    mcqs = parse_mcq_part(raw)
    tfs = parse_tf_part(raw)
    items = mcqs + tfs
    items = merge_arabic(items, root)

    out_path = root / "final_mcqs.json"
    payload = {
        "title": "Database Security — Final Question Bank",
        "questions": items,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {len(items)} items ({len(mcqs)} MCQ, {len(tfs)} T/F) to {out_path}",
    )


if __name__ == "__main__":
    main()
