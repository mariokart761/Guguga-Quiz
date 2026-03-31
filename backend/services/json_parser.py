"""
JSON 試卷解析器
將 yamol_parser 工具輸出的 JSON 格式（schema_version 1.0.0）
轉換為與 html_parser 相同的 ParsedPaper 結構，以便複用 import 流程。
"""

import json
import re
from typing import Any

from services.html_parser import (
    ParsedGroup,
    ParsedOption,
    ParsedPaper,
    ParsedQuestion,
)


def parse_quiz_json(json_content: str) -> ParsedPaper:
    """解析 yamol JSON 字串，回傳 ParsedPaper"""
    data = json.loads(json_content)
    return _JsonParser(data).parse()


class _JsonParser:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.result = ParsedPaper()

    def parse(self) -> ParsedPaper:
        exam: dict = self.data.get("exam", {})
        self._parse_meta(exam)
        group_id_to_no = self._parse_groups(exam)
        self._parse_questions(exam, group_id_to_no)
        return self.result

    # ── meta ──────────────────────────────────────────────────────────────────

    def _parse_meta(self, exam: dict):
        title = exam.get("title", "")
        # 移除阿摩後綴「…#126101 - 阿摩線上測驗」
        title = re.sub(r"#\d+\s*[-–]\s*阿摩線上測驗.*$", "", title).strip()
        # 移除「考試名稱：」前綴（若有）
        title = re.sub(r"^考試名稱[：:]\s*", "", title).strip()
        self.result.title = title

        year_match = re.search(r"(\d{2,3})\s*[年-]", title)
        if year_match:
            year = int(year_match.group(1))
            if year < 200:
                year += 1911
            self.result.exam_year = year

    # ── groups ────────────────────────────────────────────────────────────────

    def _parse_groups(self, exam: dict) -> dict[str, int]:
        """建立題組，回傳 group_id_str → group_no 對照表"""
        group_id_to_no: dict[str, int] = {}

        for idx, g in enumerate(exam.get("groups", []), start=1):
            group_id_str = g.get("group_id", f"G{idx}")
            group_id_to_no[group_id_str] = idx

            q_range: list[int] = g.get("question_range", [0, 0])
            image_urls = [
                img["src"]
                for img in g.get("images", [])
                if img.get("src")
            ]

            self.result.groups.append(ParsedGroup(
                group_no=idx,
                intro_html=g.get("prompt_html", ""),
                intro_text=g.get("prompt_text", ""),
                start_no=q_range[0] if len(q_range) > 0 else 0,
                end_no=q_range[1] if len(q_range) > 1 else 0,
                image_urls=image_urls,
            ))

        return group_id_to_no

    # ── questions ─────────────────────────────────────────────────────────────

    def _parse_questions(self, exam: dict, group_id_to_no: dict[str, int]):
        for q in exam.get("questions", []):
            number: int = q.get("number", 0)

            # 題型
            raw_type = q.get("type", "single_select")
            q_type = "multiple" if raw_type == "multiple_select" else "single"

            # 答案
            answer_list: list[str] = q.get("answer", [])
            answer_raw: str = q.get("answer_raw") or ",".join(answer_list)
            if answer_raw:
                self.result.answers[number] = answer_raw.upper()

            # 選項（JSON 已經分開，直接對應）
            options = [
                ParsedOption(
                    key=opt["key"].upper(),
                    html=f"<span>{opt.get('text', '')}</span>",
                    text=opt.get("text", ""),
                )
                for opt in q.get("options", [])
            ]

            # 題組關聯
            group_id_str = q.get("group_id")
            group_ref = group_id_to_no.get(group_id_str) if group_id_str else None

            # 題目自身的圖片（不含題組圖片）
            image_urls = [
                img["src"]
                for img in q.get("images", [])
                if img.get("src") and img.get("belongs_to") != "group"
            ]

            # 題幹 HTML：優先使用 stem_html，退而求其次用 stem 純文字
            stem_html = q.get("stem_html") or f"<p>{q.get('stem', '')}</p>"
            stem_text = q.get("stem", "")

            self.result.questions.append(ParsedQuestion(
                question_no=number,
                stem_html=stem_html,
                stem_text=stem_text,
                question_type=q_type,
                options=options,
                image_urls=image_urls,
                group_ref=group_ref,
            ))
