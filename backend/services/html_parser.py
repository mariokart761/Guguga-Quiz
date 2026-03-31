"""
HTML 試卷解析器
將上傳的試卷 HTML 解析為結構化的 paper / group / question / option 資料

支援格式：
  - 阿摩線上測驗 (yamol.tw) 匯出 HTML（主要格式）
  - 通用格式 fallback
"""

import re
import warnings
from typing import Optional
from bs4 import BeautifulSoup, Tag, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


# ── 資料模型 ──────────────────────────────────────────────────────────────────


class ParsedOption:
    def __init__(self, key: str, html: str, text: str):
        self.key = key
        self.html = html
        self.text = text


class ParsedQuestion:
    def __init__(
        self,
        question_no: int,
        stem_html: str,
        stem_text: str,
        question_type: str,
        options: list["ParsedOption"],
        image_urls: list[str],
        group_ref: Optional[int] = None,
    ):
        self.question_no = question_no
        self.stem_html = stem_html
        self.stem_text = stem_text
        self.question_type = question_type
        self.options = options
        self.image_urls = image_urls
        self.group_ref = group_ref


class ParsedGroup:
    def __init__(
        self,
        group_no: int,
        intro_html: str,
        intro_text: str,
        start_no: int,
        end_no: int,
        image_urls: list[str],
    ):
        self.group_no = group_no
        self.intro_html = intro_html
        self.intro_text = intro_text
        self.start_no = start_no
        self.end_no = end_no
        self.image_urls = image_urls


class ParsedPaper:
    def __init__(self):
        self.title: str = ""
        self.subject: str = ""
        self.exam_year: Optional[int] = None
        self.term: str = ""
        self.groups: list[ParsedGroup] = []
        self.questions: list[ParsedQuestion] = []
        self.answers: dict[int, str] = {}  # question_no -> "A" | "A,B,C"


# ── 工具函式 ──────────────────────────────────────────────────────────────────


def extract_text(element) -> str:
    if element is None:
        return ""
    return element.get_text(separator=" ", strip=True)


def extract_images(element) -> list[str]:
    if element is None:
        return []
    return [img.get("src", "") for img in element.find_all("img") if img.get("src")]


def split_stem_and_options(inner_html: str) -> tuple[str, list[tuple[str, str]]]:
    """
    將題目段落的 inner HTML 拆分為題幹 HTML 與選項清單。

    輸入範例：
      "1.某題幹...(A)選項A文字(B)選項B文字(C)選項C(D)選項D"

    支援全形括號 （A） 及半形括號 (A)。
    回傳 (stem_html, [(key, option_inner_html), ...])
    """
    # 以 (A)(B)(C)(D) 分割，支援全/半形括號
    option_pat = re.compile(r"[\(（]([A-Da-d])[\)）]")
    parts = option_pat.split(inner_html)

    if len(parts) < 3:
        # 沒有找到選項，整段當題幹
        return inner_html, []

    stem_html = parts[0]
    options: list[tuple[str, str]] = []
    i = 1
    while i + 1 < len(parts):
        key = parts[i].upper()
        content = parts[i + 1].strip()
        options.append((key, content))
        i += 2

    return stem_html, options


# ── 主解析器 ──────────────────────────────────────────────────────────────────


