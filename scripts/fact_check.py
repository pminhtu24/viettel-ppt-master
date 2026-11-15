#!/usr/bin/env python3
"""Fact audit for drawn pages.

Wording on a slide is free; claim-bearing tokens are not. Every number, period label, section
name and status word a slide shows must trace to the source blocks its text is bound to, keep the
qualifiers the source attaches to it, and stay inside the source section it comes from. The checks
are deterministic; what they cannot decide goes to a review table for the main agent.

  python3 fact_check.py audit <project> [--pages 3,7]   findings per page (JSON); exit 1 on errors
  python3 fact_check.py table <project> [--pages ...]   Markdown review table for the main agent
  python3 fact_check.py outline <project>               source blocks with their section path

Bindings: an SVG text binds source blocks through `data-src="<block-id> …"` or, for content
contract v1, through `data-claims` → content-lock facts → `sources[].ref` (inherited from parent
groups, as in content_check.py).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ---------------------------------------------------------------- text normalisation

ALIASES = [  # applied to lower-cased text, so slide and source spell qualifiers the same way
    (r"\bluỹ\b", "lũy"), (r"\blk\b", "lũy kế"), (r"\bkh\b", "kế hoạch"), (r"\bth\b", "thực hiện"),
    (r"\bq([1-4])\b", r"quý \1"), (r"\bt([1-9]|1[0-2])\b", r"tháng \1"), (r"\bytd\b", "lũy kế năm"),
]
PERIOD_RE = re.compile(r"\b(tuần(?: (?:này|sau|trước|tới|\d{1,2}))?|tháng(?: \d{1,2})?|quý(?: [1-4])?"
                       r"|năm(?: \d{4})?|lũy kế|6 tháng đầu năm|nửa đầu năm|cả năm)\b")
NUM_RE = re.compile(r"(?<![\w/.,])\d+(?:[.,]\d+)*(?:/\d+(?:[.,]\d+)*)*(?!G\b)")   # 5G is a name; v1.0.5 is not 0.5
RATIO_RE = re.compile(r"(?<![\w/.,])(\d{1,4})/(\d{1,4})(?![\w/.,]*\d)")
STATUS_RE = re.compile(r"\b(chậm|quá hạn|hoàn thành|hoàn thiện|không đạt|đạt|vượt|tăng|giảm|dẫn đầu|đứng đầu|thắng thầu)\b")
HEDGES = ("nguy cơ", "dự kiến", "có thể", "đề xuất", "mục tiêu", "chưa", "không", "cần", "kế hoạch")


def hedge_before(text: str, at: int) -> str | None:
    """The hedge or negation in the words before a status word; "đang" only right before "hoàn thành/thiện"
    ("đang hoàn thiện" is not done yet, "đang chậm" is just "chậm")."""
    if text[max(0, at - 5):at] == "đang " and text.startswith("hoàn", at):
        return "đang"
    return next((h for h in HEDGES if h in text[max(0, at - 25):at]), None)


ORDINAL_RE = re.compile(r"\b(phần|part|chương|mục|bước|step|giai đoạn|gđ|section|sự cố|lần|đợt|kịch bản)\s*$")
STOPWORDS = set("""và của các những cho với trong là được có đã đang sẽ này đó từ theo về tại trên để một
hai ba bốn năm đến khi như cũng thì mà nên hoặc hay bị do vì nhằm qua ra vào lên xuống sau trước nhất
rất hơn nhiều mỗi toàn bộ cùng còn chỉ tới gồm bao giờ đây đều không chưa cần phải ngày hạn the of and to
for in on with by from at a an is are be as or new""".split())


def clean(text: str) -> str:
    """Plain visible text: no HTML tags, Markdown emphasis or escapes, single spaces."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|~<>])", r"\1", text)
    text = re.sub(r"[*`]+", "", text)
    return " ".join(unicodedata.normalize("NFC", text).split())


def norm(text: str) -> str:
    text = clean(text).lower()
    for pattern, repl in ALIASES:
        text = re.sub(pattern, repl, text)
    return text


def loose(text: str) -> str:
    """For name matching: `TT. VHKTTC` = `TT VHKTTC`, `P.NS` = `P NS`."""
    return " ".join(re.sub(r"(?<=\w)\.(?=\w|\s)", " ", norm(text)).split())


def num_key(token: str) -> str:
    parts = [re.sub(r"[.,]", "", part).lstrip("0") or "0" for part in token.split("/")]
    if len(parts) == 3 and len(parts[2]) == 2:
        parts[2] = "20" + parts[2]                              # 17/8/26 = 17/8/2026
    return "/".join(parts)


def numbers(text: str) -> list[tuple[int, str]]:
    """(position, canonical) for every number, ratio or date token. A slash right after a word is a
    separator, not a ratio (`tuyến/12%`)."""
    text = re.sub(r"(?<=[^\W\d_])/(?=\d)", " ", text)
    return [(m.start(), num_key(m.group())) for m in NUM_RE.finditer(text)]


def number_set(text: str) -> set[str]:
    keys = {k for _, k in numbers(text)}
    extra = {k.rsplit("/", 1)[0] for k in keys if k.count("/") == 2}        # 24/8/2026 also answers 24/8
    extra |= {part for k in keys if k.count("/") == 1 for part in k.split("/")}   # 87.280/105.168 answers 87.280
    return keys | extra


def _date_like(token: str) -> bool:
    parts = token.split("/")
    return len(parts) in (2, 3) and parts[0].isdigit() and parts[1].isdigit() and 1 <= int(parts[0]) <= 31 \
        and 1 <= int(parts[1]) <= 12


def _count(part: str) -> int | None:
    """`1.406` → 1406; None for decimals (`0,9`, `9.7`), which are not counts."""
    return int(part.replace(".", "")) if re.fullmatch(r"\d{1,3}(\.\d{3})+|\d+", part) else None


