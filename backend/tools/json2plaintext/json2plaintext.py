import json
import re
import html
import argparse
from pathlib import Path


def clean_text(text: str) -> str:
    """清理文字：去除 HTML escape、多餘空白、斷行。"""
    if text is None:
        return ""

    text = html.unescape(str(text))
    text = text.replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def normalize_question_stem(stem: str, number) -> str:
    """去掉前面可能重複的題號與複選題字樣。"""
    stem = clean_text(stem)
    if number is not None:
        stem = re.sub(rf"^\s*{re.escape(str(number))}\s*[\.、]\s*", "", stem)
    stem = re.sub(r"^\s*複選題\s*", "", stem)
    return stem.strip()


def build_group_map(groups: list) -> dict:
    """建立 group_id -> group 資料對照表"""
    result = {}
    for g in groups:
        group_id = g.get("group_id")
        if group_id:
            result[group_id] = {
                "title": clean_text(g.get("title", "")),
                "prompt_text": clean_text(g.get("prompt_text", "")),
            }
    return result


def format_question(q: dict, group_map: dict, shown_groups: set, include_answers: bool) -> str:
    number = q.get("number", "")
    qtype = q.get("type", "")
    stem = normalize_question_stem(q.get("stem", ""), number)
    options = q.get("options", [])
    answers = q.get("answer", [])
    group_id = q.get("group_id")

    lines = []

    # 題組背景只輸出一次
    if group_id and group_id in group_map and group_id not in shown_groups:
        group = group_map[group_id]
        if group["title"]:
            lines.append(group["title"])
        if group["prompt_text"]:
            lines.append(group["prompt_text"])
        lines.append("")
        shown_groups.add(group_id)

    # 題型標記
    if qtype == "multiple_select":
        lines.append(f"{number}. {stem}（複選題）")
    else:
        lines.append(f"{number}. {stem}")

    # 選項
    for opt in options:
        key = clean_text(opt.get("key", ""))
        text = clean_text(opt.get("text", ""))
        lines.append(f"({key}) {text}")

    # 答案
    if include_answers and answers:
        if len(answers) == 1:
            lines.append(f"答案：{answers[0]}")
        else:
            lines.append(f"答案：{', '.join(map(str, answers))}")

    return "\n".join(lines)


def convert_json_to_text(input_file: Path, output_file: Path, include_answers: bool = False) -> None:
    with input_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    exam = data.get("exam", {})
    title = clean_text(exam.get("title", input_file.stem))
    groups = exam.get("groups", [])
    questions = exam.get("questions", [])

    if not isinstance(questions, list):
        raise ValueError("JSON 格式不符：exam.questions 不是陣列")

    group_map = build_group_map(groups)
    shown_groups = set()

    output_lines = [title, "=" * len(title), ""]

    for q in questions:
        if not isinstance(q, dict):
            continue
        block = format_question(
            q=q,
            group_map=group_map,
            shown_groups=shown_groups,
            include_answers=include_answers,
        )
        output_lines.append(block)
        output_lines.append("")

    final_text = "\n".join(output_lines).strip() + "\n"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(final_text)


def batch_convert(input_dir: Path, output_dir: Path, include_answers: bool = False) -> None:
    json_files = sorted(input_dir.glob("*.json"))

    if not json_files:
        print(f"[提醒] 在資料夾中找不到 JSON：{input_dir}")
        return

    success_count = 0
    fail_count = 0

    for json_file in json_files:
        output_file = output_dir / f"{json_file.stem}.txt"

        try:
            convert_json_to_text(
                input_file=json_file,
                output_file=output_file,
                include_answers=include_answers,
            )
            print(f"[成功] {json_file.name} -> {output_file.name}")
            success_count += 1
        except Exception as e:
            print(f"[失敗] {json_file.name}：{e}")
            fail_count += 1

    print("\n====== 批次處理完成 ======")
    print(f"成功：{success_count}")
    print(f"失敗：{fail_count}")
    print(f"輸出資料夾：{output_dir.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="將整個資料夾中的考題 JSON 批次轉成乾淨的選擇題文字檔"
    )
    parser.add_argument(
        "input_dir",
        help="輸入 JSON 資料夾路徑"
    )
    parser.add_argument(
        "output_dir",
        help="輸出 TXT 資料夾路徑"
    )
    parser.add_argument(
        "--include-answers",
        action="store_true",
        help="若加上此參數，輸出時會包含答案"
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"[錯誤] 輸入資料夾不存在：{input_dir}")
        return

    if not input_dir.is_dir():
        print(f"[錯誤] 輸入路徑不是資料夾：{input_dir}")
        return

    batch_convert(
        input_dir=input_dir,
        output_dir=output_dir,
        include_answers=args.include_answers
    )


if __name__ == "__main__":
    main()