class QuizHTMLParser:
    """
    解析試卷 HTML 的主要 class。

    策略：
      1. 偵測到阿摩 (yamol.tw) 格式 → 使用精確的結構化解析
      2. 無法偵測 → fallback 通用格式（依題號定位）
    """

    def __init__(self, html_content: str):
        self.soup = BeautifulSoup(html_content, "lxml")
        self.result = ParsedPaper()
        self._group_counter = 0
        self._current_group: Optional[ParsedGroup] = None

    def parse(self) -> ParsedPaper:
        self._extract_meta()
        if not self._try_yamol_format():
            self._extract_answers_generic()
            self._extract_questions_generic()
        return self.result

    # ── Meta ─────────────────────────────────────────────────────────────────

    def _extract_meta(self):
        # 優先找阿摩格式的考試名稱段落（class 含 pageTitleSmall 或含「考試名稱：」文字）
        title_p = self.soup.find("p", class_=re.compile(r"pageTitleSmall"))
        if not title_p:
            title_p = self.soup.find(
                lambda tag: tag.name == "p" and "考試名稱" in tag.get_text()
            )

        if title_p:
            raw = extract_text(title_p)
        else:
            title_el = self.soup.find("title") or self.soup.find("h1")
            raw = extract_text(title_el) if title_el else ""

        # 移除阿摩後綴：「...#126101 - 阿摩線上測驗」
        raw = re.sub(r"#\d+\s*[-–]\s*阿摩線上測驗.*$", "", raw).strip()
        raw = re.sub(r"^考試名稱[：:]\s*", "", raw).strip()
        self.result.title = raw

        year_match = re.search(r"(\d{2,3})\s*[年-]", self.result.title)
        if year_match:
            year = int(year_match.group(1))
            if year < 200:
                year += 1911
            self.result.exam_year = year

    # ── 阿摩格式解析 ─────────────────────────────────────────────────────────

    def _try_yamol_format(self) -> bool:
        """
        嘗試以阿摩格式解析。
        偵測特徵：存在 div.border-b.border-gray-200.pb-4 容器。
        """
        containers = self.soup.select("div.border-b.border-gray-200.pb-4")
        if not containers:
            return False
        for container in containers:
            self._parse_yamol_container(container)
        return len(self.result.questions) > 0

    def _parse_yamol_container(self, container: Tag):
        """解析單個阿摩格式的題目容器"""

        # 1. 答案（左側紅色欄位中間的 div.text-center）
        answer_div = container.select_one("div.text-center")
        answer_raw = answer_div.get_text(strip=True) if answer_div else ""
        clean_ans = re.sub(r"[，、\s]", ",", answer_raw.upper()) if answer_raw else ""

        # 2. 右側內容區（div.flex-1）
        content_div = container.select_one("div.flex-1")
        if not content_div:
            return

        # 3. 題組導言框（若存在，代表本題是該題組的第一題）
        group_box = content_div.select_one("div.rounded-sm.border-2.border-black")
        if group_box:
            self._parse_group_box(group_box, content_div)

        # 4. 題號（第N題 段落）
        question_no: Optional[int] = None
        for p in content_div.find_all("p"):
            m = re.search(r"第\s*(\d+)\s*題", p.get_text())
            if m:
                question_no = int(m.group(1))
                break

        if question_no is None:
            return

        # 5. 題目內容區（div.w-full.break-words）
        content_inner = content_div.select_one("div.w-full.break-words")
        if not content_inner:
            return

        # 6. 複選題判斷：有「複選題」標記，或答案含逗號
        is_multiple = bool(content_inner.find("b", string=re.compile(r"複選")))
        if clean_ans and "," in clean_ans:
            is_multiple = True

        # 7. 題目段落（div.w-full.break-words 中的 <p>）
        question_p = content_inner.find("p")
        if not question_p:
            return

        # 8. 從 inner HTML 拆分題幹與選項
        inner_html = question_p.decode_contents()
        stem_raw_html, option_pairs = split_stem_and_options(inner_html)

        # 去掉題幹前面的題號前綴（"1." / "1、"）
        stem_soup = BeautifulSoup(stem_raw_html, "lxml")
        stem_text_raw = stem_soup.get_text(separator="", strip=True)
        stem_text = re.sub(r"^\d+[.、．]\s*", "", stem_text_raw).strip()

        # 9. 建立選項物件
        options: list[ParsedOption] = []
        for key, opt_inner in option_pairs:
            opt_soup = BeautifulSoup(opt_inner, "lxml")
            opt_text = opt_soup.get_text(separator="", strip=True)
            options.append(ParsedOption(
                key=key,
                html=f"<span>({key}) {opt_inner}</span>",
                text=f"({key}) {opt_text}",
            ))

        # 10. 圖片（題目段落內的 <img>）
        image_urls = extract_images(question_p)

        # 11. 更新答案表
        if clean_ans:
            self.result.answers[question_no] = clean_ans

        # 12. 題組關聯
        group_ref = self._resolve_group_ref(question_no)

        self.result.questions.append(ParsedQuestion(
            question_no=question_no,
            stem_html=str(question_p),
            stem_text=stem_text,
            question_type="multiple" if is_multiple else "single",
            options=options,
            image_urls=image_urls,
            group_ref=group_ref,
        ))

    def _parse_group_box(self, group_box: Tag, content_div: Tag):
        """解析題組導言框，建立 ParsedGroup 並追蹤為 current group"""
        self._group_counter += 1

        intro_html = str(group_box)
        intro_text = extract_text(group_box)
        image_urls = extract_images(group_box)

        # 尋找 "X-Y 為題組" 範圍標記
        start_no, end_no = 0, 0
        for p in content_div.find_all("p"):
            m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*為題組", p.get_text())
            if m:
                start_no = int(m.group(1))
                end_no = int(m.group(2))
                break

        group = ParsedGroup(
            group_no=self._group_counter,
            intro_html=intro_html,
            intro_text=intro_text,
            start_no=start_no,
            end_no=end_no,
            image_urls=image_urls,
        )
        self.result.groups.append(group)
        self._current_group = group

    def _resolve_group_ref(self, question_no: int) -> Optional[int]:
        """根據題號決定所屬題組編號；若超出範圍則清除 current group"""
        if self._current_group is None:
            return None
        g = self._current_group
        if g.start_no > 0 and g.start_no <= question_no <= g.end_no:
            return g.group_no
        if g.start_no == 0:
            # 若無法解析範圍，先不清除，讓後續題目也可能屬於此題組
            return g.group_no
        # 超出範圍
        self._current_group = None
        return None

    # ── 通用格式 fallback ─────────────────────────────────────────────────────

    def _extract_answers_generic(self):
        """從 HTML 中尋找答案欄，解析「1.A 2.B 3.CD」格式"""
        answer_section = None
        for keyword in ["答案", "解答", "答案欄", "Answer"]:
            answer_section = self.soup.find(
                lambda tag: tag.name in ["div", "table", "section", "p"]
                and keyword in tag.get_text()
            )
            if answer_section:
                break

        if not answer_section:
            return

        text = answer_section.get_text()
        matches = re.findall(r"(\d+)[.、\s]+([A-Da-d,，、]+)", text)
        for no_str, ans in matches:
            clean = re.sub(r"[，、\s]", ",", ans.upper())
            self.result.answers[int(no_str)] = clean

    def _extract_questions_generic(self):
        """通用格式：在 p/div/li 中依題號定位，逐題解析"""
        question_pattern = re.compile(r"^\s*(\d+)[.、．\s]")
        candidates = self.soup.find_all(["p", "div", "li", "tr"])

        question_starts: list[tuple[int, Tag]] = []
        for el in candidates:
            text = el.get_text(strip=True)
            m = question_pattern.match(text)
            if m:
                no = int(m.group(1))
                if 1 <= no <= 300:
                    question_starts.append((no, el))

        if not question_starts:
            return

        seen: set[int] = set()
        unique_starts: list[tuple[int, Tag]] = []
        for no, el in question_starts:
            if no not in seen:
                seen.add(no)
                unique_starts.append((no, el))
        unique_starts.sort(key=lambda x: x[0])

        for i, (no, el) in enumerate(unique_starts):
            q = self._parse_question_generic(no, el, unique_starts, i)
            if q:
                self.result.questions.append(q)

    def _parse_question_generic(
        self,
        no: int,
        el: Tag,
        all_starts: list[tuple[int, Tag]],
        idx: int,
    ) -> Optional[ParsedQuestion]:
        stem_parts: list[Tag] = [el]
        current = el.next_sibling
        options_raw: list[Tag] = []
        option_pattern = re.compile(r"^\s*[\(（]?([A-Da-d])[\)）]?[.、\s]")
        next_no = all_starts[idx + 1][0] if idx + 1 < len(all_starts) else None

        while current is not None:
            if hasattr(current, "get_text"):
                text = current.get_text(strip=True)
                if next_no and re.match(rf"^\s*{next_no}[.、．\s]", text):
                    break
                if option_pattern.match(text):
                    options_raw.append(current)
                elif not options_raw:
                    stem_parts.append(current)
            current = current.next_sibling

        stem_html = "".join(str(p) for p in stem_parts)
        stem_text = " ".join(
            p.get_text(strip=True) for p in stem_parts if hasattr(p, "get_text")
        )

        options: list[ParsedOption] = []
        for opt_el in options_raw:
            opt_text = opt_el.get_text(strip=True)
            m = re.match(r"^\s*[\(（]?([A-Da-d])[\)）]?\s*[.、]?\s*(.*)", opt_text, re.DOTALL)
            if m:
                options.append(ParsedOption(
                    key=m.group(1).upper(),
                    html=str(opt_el),
                    text=opt_text,
                ))

        image_urls: list[str] = []
        for part in stem_parts + options_raw:
            if hasattr(part, "find_all"):
                image_urls.extend(extract_images(part))

        answer_raw = self.result.answers.get(no, "")
        q_type = "multiple" if (answer_raw and "," in answer_raw) else "single"

        return ParsedQuestion(
            question_no=no,
            stem_html=stem_html,
            stem_text=stem_text,
            question_type=q_type,
            options=options,
            image_urls=image_urls,
        )


# ── 對外介面 ──────────────────────────────────────────────────────────────────


def parse_quiz_html(html_content: str) -> ParsedPaper:
    """解析 HTML 字串，回傳 ParsedPaper"""
    return QuizHTMLParser(html_content).parse()