def ratio_percents(text: str) -> list[tuple[list[int], float, int]]:
    """Every `a/b[/c…]` of whole numbers that is directly followed by its percentage:
    `21/75/160 trạm ~46,88%` → ([21, 75, 160], 46.88, 2). Dates, decimals and ranks are skipped."""
    text = re.sub(r"(?<=[^\W\d_])/(?=\d)", " ", text)
    tokens = list(NUM_RE.finditer(text))
    out = []
    for m, nxt in zip(tokens, tokens[1:]):
        parts = [_count(part) for part in m.group().split("/")]
        pct = re.fullmatch(r"\d+(?:[.,]\d+)?", nxt.group())
        if (len(parts) < 2 or None in parts or _date_like(m.group()) or not pct or nxt.start() - m.end() > 25
                or not re.match(r"\s*%", text[nxt.end():])
                or re.search(r"(thứ|hạng|top)\s*$", text[:m.start()].lower())):      # a rank (thứ 9/34), not a share
            continue
        value = nxt.group().replace(",", ".")
        out.append((parts, float(value), len(value.partition(".")[2])))
    return out


def pct_matches(a: int, b: int, pct: float, decimals: int) -> bool:
    """Rounded or truncated to the decimals shown (65,74 → ~66%, 65,9 → 65%)."""
    return b > 0 and abs(a / b * 100 - pct) <= 10 ** -decimals + 1e-9


def is_measure(text: str) -> bool:
    """A measured fact (percentage, count, ratio) — not a date or a single-digit name like 5G."""
    return "%" in text or any(("/" in t and not _date_like(t)) or ("/" not in t and len(re.sub(r"\D", "", t)) >= 2)
                              for t in NUM_RE.findall(text))


def periods(text_norm: str) -> list[tuple[int, str]]:
    return [(m.start(), m.group()) for m in PERIOD_RE.finditer(text_norm)]


def period_in(phrase: str, context_norm: str) -> bool:
    """`quý 3` needs `quý 3`; bare `quý` is satisfied by any quarter; `lũy kế` by itself."""
    if re.search(r"\d", phrase):
        return phrase in context_norm
    return re.search(rf"\b{re.escape(phrase)}\b", context_norm) is not None


def words(text_norm: str) -> list[str]:
    return [w for w in re.findall(r"[^\W\d_]+", text_norm) if w not in STOPWORDS and len(w) > 1]


def has_name(name: str, text_loose: str) -> bool:
    """Whole-word match; the parts of a multi-word code may be written together (TT VHKT = TTVHKT)."""
    pattern = r"\s*".join(re.escape(part) for part in loose(name).split())
    return re.search(rf"(?<!\w){pattern}(?!\w)", text_loose) is not None


# ---------------------------------------------------------------- source outline

@dataclass
class Block:
    id: str
    text: str                                  # cleaned
    path: list[str] = field(default_factory=list)
    header: str = ""                           # table header rows, for table cells
    title: str = ""                            # set when this block heads the blocks after it

    @property
    def context(self) -> str:
        return norm(" ".join([self.text, *self.path, self.header]))

    def raw_clauses(self) -> list[str]:
        """Clauses as written: `;`-separated parts and sentences; a short lead-in (before `:`)
        belongs to every clause."""
        body, lead = self.text, ""
        m = re.match(r"^(.{3,80}?):\s", body)
        if m and not NUM_RE.search(m.group(1)):
            lead, body = m.group(1) + ":", body[m.end():]
        parts = [p for p in re.split(r";\s*|(?<=[^\d\s])\.\s+", body) if p.strip()]
        return [f"{lead} {p}".strip() for p in parts] or [self.text]

    def clauses(self) -> list[str]:
        return [norm(c) for c in self.raw_clauses()]


_HEAD_MD = re.compile(r"^(#{1,6})\s+(.*)$")
_HEAD_NUM = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*[.:]?\s*$")
_BULLET = re.compile(r"^\s*[*+-]\s+(.*)$")


def _bullet_heading(rest: str) -> bool:
    """Bullets that head the bullets after them: emphasised-only text (optionally with a parenthetical
    note) that is not itself a measured fact, or any short bullet ending with `:`."""
    plain = clean(rest)
    if len(plain) > 160:
        return False
    if plain.endswith(":") and len(plain) <= 90:
        return True
    if not rest.startswith("*"):
        return False
    outside = re.sub(r"\*{1,3}[^*]+\*{1,3}", "", rest).strip(" :.*")
    emphasised_only = outside == "" or (outside.startswith("(") and outside.endswith(")"))
    bold = " ".join(re.findall(r"\*{1,3}([^*]+)\*{1,3}", rest))
    return emphasised_only and not is_measure(bold)


