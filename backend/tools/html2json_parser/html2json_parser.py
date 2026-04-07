from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag


QUESTION_NO_RE = re.compile(r"第\s*(\d+)\s*題")
GROUP_RANGE_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*為題組")
ANSWER_RE = re.compile(r"^\((.*?)\)$")
OPTION_RE = re.compile(r"\(([A-Z])\)\s*(.*?)(?=\s*\([A-Z]\)\s*|$)", re.S)
TITLE_RE = re.compile(r"考試名稱：\s*(.*)")
GROUP_LABEL_RE = re.compile(r"【題組\s*(\d+)】")


@dataclass
class ImageRef:
    src: str
    alt: Optional[str] = None
    belongs_to: str = "question"
    local_name: Optional[str] = None


@dataclass
class QuestionGroup:
    group_id: str
    title: str
    prompt_html: str
    prompt_text: str
    question_range: List[int]
    images: List[Dict[str, Any]]


@dataclass
class Question:
    question_id: str
    number: int
    type: str
    stem: str
    stem_html: str
    options: List[Dict[str, Any]]
    answer: List[str]
    answer_raw: str
    group_id: Optional[str]
    images: List[Dict[str, Any]]
    source_block_index: int
    raw_text: str


class ExamHTMLParser:
    def __init__(self, html: str, source_name: str = "") -> None:
        self.html = html
        self.source_name = source_name
        self.soup = BeautifulSoup(html, "html.parser")
        self.container = self.soup.find(id="exam-download-root") or self.soup.body or self.soup
        self.blocks = self.container.find_all("div", class_=lambda c: c and "border-b" in c)

    def parse(self) -> Dict[str, Any]:
        exam_title = self._extract_exam_title()
        questions: List[Question] = []
        groups: List[QuestionGroup] = []
        current_group_id: Optional[str] = None
        group_counter = 0

        for i, block in enumerate(self.blocks, start=1):
            answer_raw = self._extract_answer(block)
            if not answer_raw:
                continue

            is_multiple_choice = "複選題" in block.get_text(" ", strip=True)
            question_no = self._extract_question_no(block)
            if question_no is None:
                continue

            group = self._extract_group(block)
            if group is not None:
                group_counter += 1
                current_group_id = f"G{group_counter}"
                groups.append(
                    QuestionGroup(
                        group_id=current_group_id,
                        title=group["title"],
                        prompt_html=group["prompt_html"],
                        prompt_text=group["prompt_text"],
                        question_range=group["question_range"],
                        images=group["images"],
                    )
                )
            elif not self._is_question_in_current_group(question_no, groups, current_group_id):
                current_group_id = None

            qnode = self._find_question_body_node(block)
            stem_html = qnode.decode_contents() if qnode else ""
            stem_text = qnode.get_text(" ", strip=True) if qnode else block.get_text(" ", strip=True)
            stem, options = self._split_stem_and_options(stem_text)
            images = self._extract_images(qnode, belongs_to="question") if qnode else []

            questions.append(
                Question(
                    question_id=f"Q{question_no}",
                    number=question_no,
                    type="multiple_select" if is_multiple_choice else "single_select",
                    stem=stem,
                    stem_html=stem_html,
                    options=options,
                    answer=self._normalize_answers(answer_raw),
                    answer_raw=answer_raw,
                    group_id=current_group_id,
                    images=images,
                    source_block_index=i,
                    raw_text=stem_text,
                )
            )

        return {
            "schema_version": "1.0.0",
            "source": {
                "file_name": self.source_name,
                "format": "html",
                "parser": "ExamHTMLParser",
            },
            "exam": {
                "title": exam_title,
                "groups": [asdict(g) for g in groups],
                "questions": [asdict(q) for q in questions],
                "stats": {
                    "question_count": len(questions),
                    "group_count": len(groups),
                },
            },
        }

    def _extract_exam_title(self) -> str:
        p = self.container.find("p")
        if not p:
            return ""
        text = p.get_text(" ", strip=True)
        m = TITLE_RE.search(text)
        return m.group(1).strip() if m else text

    def _extract_answer(self, block: Tag) -> str:
        red = block.find("div", class_=lambda c: c and "text-red-600" in c)
        if not red:
            return ""
        text = red.get_text("", strip=True)
        m = ANSWER_RE.match(text)
        return m.group(1).strip() if m else text.strip("() ")

    def _extract_question_no(self, block: Tag) -> Optional[int]:
        p = block.find("p", string=QUESTION_NO_RE)
        if p:
            m = QUESTION_NO_RE.search(p.get_text(" ", strip=True))
            if m:
                return int(m.group(1))
        text = block.get_text(" ", strip=True)
        m = QUESTION_NO_RE.search(text)
        return int(m.group(1)) if m else None

    def _extract_group(self, block: Tag) -> Optional[Dict[str, Any]]:
        box = block.find("div", class_=lambda c: c and "border-2" in c and "border-black" in c)
        if not box:
            return None

        prompt_html = box.decode_contents()
        prompt_text = box.get_text(" ", strip=True)
        title_match = GROUP_LABEL_RE.search(prompt_text)
        title = title_match.group(0) if title_match else "題組"

        range_text_node = block.find("p", string=GROUP_RANGE_RE)
        range_text = range_text_node.get_text(" ", strip=True) if range_text_node else block.get_text(" ", strip=True)
        m = GROUP_RANGE_RE.search(range_text)
        question_range = [int(m.group(1)), int(m.group(2))] if m else []
        images = self._extract_images(box, belongs_to="group")

        return {
            "title": title,
            "prompt_html": prompt_html,
            "prompt_text": prompt_text,
            "question_range": question_range,
            "images": images,
        }

    def _is_question_in_current_group(
        self,
        qno: int,
        groups: List[QuestionGroup],
        current_group_id: Optional[str],
    ) -> bool:
        if not current_group_id:
            return False
        for g in groups:
            if g.group_id == current_group_id and len(g.question_range) == 2:
                start, end = g.question_range
                return start <= qno <= end
        return False

    def _find_question_body_node(self, block: Tag) -> Optional[Tag]:
        qps = block.find_all("p", string=QUESTION_NO_RE)
        if qps:
            q_label = qps[-1]
            sib = q_label.find_next_sibling("div")
            if sib:
                return sib
        candidates = block.find_all("div", class_=lambda c: c and "break-words" in c)
        if candidates:
            return candidates[-1]
        return None

    def _extract_images(self, node: Optional[Tag], belongs_to: str) -> List[Dict[str, Any]]:
        if node is None:
            return []
        result = []
        for idx, img in enumerate(node.find_all("img"), start=1):
            src = (img.get("src") or "").strip()
            alt = img.get("alt") or None
            result.append(asdict(ImageRef(src=src, alt=alt, belongs_to=belongs_to, local_name=f"img_{idx}")))
        return result

    def _normalize_answers(self, answer_raw: str) -> List[str]:
        return [x.strip() for x in answer_raw.split(",") if x.strip()]

    def _split_stem_and_options(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"^\d+\.\s*", "", text)
        text = text.replace("複選題", "").strip()
        matches = list(OPTION_RE.finditer(text))
        if not matches:
            return text, []

        stem = text[:matches[0].start()].strip()
        options = []
        for m in matches:
            options.append({
                "key": m.group(1),
                "text": re.sub(r"\s+", " ", m.group(2)).strip(),
            })
        return stem, options


