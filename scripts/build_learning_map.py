#!/usr/bin/env python3
"""Extract structured course data from program documents (培养方案).

Reads .docx/.pdf program files and extracts course tables into a
structured JSON database.  Enables answering counting/aggregation
queries like "几门数学课" that chunk-based RAG cannot handle.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COURSE_CODE_RE = re.compile(r"(\d{8})")
CREDIT_NUM_RE = re.compile(r"^(\d+\.?\d*)$")


def extract_from_docx(path: Path) -> list[dict]:
    """Extract course data from a .docx program document."""
    from docx import Document

    doc = Document(str(path))
    courses: list[dict] = []
    current_category = ""
    current_subcategory = ""

    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if not cells or all(not c for c in cells):
                continue

            joined = " ".join(cells)

            # Skip header rows
            if any(h in joined for h in ["课程代码", "课程名称", "课程编码"]) and "学分" in joined:
                continue

            # Detect category headers
            if len(cells) >= 1 and cells[0]:
                cat_text = cells[0].replace("\n", " ")
                if any(kw in cat_text for kw in ["平台课程", "实践教学", "综合素质",
                                                   "通识", "学科", "专业"]) and len(cells) <= 3:
                    if "必修" in cat_text or "必" in cat_text:
                        current_subcategory = "必修"
                    elif "选修" in cat_text or "选" in cat_text:
                        current_subcategory = "选修"
                    current_category = cat_text[:60]
                    continue

            # Look for course code in all cells
            code = ""
            for cell in cells:
                m = COURSE_CODE_RE.search(cell)
                if m:
                    code = m.group(1)
                    break
            if not code:
                continue

            # Extract fields by position
            name = ""
            credits = None
            hours_total = None
            semester = ""

            # Typical table layout:
            # [category, code, name, credits, total_hours, lecture, lab, weekly, semester, notes]
            if len(cells) >= 2:
                # Find name cell (after code cell)
                code_idx = next((i for i, c in enumerate(cells) if code in c), 0)
                if code_idx + 1 < len(cells):
                    name = cells[code_idx + 1].split("\n")[0].strip()[:60]
                # Find numeric cells
                num_cells = []
                for i in range(code_idx + 2, len(cells)):
                    c = cells[i].strip()
                    if CREDIT_NUM_RE.match(c):
                        num_cells.append(c)
                if num_cells:
                    credits = float(num_cells[0])
                if len(num_cells) >= 2:
                    hours_total = float(num_cells[1])
                # Semester is often the last column before notes
                for i in range(len(cells) - 1, code_idx + 1, -1):
                    c = cells[i].strip()
                    if re.match(r"^\d", c) and len(c) <= 6:
                        semester = c
                        break

            if not name or len(name) < 2:
                continue

            is_required = current_subcategory
            # Detect required/elective from note columns
            note_cols = " ".join(cells[-3:])
            if "选" in note_cols and "必" not in note_cols:
                is_required = "选修"
            elif "必" in note_cols:
                is_required = "必修"

            courses.append({
                "code": code,
                "name": name,
                "credits": credits,
                "hours_total": hours_total,
                "semester": semester,
                "category": current_category,
                "required": is_required,
                "source": path.name,
            })

    return courses


def extract_from_pdf_text(text: str, source_name: str) -> list[dict]:
    """Extract course data from already-parsed PDF text (OCR quality varies)."""
    courses: list[dict] = []
    current_subcategory = ""

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect category
        if any(kw in line for kw in ["平台课程", "实践教学", "通识", "学科", "专业"]) and \
           len(line) < 80:
            if "必" in line:
                current_subcategory = "必修"
            elif "选" in line:
                current_subcategory = "选修"
            continue

        code_match = COURSE_CODE_RE.search(line)
        if not code_match:
            continue

        code = code_match.group(1)
        parts = [p.strip() for p in re.split(r"\s{2,}|\t|\|", line) if p.strip()]

        if len(parts) < 3:
            continue

        code_idx = next((i for i, p in enumerate(parts) if code in p), 0)
        name = ""
        if code_idx + 1 < len(parts):
            name = parts[code_idx + 1]
            name = re.sub(r"\s*\(.*?\)", "", name).split("  ")[0].strip()[:60]

        if len(name) < 2 or len(name) > 60:
            continue

        credits = None
        for p in parts[code_idx + 2:]:
            m = CREDIT_NUM_RE.match(p)
            if m:
                credits = float(m.group(1))
                break

        courses.append({
            "code": code,
            "name": name,
            "credits": credits,
            "hours_total": None,
            "semester": "",
            "category": "",
            "required": current_subcategory,
            "source": source_name,
        })

    return courses


CLASSIFY_RULES: list[tuple[str, list[str]]] = [
    ("数学类", ["高等数学", "线性代数", "概率", "离散", "统计", "数值", "数学分析"]),
    ("英语类", ["大学英语", "英语"]),
    ("物理类", ["大学物理", "物理"]),
    ("思政类", ["马克思主义", "中国近现代史", "思想道德", "毛泽东", "习近平",
                "形势与政策", "思政", "马原", "毛概", "思修", "近代史"]),
    ("体育类", ["体育"]),
    ("编程语言类", ["C语言", "C++", "Java", "Python", "程序设计", "编程"]),
    ("计算机核心", ["数据结构", "操作系统", "计算机网络", "计算机组成",
                    "数据库", "编译原理", "算法设计", "软件工程", "软件测试"]),
    ("AI/数据科学", ["机器学习", "人工智能", "深度学习", "自然语言", "图像处理",
                     "智能推荐", "科学计算", "数据挖掘", "神经网络", "经典模型"]),
    ("实践/项目", ["实训", "项目实战", "实践", "实习", "毕业设计", "毕业论文",
                   "课程设计", "PBL", "综合项目"]),
]


def classify_course(name: str) -> str:
    for ctype, keywords in CLASSIFY_RULES:
        if any(k in name for k in keywords):
            return ctype
    return "其他"


def merge_courses(all_courses: list[dict]) -> list[dict]:
    """Deduplicate by course code AND name, merging info from multiple sources."""
    seen: dict[str, dict] = {}
    seen_names: dict[str, str] = {}  # name → code (for name dedup)

    for c in all_courses:
        code = c["code"]
        name = c.get("name", "").strip()

        # If same name seen with different code, use the longer/better entry
        if name and name in seen_names:
            existing_code = seen_names[name]
            existing = seen.get(existing_code)
            if existing:
                # Merge into existing, prefer more complete data
                for key in ["credits", "hours_total", "semester", "required"]:
                    if c.get(key) is not None and existing.get(key) is None:
                        existing[key] = c[key]
                # Keep shorter code (more standard)
                if len(code) < len(existing_code):
                    seen_names[name] = code
                    del seen[existing_code]
                    seen[code] = existing
                    existing["code"] = code
                continue

        if code not in seen:
            seen[code] = dict(c)
            if name:
                seen_names[name] = code
        else:
            existing = seen[code]
            for key in ["credits", "hours_total", "semester", "required"]:
                if c.get(key) is not None and existing.get(key) is None:
                    existing[key] = c[key]
            if len(c.get("name", "")) > len(existing.get("name", "")):
                existing["name"] = c["name"]

    return sorted(seen.values(), key=lambda c: c["code"])


def build_db(args: argparse.Namespace) -> dict:
    program_files = sorted(Path(args.programs_dir).glob("*"))
    program_files = [p for p in program_files
                     if p.suffix.lower() in {".docx", ".pdf"} and not p.name.startswith("~")]
    print(f"Found {len(program_files)} program documents")

    all_courses: list[dict] = []
    for path in program_files:
        print(f"  Processing: {path.name}")
        if path.suffix == ".docx":
            courses = extract_from_docx(path)
        else:
            # Read text from chunks
            chunks_file = Path(args.chunks)
            program_text = ""
            if chunks_file.exists():
                with chunks_file.open(encoding="utf-8") as f:
                    for line in f:
                        c = json.loads(line)
                        sf = c.get("source_file", "")
                        if str(path) in sf or path.name in sf:
                            program_text += c.get("text", "") + "\n"
            if program_text:
                courses = extract_from_pdf_text(program_text, path.name)
            else:
                print(f"    ⚠ No text for {path.name}")
                continue

        for c in courses:
            c["course_type"] = classify_course(c["name"])
        all_courses.extend(courses)
        print(f"    → {len(courses)} courses")

    deduped = merge_courses(all_courses)

    by_type: dict[str, list[str]] = {}
    for c in deduped:
        t = c.get("course_type", "其他")
        by_type.setdefault(t, []).append(c["name"])

    result = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_courses": len(deduped),
        "by_type": {k: len(v) for k, v in sorted(by_type.items())},
        "course_types": {k: sorted(v) for k, v in sorted(by_type.items())},
        "courses": deduped,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programs-dir", default=str(ROOT / "data" / "raw" / "programs"))
    parser.add_argument("--chunks", default=str(ROOT / "data" / "processed" / "chunks.jsonl"))
    parser.add_argument("--out", default=str(ROOT / "data" / "processed" / "learning_map.json"))
    args = parser.parse_args()

    db = build_db(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"Total unique courses: {db['total_courses']}")
    print(f"By type:")
    for t, count in sorted(db["by_type"].items()):
        names = db["course_types"].get(t, [])[:6]
        preview = ", ".join(names)
        if len(db["course_types"].get(t, [])) > 6:
            preview += f" ... (+{count - 6})"
        print(f"  {t}: {count}门 — {preview}")
    print(f"\nOutput: {out_path}")

    if db["total_courses"] < 10:
        print("⚠ Very few courses extracted — check program doc table structure")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