def build_outline(project: Path) -> dict[str, Block]:
    """Every indexed block with the headings above it. Word exports are often flat, so headed bullets
    act as sub-headings: bracketed tags ([TTKTKV3]) one level up, consecutive ones nest, and a heading
    after content replaces the deepest one."""
    index = json.loads((project / "sources/source_index.json").read_text(encoding="utf-8"))
    out: dict[str, Block] = {}
    for record in index["sources"].values():
        text = (project / record["path"]).read_text(encoding="utf-8")
        spans = sorted(record["blocks"].items(), key=lambda kv: (kv[1][0], -kv[1][1]))
        stack: list[tuple[float, str]] = []
        prev_heading_level: float | None = None
        md_header: list[str] = []
        html_table: tuple[int, int, str] | None = None
        for bid, (start, end) in spans:
            raw = text[start:end]
            path = [title for _, title in stack]
            if raw.lstrip().lower().startswith("<tr"):                       # HTML table row
                header = html_table[2] if html_table and html_table[0] <= start < html_table[1] else ""
                out[bid] = Block(bid, clean(raw), path, header)
                continue
            if "<table" in raw.lower():
                rows = re.findall(r"<tr\b.*?</tr>", raw, re.S | re.I)
                html_table = (start, end, clean(" ".join(rows[:2])))
                out[bid] = Block(bid, clean(raw), path)
                prev_heading_level = None
                continue
            if raw.lstrip().startswith("|"):                                  # Markdown table row
                cells = [c.strip() for c in raw.strip().strip("|").split("|")]
                if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
                    continue
                if all(not c or c.startswith("**") for c in cells):
                    md_header.append(clean(raw))
                    out[bid] = Block(bid, clean(raw), path)
                else:
                    out[bid] = Block(bid, clean(raw), path, " ".join(md_header))
                prev_heading_level = None
                continue
            md_header = []
            level, title = None, ""
            if m := _HEAD_MD.match(raw):
                level, title = len(m.group(1)) + 1, m.group(2)
            elif (m := _HEAD_NUM.match(raw)) and len(m.group(1)) <= 90:   # a long bold sentence is content
                level, title = 1, m.group(1)
            elif (m := _BULLET.match(raw)) and _bullet_heading(m.group(1).strip()):
                rest = m.group(1).strip()
                bracket = rest.lstrip("*").startswith("[")
                deepest = max((lv for lv, _ in stack if lv >= 7), default=None)
                if prev_heading_level is not None and prev_heading_level >= 6:
                    level = prev_heading_level + 1
                else:
                    level = 6 if bracket else (deepest or 7)
                title = rest
            if level is not None:
                while stack and stack[-1][0] >= level:
                    stack.pop()
                path = [t for _, t in stack]
            out[bid] = Block(bid, clean(re.sub(r"^\s*(?:#{1,6}|[*+-])\s+", "", raw)), path,
                             title=clean(title) if level is not None else "")
            if level is not None:
                stack.append((level, clean(title)))
            prev_heading_level = level
    return out


_ASCII_CODE = re.compile(r"^(?=(?:[^A-Z]*[A-Z]){2})[A-Za-z][A-Za-z0-9&]{2,}$")  # APEC, TTKTKV3, VTNet, CMU0508
_LATIN_NAME = re.compile(r"^[A-Z][a-z]{3,}$")                                  # Dominica, Starlink


_CODE_TOKEN = re.compile(r"(?<![\w&])[A-Za-z][A-Za-z0-9&]{2,}(?![\w&])")
BRAND_WORDS = {"viettel"}


def source_corpus(outline: dict[str, Block]) -> str:
    return " ".join(" ".join([b.text, b.header, *b.path]) for b in outline.values()).lower()


def invented_codes(text: str, corpus: str) -> list[str]:
    """Codes and capitalised names (VTNT, NetBi, TTDL) in mixed-case text that the source never writes.
    All-caps lines (decorative labels, headings) are left alone: their words are not names."""
    if not any(c.islower() for c in text):
        return []
    out = [m.group() for m in _CODE_TOKEN.finditer(text)
           if _ASCII_CODE.match(m.group()) and m.group().lower() not in BRAND_WORDS
           and not re.search(rf"(?<![\w&]){re.escape(m.group().lower())}(?![\w&])", corpus)]
    return list(dict.fromkeys(out))