def parse_exam_file(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    html = path.read_text(encoding="utf-8")
    parser = ExamHTMLParser(html, source_name=path.name)
    return parser.parse()


def find_html_files(input_dir: Path) -> List[Path]:
    exts = {".html", ".htm", ".HTML", ".HTM"}
    return sorted([p for p in input_dir.rglob("*") if p.is_file() and p.suffix in exts])


def batch_parse(input_dir: str | Path, output_dir: str | Path) -> int:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = find_html_files(input_dir)
    if not files:
        print(f"WARN: 找不到 HTML 檔案，目錄={input_dir.resolve()}")
        return 0

    count = 0
    for file_path in files:
        data = parse_exam_file(file_path)
        out_path = output_dir / f"{file_path.stem}.json"
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK: {file_path} -> {out_path}")
        count += 1

    print(f"DONE: 共處理 {count} 個檔案")
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse exam HTML into structured JSON")
    ap.add_argument("input", help="input html file or directory")
    ap.add_argument("-o", "--output", help="output json file or directory", default=None)
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: 找不到輸入路徑: {input_path.resolve()}")
        return 1

    if input_path.is_file():
        data = parse_exam_file(input_path)
        out = Path(args.output) if args.output else input_path.with_suffix(".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"OK: {input_path} -> {out}")
        print(
            f"DONE: 題目 {data['exam']['stats']['question_count']} 題, 題組 {data['exam']['stats']['group_count']} 組"
        )
        return 0

    out_dir = Path(args.output) if args.output else input_path / "parsed_json"
    batch_parse(input_path, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