def entity_vocabulary(outline: dict[str, Block]) -> tuple[set[str], set[str]]:
    """(names, section names). Names are proper names and codes that identify a part of the source;
    section names are the ones that also appear in a heading (place, project, unit, workstream).
    Names spread over many blocks (the reporting unit itself, KPI, KH) identify nothing."""
    found: dict[str, set[str]] = {}
    for block in outline.values():
        text = block.text
        tokens = list(re.finditer(r"[^\W\d_][\w&]*", text))
        i = 0
        while i < len(tokens):
            if not tokens[i].group()[:1].isupper():
                i += 1
                continue
            j = i
            while (j + 1 < len(tokens) and tokens[j + 1].group()[:1].isupper()
                   and text[tokens[j].end():tokens[j + 1].start()] == " "):
                j += 1
            run = [t.group() for t in tokens[i:j + 1]]
            if any(w.isupper() and not w.isascii() for w in run):
                i = j + 1                                       # an all-caps Vietnamese heading, not names
                continue
            before = text[:tokens[i].start()].rstrip()
            mid = bool(before) and before[-1] not in ".:!?;-–(*#|>+[\"“"
            if not mid and len(run) > 1 and not _ASCII_CODE.match(run[0]):
                run = run[1:]                                   # sentence-initial capital is grammar
            candidates = []
            if len(run) > 1 and not all(w.isupper() and not w.isascii() for w in run):
                candidates.append(" ".join(run))
            for w in run:
                if _ASCII_CODE.match(w) or (mid and _LATIN_NAME.match(w)):
                    candidates.append(w)
            for c in candidates:
                found.setdefault(c, set()).add(block.id)
            i = j + 1
    limit = max(4, len(outline) // 25)
    corpus = " ".join(b.text for b in outline.values())
    def proper(p: str) -> bool:                        # never written in another case (trung tâm, VTNET/VTNet)
        same = len(re.findall(rf"(?<!\w){re.escape(p)}(?!\w)", corpus))
        return same == len(re.findall(rf"(?<!\w){re.escape(p)}(?!\w)", corpus, re.I))
    names = {p for p, ids in found.items() if len(ids) <= limit and len(p) >= 3 and proper(p)}
    titles = loose(" ".join({t for b in outline.values() for t in b.path}))
    sections = {n for n in names if has_name(n, titles)}
    return names, sections


# ---------------------------------------------------------------- slide texts

@dataclass
class SlideText:
    text: str
    blocks: set[str]
    editorial: bool          # bound only to editorial IDs (no source block behind it)
    group_text: str          # visible text of the parent group (qualifier context)
    siblings: list["SlideText"] = field(default_factory=list)
    heading: bool = False
    x: float = 0.0
    y: float = 0.0


def lock_refs(lock: dict) -> dict[str, set[str]]:
    refs: dict[str, set[str]] = {}
    for fact in lock.get("facts", []):
        refs[fact["id"]] = {s["ref"] for s in fact.get("sources", [])}
    for item in lock.get("derived", []):
        refs[item["id"]] = set().union(*(refs.get(i, set()) for i in item.get("inputs", [])))
    for item in lock.get("conclusions", []):
        refs[item["id"]] = (set() if item.get("kind", "supported") == "editorial"
                            else set().union(*(refs.get(i, set()) for i in item.get("supports", []))))
    return refs


def slide_texts(svg: Path, refs: dict[str, set[str]]) -> list[SlideText]:
    root = ET.parse(svg).getroot()
    parent = {child: el for el in root.iter() for child in el}
    local = lambda el: el.tag.rsplit("}", 1)[-1]
    out: list[SlideText] = []
    by_group: dict[ET.Element, list[SlideText]] = {}

    def visible(el) -> bool:
        while el is not None:
            if (el.get("display") == "none" or el.get("visibility") == "hidden" or el.get("opacity") == "0"
                    or local(el) in ("defs", "metadata", "title", "desc")):
                return False
            el = parent.get(el)
        return True

    def inherited(el, attr) -> list[str]:
        while el is not None:
            if el.get(attr):
                return el.get(attr).split()
            el = parent.get(el)
        return []

    for el in root.iter():
        if local(el) != "text" or el.get("data-chrome") or not visible(el):
            continue
        text = " ".join(t.strip() for t in el.itertext() if t.strip())
        if not text:
            continue
        src, claims = set(inherited(el, "data-src")), inherited(el, "data-claims")
        blocks = src or set().union(set(), *(refs.get(c, set()) for c in claims))
        group = parent.get(el, root)
        group_text = " ".join(t.strip() for t in group.itertext() if t.strip())
        coord = lambda v: float(re.match(r"-?[\d.]+", v or "0").group() or 0) if re.match(r"-?[\d.]+", v or "") else 0.0
        item = SlideText(text, blocks, bool(claims or src) and not blocks, group_text,
                         heading=(el.get("font-weight") or "") in ("bold", "600", "700", "800", "900"),
                         x=coord(el.get("x")), y=coord(el.get("y")))
        out.append(item)
        by_group.setdefault(group, []).append(item)
    for members in by_group.values():
        for item in members:
            item.siblings = [m for m in members if m is not item]
    return out


# ---------------------------------------------------------------- rules

COUNT_RE = re.compile(r"\b(\d{1,2})\s+(đầu việc|nhiệm vụ|mốc|giải pháp|chương trình|kịch bản|hạng mục|sự vụ|sự cố|"
                      r"trụ cột|bước|nội dung|vấn đề|dự án|đơn vị|nhóm|lĩnh vực|tính năng|module|giai đoạn)\b")
META_RE = re.compile(r"^\s*(nguồn|source)\b", re.I)   # source footers describe the document, not facts
GENERIC_SECTION_WORDS = set("công tác kết quả thực hiện nhiệm vụ trọng tâm tiến độ đảm bảo tình hình chỉ tiêu "
                            "chủ yếu triển khai kế hoạch".split())


def finding(page: str, rule: str, level: str, item: SlideText, detail: str) -> dict:
    return {"page": page, "rule": rule, "level": level, "text": item.text[:160], "detail": detail,
            "blocks": sorted(item.blocks)}


@dataclass
class PageContext:
    outline: dict[str, Block]
    names: set[str]
    sections: set[str]
    doc_head: str
    children: dict[tuple, int]          # section path → number of blocks directly under it
    derived: set[str]                   # number keys of locked calculations on this page
    number_home: dict[str, set[str]]    # number key → source blocks that contain it
    counting_nouns: set[str]            # words that follow real ratios in the source (trạm, nhiệm, đảo …)
    name_blocks: dict[str, set[str]] = field(default_factory=dict)
    corpus: str = ""                    # the whole source, lower-cased (invented names)

    def blocks_with(self, name: str) -> set[str]:
        if name not in self.name_blocks:
            self.name_blocks[name] = {b.id for b in self.outline.values() if has_name(name, loose(b.context))}
        return self.name_blocks[name]


def period_ok(phrase: str, context_norm: str) -> bool:
    if phrase == "năm" and re.search(r"\b20\d\d\b", context_norm):
        return True                                       # a year in the section answers a bare "năm"
    if phrase in ("tuần này", "tháng này"):
        phrase = phrase.split(" ")[0]                     # "tuần này" = "trong tuần" of the report
    return period_in(phrase, context_norm)


def audit_page(page: str, items: list[SlideText], pc: PageContext) -> list[dict]:
    outline = pc.outline
    found: list[dict] = []
    page_blocks = set().union(set(), *(i.blocks for i in items))
    page_list = [outline[b] for b in sorted(page_blocks) if b in outline]
    blocks_ctx = norm(" ".join(b.context for b in page_list))          # what this page's sources say
    page_ctx = blocks_ctx + " " + pc.doc_head                         # + the document's own title lines
    page_numbers = number_set(blocks_ctx) | pc.derived
    head_numbers = number_set(pc.doc_head)
    title_text = norm(" ".join(i.text for i in items if i.heading)[:400])
    # ratios this page's source prints whole, and the chains (a/b/c) a slide might cut a pair out of
    source_pairs = {k for b in page_list for _, k in numbers(b.context) if k.count("/") == 1}
    source_rp = [rp for b in page_list for rp in ratio_percents(b.text)]
    printed = {(f"{p[0]}/{p[1]}", pct) for p, pct, _ in source_rp if len(p) == 2}     # the source's own a/b ~x%
    chains: dict[str, tuple[list[int], float | None, int]] = {}
    for b in page_list:
        for _, k in numbers(b.text):
            if k.count("/") >= 2 and not _date_like(k):
                parts = [int(x) for x in k.split("/")]
                rp = next(((pct, d) for p, pct, d in source_rp if p == parts), (None, 0))
                for a_, b_ in zip(parts, parts[1:]):
                    chains.setdefault(f"{a_}/{b_}", (parts, *rp))

    for item in items:
        if META_RE.match(item.text):
            continue
        blocks = [outline[b] for b in sorted(item.blocks) if b in outline]
        text_n, text_l = norm(item.text), loose(item.text)
        ctx = norm(" ".join(b.context for b in blocks)) if blocks else page_ctx
        ctx_l = loose(ctx)
        group_n = norm(item.group_text) + " " + title_text
        bound = bool(blocks)
        nums = numbers(item.text)
        clause_map = {key: [c for b in blocks for c in b.clauses() if key in number_set(c)] for _, key in nums}

        # 1. a period label the bound source never uses
        for _, phrase in periods(text_n):
            if period_ok(phrase, ctx):
                continue
            if not bound:
                level, why = "review", "editorial text"
            elif period_ok(phrase, blocks_ctx):
                level, why = "warn", "another source block of this page says it — bind the text to that block"
            else:
                level, why = "error", "no source block of this page says it"
            found.append(finding(page, "period-invented", level, item, f"'{phrase}' is not in the bound source: {why}"))
        # 2. a period label that belongs to another clause of the same source block
        spans = [(m.start(), m.end()) for m in PERIOD_RE.finditer(text_n)]
        nums_n = [(pos, key) for pos, key in numbers(text_n) if not any(a <= pos < b for a, b in spans)]
        for p_pos, phrase in periods(text_n):
            if not period_ok(phrase, ctx):
                continue
            near = [(n_pos, key) for n_pos, key in nums_n
                    if abs(n_pos - p_pos) <= 25 and not re.search(r"[,;·(|]", text_n[min(n_pos, p_pos):max(n_pos, p_pos)])]
            if not near:
                continue
            _, key = min(near, key=lambda n: abs(n[0] - p_pos))
            clauses = clause_map.get(key) or []
            general = norm(" ".join(" ".join(b.path) + " " + b.header for b in blocks))
            if clauses and not any(period_ok(phrase, c) for c in clauses) and not period_ok(phrase, general):
                found.append(finding(page, "period-other-clause", "error", item,
                                     f"'{phrase}' belongs to another clause than {key} in the source"))
        # 3. a percentage whose source clause carries a period label the slide group drops
        for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", item.text):
            key = num_key(m.group(1))
            clauses = clause_map.get(key) or []
            wanted = set()
            if len(clauses) == 1:
                at = re.search(rf"(?<![\d.,]){re.escape(m.group(1))}\s*%", clauses[0])
                if at:
                    tail = re.split(r"[,;(]", clauses[0][at.end():at.end() + 30])[0]
                    wanted = {p for _, p in periods(tail)}
            if wanted and not any(period_ok(p.split(" ")[0], group_n) for p in wanted):
                found.append(finding(page, "period-dropped", "warn", item,
                                     f"{m.group(1)}%: the source says '{', '.join(sorted(wanted))}' — keep it next to the number"))
        # 4. status words: the bound source must say them, and with the same hedge or negation
        for m in STATUS_RE.finditer(text_n):
            word = m.group()
            if hedge_before(text_n, m.start()):
                continue
            def hits_in(texts: list[str]) -> list[str | None]:
                return [hedge_before(t, x.start())
                        for t in texts for x in re.finditer(rf"\b{word}\b", t)]
            own = hits_in([norm(b.text) for b in blocks]) if bound else hits_in([page_ctx])
            if own:
                if all(own) and not any(h in group_n for h in own):
                    found.append(finding(page, "hedge-dropped", "error", item,
                                         f"'{word}' — the source says '{own[0]} {word}'"))
                continue
            if word == "vượt" and any(float(x.replace(",", ".")) > 100
                                     for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", item.group_text + " " + ctx)):
                continue                                  # "vượt" read straight off a >100% figure
            near = hits_in([norm(b.text) for b in page_list])
            if near and all(near):
                found.append(finding(page, "hedge-dropped", "error", item,
                                     f"'{word}' — this page's source only says '{near[0]} {word}'"))
            elif near:
                found.append(finding(page, "status-unbound", "warn", item,
                                     f"'{word}' is said by another source block of this page — bind the text to it"))
            else:
                strong = word not in ("hoàn thành", "hoàn thiện", "đạt", "tăng")
                sections = {tuple(b.path) for b in blocks}
                sibling = next((o.id for o in outline.values() if tuple(o.path) in sections
                                and re.search(rf"\b{word}\b", norm(o.text))), None)
                hint = (f" ({sibling} in the same section says it about another item — keep statuses with their own item)"
                        if sibling else "")
                found.append(finding(page, "status-unsourced", "error" if strong else "review", item,
                                     f"'{word}' is not said by the source this text is bound to{hint}"))
        # 5. a section name (place, project, unit) that the bound source does not contain
        shown = [n for n in pc.sections if has_name(n, text_l)]
        shown = [n for n in shown if not any(n != o and has_name(n, loose(o)) for o in shown)]   # longest only
        for name in shown:
            if has_name(name, ctx_l):
                continue
            homes = [outline[b] for b in sorted(pc.blocks_with(name))]
            same = [h for h in homes if any(h.path[-1:] == b.path[-1:] for b in blocks)]
            if not bound:
                level, why = "review", "editorial text names it"
            elif same or has_name(name, loose(blocks_ctx)):
                level, why = "warn", "the same section says it in another block — bind the text to that block"
            elif len({h.path[0] for h in homes if h.path}) >= 2:
                level, why = "warn", "a topic label used across the report — check it fits this text"
            else:
                where = " › ".join(homes[0].path[-2:]) if homes else "nowhere in the source"
                level, why = "error", f"it belongs to another section ({where})"
            found.append(finding(page, "name-unbound", level, item, f"'{name}' is not in the bound source: {why}"))
        # 6. a heading's section names must cover every number shown under it. Names that nest
        #    (TTKTKV3 › Cà Mau) all apply; peers (HNI · Trường Sa · APEC) apply one at a time.
        if item.heading and shown:
            leaves = [n for n in shown
                      if not any(o != n and pc.blocks_with(o) < pc.blocks_with(n) for o in shown)]
            def scoped_by_me(sib: SlideText) -> bool:
                above = [h for h in [item, *item.siblings]
                         if h is not sib and h.heading and h.y < sib.y - 1 and abs(h.x - sib.x) < 320]
                return bool(above) and min(above, key=lambda h: (sib.y - h.y, abs(h.x - sib.x))) is item
            for sib in (s_ for s_ in item.siblings if scoped_by_me(s_)):
                sblocks = [outline[b] for b in sib.blocks if b in outline]
                for _, key in numbers(sib.text):
                    owners = [b for b in sblocks if key in number_set(b.text)]
                    if not owners or any(has_name(n, loose(b.context)) for n in leaves for b in owners):
                        continue
                    leaf_words = [w for w in words(norm(owners[0].path[-1] if owners[0].path else ""))
                                  if w not in GENERIC_SECTION_WORDS]
                    hits = sum(w in words(text_n) for w in leaf_words)
                    if leaf_words and (hits >= 2 or hits / len(leaf_words) >= 0.4):
                        continue                          # the heading names that section in words
                    found.append(finding(page, "heading-scope", "error", sib,
                                         f"heading names '{' / '.join(leaves)}', but {key} comes from "
                                         f"'{' › '.join(owners[0].path[-2:])}' ({owners[0].id})"))
                    break
        # 7. a ratio shown without the noun that makes it a ratio (9/9 nhiệm vụ ≠ 9/9)
        for m in RATIO_RE.finditer(item.text):
            a_, b_ = int(m.group(1)), int(m.group(2))
            for block in blocks + [b for b in page_list if b not in blocks]:
                sm = re.search(rf"(\S*)\s*(?<![\w/]){re.escape(m.group(1))}\s*/\s*{re.escape(m.group(2))}"
                               rf"(?![\w/])\s*([^\W\d_]+)", block.text)
                if not sm:
                    continue
                noun, prev = sm.group(2).lower(), sm.group(1).lower()
                date_like = 1 <= a_ <= 31 and 1 <= b_ <= 12
                if (noun in STOPWORDS or prev in ("ngày", "trước", "từ", "đến", "hạn", "sau", "tới")
                        or (date_like and noun not in pc.counting_nouns)):
                    break                                    # a date in the source as well
                after = item.text[m.end():]
                if not after.strip():                     # the line may wrap into the next text
                    at = item.group_text.find(item.text)
                    after = item.group_text[at + len(item.text):] if at >= 0 else ""
                nxt = re.match(r"\s*([^\W\d_]+)", after)     # no punctuation between ratio and noun
                if not (nxt and nxt.group(1).lower() == noun):
                    found.append(finding(page, "ratio-noun", "error" if date_like else "warn", item,
                                         f"{a_}/{b_} is '{a_}/{b_} {sm.group(2)}' in the source" +
                                         (" — without it the reader sees a date" if date_like else "")))
                break
        # 8. numbers must come from the real source text (a lock's own wording is not a source)
        counts = {str(n) for n in pc.children.values()}
        for pos, key in nums:
            prefix = norm(item.text[:pos])
            if key in chains and key not in source_pairs and key not in pc.derived:
                # 8a. a pair cut out of a longer chain: the source's legend, not the position, says what pairs
                parts, pct, dec = chains[key]
                a_, b_ = (int(x) for x in key.split("/"))
                chain = "/".join(map(str, parts))
                if pct is None:
                    found.append(finding(page, "ratio-sliced", "warn", item,
                                         f"{key} is cut from {chain} in the source — its legend says which two "
                                         f"numbers pair; show the chain whole or the pair the legend gives"))
                elif not pct_matches(a_, b_, pct, dec):
                    right = [f"{x}/{y}" for i, x in enumerate(parts) for y in parts[i + 1:] if pct_matches(x, y, pct, dec)]
                    found.append(finding(page, "ratio-sliced", "error", item,
                                         f"{key} is cut from {chain} in the source, whose {pct:g}% is "
                                         f"{right[0] if right else 'not this pair'} — show that pair or the chain whole"))
                continue
            if key in page_numbers or (not bound and key in head_numbers) or ORDINAL_RE.search(prefix):
                continue
            if re.fullmatch(r"\d{1,2}", key) and (re.fullmatch(r"\s*0?\d{1,2}[.)]?\s*", item.text) or not bound):
                if not bound and key not in counts and not re.fullmatch(r"\s*0?\d{1,2}[.)]?\s*", item.text):
                    found.append(finding(page, "editorial-number", "error", item,
                                         f"{key} is not in any source block of this page"))
                continue
            homes = sorted(pc.number_home.get(key, set()))
            if homes and re.fullmatch(r"(0?[1-9]|1[0-2])/(19|20)\d\d", key):
                continue        # a period label (Quý 4/2026, 12/2026) the source prints — not a measured value
            if homes:
                found.append(finding(page, "number-unbound", "warn", item,
                                     f"{key} is in the source ({homes[0]}) but not in the blocks this page binds"))
            elif "/" in key and all(part in page_numbers for part in key.split("/")):
                found.append(finding(page, "number-recomposed", "review", item,
                                     f"{key} is built from two source numbers — check that the pairing is meaningful"))
            else:
                found.append(finding(page, "number-unsourced", "error" if bound else "review", item,
                                     f"{key} is not anywhere in the source text"))
        # 8b. a percentage shown next to a ratio must be that ratio's (same text, or the only pair of its group)
        pairs = [rp for rp in ratio_percents(item.text) if len(rp[0]) == 2]
        lone = [k for _, k in nums if k.count("/") == 1 and not _date_like(k)]
        if not pairs and len(lone) == 1 and "%" not in item.text:
            others = [s.text for s in item.siblings if "%" in s.text or any("/" in k for _, k in numbers(s.text))]
            if len(others) == 1 and re.fullmatch(r"[~≈(\s]*\d+(?:[.,]\d+)?\s*%\)?", others[0]):
                pairs = [rp for rp in ratio_percents(f"{item.text} {others[0]}") if len(rp[0]) == 2]
        for (a_, b_), pct, dec in pairs:
            key = f"{a_}/{b_}"
            if pct_matches(a_, b_, pct, dec) or key in chains:        # a cut chain is rule 8a's
                continue
            real = f"{a_ / b_ * 100:.{dec}f}".replace(".", ",") if b_ else "?"
            if (key, pct) in printed:
                found.append(finding(page, "ratio-percent", "review", item,
                                     f"the source itself prints {key} with {pct:g}%, but {key} = {real}% — "
                                     f"copied faithfully; tell the user the source disagrees with itself"))
            else:
                found.append(finding(page, "ratio-percent", "error", item,
                                     f"{pct:g}% is shown next to {key}, but {key} = {real}% — "
                                     f"pair the percentage with the ratio the source gives it"))
        # 9. "N items" must count what the source lists
        for m in COUNT_RE.finditer(text_n) if item.heading else ():
            n, noun = m.group(1), m.group(2)
            stated = [int(x) for x in re.findall(rf"\b(\d{{1,3}})\s+{noun}\b", page_ctx)]
            if int(n) in stated or (len(stated) > 1 and sum(stated) == int(n)):
                continue
            under = {pc.children.get(tuple(b.path), 0) for b in page_list} | {pc.children.get(tuple(b.path) + (b.title,), 0)
                                                                               for b in page_list if b.title}
            if int(n) not in under:
                found.append(finding(page, "count-mismatch", "error", item,
                                     f"'{n} {noun}': the source section lists {sorted(c for c in under if c)} items"))
        # 10. an item lifted from another part of the source into a page about one part
        peer_parts = [tuple(outline[b].path[:2]) for sib in item.siblings for b in sorted(sib.blocks)[:1]
                      if b in outline and outline[b].path]
        if blocks and len(peer_parts) >= 3:
            common = max(set(peer_parts), key=peer_parts.count)
            mine = {tuple(b.path[:2]) for b in blocks if b.path}
            if peer_parts.count(common) >= 0.75 * len(peer_parts) and mine and common not in mine:
                found.append(finding(page, "foreign-section", "review", item,
                                     f"from '{' › '.join(blocks[0].path[:3])}' while its list comes from "
                                     f"'{' › '.join(common)}'"))
        # 12. a code or name the source never writes (an invented unit, site or project abbreviation)
        for name in invented_codes(item.text, pc.corpus) if pc.corpus else ():
            found.append(finding(page, "name-invented", "error", item,
                                 f"'{name}' is nowhere in the source — use the source's own name or plain words"))
        # 11. long text with little overlap with its source → human review
        w = words(text_n)
        if len(w) >= 6:
            pool = set(words(ctx))
            share = sum(x in pool for x in w) / len(w)
            if share < 0.5:
                found.append(finding(page, "low-overlap", "review", item,
                                     f"only {share:.0%} of its content words appear in the bound source"))
    return found


# ---------------------------------------------------------------- project

def load_pages(project: Path) -> list[tuple[str, Path, dict[str, set[str]], set[str]]]:
    import content_check as cc
    locks = cc.load_contract(project) or []
    out = []
    for lock in locks:
        derived = number_set(" ".join(f"{d.get('value', '')} {d.get('text', '')}" for d in lock.get("derived", [])))
        out.append((lock["page"], project / "svg_output" / lock["svg"], lock_refs(lock), derived))
    return out


def audit(project: Path, pages: set[str] | None = None) -> tuple[list[dict], dict]:
    if not (project / "sources/source_index.json").exists():
        return [], {"outline": {}, "texts": {}}              # legacy project: nothing to trace to
    outline = build_outline(project)
    names, sections = entity_vocabulary(outline)
    doc_head = norm(" ".join(outline[b].text for b in sorted(outline)[:8]))
    children: dict[tuple, int] = {}
    for b in outline.values():
        children[tuple(b.path)] = children.get(tuple(b.path), 0) + 1
    number_home: dict[str, set[str]] = {}
    nouns: set[str] = set()
    for b in outline.values():
        exact = {k for _, k in numbers(b.context)}
        for key in exact | {part for k in exact if k.count("/") == 1 for part in k.split("/")}:
            number_home.setdefault(key, set()).add(b.id)
        for m in re.finditer(r"(?<![\w/])(\d{1,4})/(\d{1,4})(?![\w/])\s*([^\W\d_]+)", b.text):
            if not (1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12):
                nouns.add(m.group(3).lower())
    findings, texts = [], {}
    corpus = source_corpus(outline)
    for pid, svg, refs, derived in load_pages(project):
        if pages and pid not in pages or not svg.exists():
            continue
        try:
            items = slide_texts(svg, refs)
        except ET.ParseError:      # empty or half-written: page_plan check reports it
            continue
        texts[pid] = items
        pc = PageContext(outline, names, sections, doc_head, children, derived, number_home, nouns - STOPWORDS,
                         corpus=corpus)
        findings += audit_page(pid, items, pc)
    return findings, {"outline": outline, "texts": texts}


SEVERITY = {"error": 0, "warn": 1, "review": 2}
REVIEW_FIELDS = {   # content_check review booleans and the rules that put each in doubt
    "source_meaning": ("low-overlap", "foreign-section", "name-unbound", "name-invented", "status-unsourced",
                       "status-unbound"),
    "numbers_units": ("number-unsourced", "number-unbound", "number-recomposed", "ratio-noun", "editorial-number",
                      "ratio-sliced", "ratio-percent"),
    "scope_period_status": ("period-invented", "period-other-clause", "period-dropped", "hedge-dropped", "heading-scope"),
    "titles_conclusions": ("count-mismatch",),
}


def review_table(project: Path, pages: set[str] | None = None, everything: bool = False) -> str:
    """Rows the main agent must judge: every flagged slide text next to the source clause it is
    bound to. Unflagged claim rows were matched against the source mechanically; `--all` adds them."""
    findings, data = audit(project, pages)
    outline, flagged = data["outline"], {}
    for f in findings:
        flagged.setdefault((f["page"], f["text"]), []).append(f)
    rows = ["| Trang | Cờ | Trên slide | Nguồn (mục › vế chứa số) | Vì sao |", "|---|---|---|---|---|"]
    for pid, items in data["texts"].items():
        for item in items:
            hits = sorted(flagged.get((pid, item.text[:160]), []), key=lambda f: SEVERITY[f["level"]])
            claim = bool(NUM_RE.search(item.text) or STATUS_RE.search(norm(item.text)))
            if not hits and not (everything and claim):
                continue
            blocks = [outline[b] for b in sorted(item.blocks) if b in outline]
            nums = number_set(item.text)
            src = []
            for b in blocks[:2]:
                clause = next((c for c in b.raw_clauses() if nums & number_set(c)), b.raw_clauses()[0])
                src.append(f"{' › '.join(b.path[-1:])} › {clause[:110]}")
            flags = ", ".join(dict.fromkeys(f"{f['level']}:{f['rule']}" for f in hits))
            why = hits[0]["detail"][:120] if hits else ""
            rows.append(f"| {pid} | {flags} | {item.text[:90]} | {' ‖ '.join(src) or '(editorial — no source)'} | {why} |")
    return "\n".join(rows) + "\n"


def draft_review(project: Path, reviewer: str, charts_file: Path | None = None) -> dict:
    """A review draft for `content_check.py --record-review`, built from the audit. Errors fail the
    page (fix the slide, then draft again). Warnings and review rows are the review table the main
    agent has read; they stay in the notes as judged. Chart notes come from the sub-agents'
    `verify-charts:` lines collected in `charts_file`; a chart without one fails its page."""
    import content_check as cc
    findings, data = audit(project)
    charts = json.loads(charts_file.read_text(encoding="utf-8")) if charts_file and charts_file.exists() else {}
    receipt_path = project / "content_review.json"          # resume: chart notes of byte-identical pages carry over
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    import hashlib
    by_page: dict[str, list[dict]] = {}
    for f in findings:
        by_page.setdefault(f["page"], []).append(f)
    draft = {}
    for lock in cc.load_contract(project) or []:
        pid, hits = lock["page"], by_page.get(lock["page"], [])
        errors = [f for f in hits if f["level"] == "error"]
        judged = list(dict.fromkeys(f"{f['level']}:{f['rule']} '{f['text'][:50]}'" for f in hits if f["level"] != "error"))
        claims = sum(bool(NUM_RE.search(i.text) or STATUS_RE.search(norm(i.text))) for i in data["texts"].get(pid, []))
        notes = (f"fact_check matched {claims} claim texts against their source blocks (numbers, period labels, "
                 f"section names, statuses, ratios, counts)")
        if errors:
            notes += "; OPEN ERRORS: " + "; ".join(dict.fromkeys(f"{f['rule']} '{f['text'][:50]}'" for f in errors))
        if judged:
            notes += "; judged in the review table: " + "; ".join(judged)
        entry = {"status": "fail" if errors else "pass", "reviewer": reviewer, "notes": notes}
        for name, rules in REVIEW_FIELDS.items():
            entry[name] = not any(f["rule"] in rules for f in errors)
        entry["required_content"] = True          # content_check --stage svg enforces `required`
        entry["visual_encoding"] = True
        viz = [v["id"] for v in lock.get("visualizations", []) if v.get("template") != "none"]
        svg = project / "svg_output" / lock["svg"]
        same_bytes = svg.exists() and receipt.get("hashes", {}).get(f"svg_output/{lock['svg']}") == \
            hashlib.sha256(svg.read_bytes()).hexdigest()
        old = receipt.get("pages", {}).get(pid, {}).get("charts", {}) if same_bytes else {}
        entry["charts"] = {v: charts.get(pid, {}).get(v) or old.get(v, "") for v in viz}
        if any(not note for note in entry["charts"].values()):
            entry["status"], entry["visual_encoding"] = "fail", False
            entry["notes"] += "; chart note missing — paste the page's verify-charts line"
        draft[pid] = entry
    return draft


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("audit", "table", "outline", "draft-review"))
    parser.add_argument("project", type=Path)
    parser.add_argument("--pages", help="comma list of page IDs (P03) or numbers")
    parser.add_argument("--all", action="store_true", help="table: include unflagged claim rows")
    parser.add_argument("--reviewer", help="draft-review: the reviewing model's real identifier")
    parser.add_argument("--charts", type=Path, help="draft-review: JSON {page: {viz_id: verify-charts line}}")
    parser.add_argument("--out", type=Path, help="draft-review: output file (default reviews/draft.json)")
    args = parser.parse_args(argv)
    project = args.project.resolve()
    pages = ({p if p.upper().startswith("P") else f"P{int(p):02d}" for p in args.pages.split(",")}
             if args.pages else None)
    if args.command == "outline":
        for block in build_outline(project).values():
            print(f"{block.id} | {' › '.join(block.path)} | {block.text[:100]}")
        return 0
    if args.command == "table":
        print(review_table(project, pages, args.all), end="")
        return 0
    if args.command == "draft-review":
        if not args.reviewer:
            parser.error("draft-review needs --reviewer <model id>")
        out = args.out or project / "reviews" / "draft.json"
        out.parent.mkdir(exist_ok=True)
        draft = draft_review(project, args.reviewer, args.charts)
        out.write_text(json.dumps(draft, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        failing = [p for p, e in draft.items() if e["status"] != "pass"]
        print(json.dumps({"draft": str(out), "pass": len(draft) - len(failing), "fix_or_justify": failing},
                         ensure_ascii=False))
        return 1 if failing else 0
    findings, _ = audit(project, pages)
    print(json.dumps(findings, ensure_ascii=False, indent=1))
    return 1 if any(f["level"] == "error" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
