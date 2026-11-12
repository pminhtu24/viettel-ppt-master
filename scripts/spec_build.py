#!/usr/bin/env python3
"""Strategist tools: read the source once, pick charts, write a short page plan; the script writes
design_spec.md, spec_lock.md and every content lock.

  python3 spec_build.py source  <project>          the source, once: every block with its ID under its section
  python3 spec_build.py catalog [--write]          every chart/structure template, one line each, by family
  python3 spec_build.py build   <project>          plan.md → design_spec.md + spec_lock.md (+ the plan gate)

The plan (`<project>/plan.md`, format in references/page-plan.md) names, per slide, the source blocks it
shows and, for data charts, the exact source number behind each mark. Quotes, index hashes, SVG names,
fact fields and the fixed Viettel sections are filled in here, so they cannot be mistyped.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import content_check as cc                      # noqa: E402
import fact_check as fc                         # noqa: E402
from page_plan import icon_report, slugify, SKILL_DIR   # noqa: E402
from source_index import read_blocks, sha256    # noqa: E402

CATALOG = json.loads((SKILL_DIR / "templates/charts/charts_index.json").read_text(encoding="utf-8"))["charts"]
LAYOUTS = SKILL_DIR / "templates/layouts/viettel_default"
BACKGROUNDS = {i["id"] for i in json.loads((LAYOUTS / "backgrounds/backgrounds_index.json")
                                           .read_text(encoding="utf-8"))["items"]}
TYPOGRAPHY = {   # viettel_default §IV starting slots
    "dense": {"body": 20, "title": 32, "subtitle": 26, "annotation": 16, "subtitle_strip": 17, "card_header": 18,
              "card_subhead": 16, "card_body": 16, "badge": 14, "hero_number": 40, "cover_title": 60},
    "standard": {"body": 24, "title": 36, "subtitle": 30, "annotation": 18, "hero_number": 48, "cover_title": 60},
}
DIMENSION_KEYS = ("category", "series", "period", "status", "entity")
CALC_OPS = ("percent", "ratio", "sum", "difference", "remainder", "percentage_points")
FAMILY_ORDER = ["structure", "kpi", "progress", "comparison", "time", "milestones", "composition", "pareto",
                "funnel", "waterfall", "flow", "matrix", "radar", "distribution", "xy", "schedule"]


# ---------------------------------------------------------------- source

class Source:
    def __init__(self, project: Path):
        self.project = project
        self.outline = fc.build_outline(project)
        self.raw = read_blocks(project)
        self.ids = list(self.outline)
        prefixes = {i.split("-B")[0] for i in self.ids}
        self.short = len(prefixes) == 1
        self.by_short = {self.label(i): i for i in self.ids}

    def label(self, block_id: str) -> str:
        return block_id.split("-", 1)[1] if self.short else block_id

    def resolve(self, ref: str) -> str:
        ref = ref.strip()
        if ref in self.outline:
            return ref
        if ref in self.by_short:
            return self.by_short[ref]
        raise KeyError(ref)

    def expand(self, spec: str) -> list[str]:
        """`B0011-B0014, B0020` → full IDs in source order."""
        out: list[str] = []
        for part in (p.strip() for p in spec.split(",") if p.strip()):
            m = re.fullmatch(r"((?:S[0-9a-f]+-)?B\d+)\s*-\s*((?:S[0-9a-f]+-)?B\d+)", part)
            if m:
                i, j = self.ids.index(self.resolve(m.group(1))), self.ids.index(self.resolve(m.group(2)))
                chosen = self.ids[min(i, j):max(i, j) + 1]
            else:
                chosen = [self.resolve(part)]
            out += [x for x in chosen if x not in out]
        return out


def cmd_source(project: Path) -> int:
    """The whole source once: sections as ▸ lines, every block as `ID · text`, table columns once per table."""
    src = Source(project)
    header = None
    for bid in src.ids:
        b = src.outline[bid]
        pad = "  " * min(len(b.path), 6)
        if "<table" in src.raw[bid].lower():
            print(f"{pad}{src.label(bid)} [bảng — các hàng ở dưới]")
            continue
        if b.header and b.header != header:
            print(f"{pad}  cột: {b.header}")
        header = b.header
        if b.title:
            print(f"{pad}▸ {src.label(bid)} {b.title}")
        else:
            print(f"{pad}{src.label(bid)} · {b.text}")
    return 0


# ---------------------------------------------------------------- catalog

def catalog_text() -> str:
    groups: dict[str, list[str]] = {}
    for key, entry in CATALOG.items():
        req = entry["data_requirements"]
        roles = "/".join(req["roles"])
        dims = "/".join(dict.fromkeys(req["dimensions"])) or "—"
        data = "" if req["family"] == "structure" else f" *(data: {roles}; {dims})*"
        groups.setdefault(req["family"], []).append(f"- `{key}` — {entry['summary']}{data}")
    lines = ["# Chart and structure catalog", "",
             f"All {len(CATALOG)} templates in `templates/charts/`, grouped by the data they need. A `structure` "
             "template takes source blocks (no numbers); every other family takes `- data:` lines naming the source "
             "number behind each mark (references/page-plan.md). Generated from charts_index.json by "
             "`spec_build.py catalog --write`.", ""]
    for family in sorted(groups, key=lambda f: FAMILY_ORDER.index(f) if f in FAMILY_ORDER else 99):
        lines += [f"## {family}", "", *groups[family], ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- plan

def parse_plan(text: str) -> dict:
    header: dict[str, str] = {}
    pages: list[dict] = []
    part = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if m := re.match(r"^##\s+(?!#)(.+)$", line):
            part = m.group(1).strip()
        elif m := re.match(r"^###\s+P(\d{1,3})\s+(.+)$", line):
            pages.append({"num": int(m.group(1)), "title": m.group(2).strip(), "part": part,
                          "keys": {}, "data": [], "calc": [], "line": line})
        elif m := re.match(r"^\s*-\s+([a-z_]+):\s*(.*)$", line):
            key, value = m.group(1), m.group(2).strip()
            if not pages:
                header[key] = value
            elif key in ("data", "calc"):
                pages[-1][key].append(value)
            else:
                pages[-1]["keys"][key] = value
    return {"header": header, "pages": pages}


def to_json_number(value: Decimal):
    return int(value) if value == value.to_integral_value() else float(value)


def number_token(block_text: str, wanted: str) -> tuple[str, int] | None:
    """The token as written in the block (and its position) whose canonical form equals `wanted`."""
    key = fc.num_key(wanted.rstrip("%"))
    for m in fc.NUM_RE.finditer(re.sub(r"(?<=[^\W\d_])/(?=\d)", " ", block_text)):
        if fc.num_key(m.group()) == key:
            return m.group(), m.start()
    for m in fc.NUM_RE.finditer(re.sub(r"(?<=[^\W\d_])/(?=\d)", " ", block_text)):
        offset = m.start()
        for part in m.group().split("/"):                  # 140 inside 140/457
            if fc.num_key(part) == key:
                return part, offset
            offset += len(part) + 1
    return None


def lead(block: fc.Block) -> str:
    m = re.match(r"^(.{3,80}?):\s", block.text)
    return (m.group(1) if m else (block.path[-1] if block.path else block.text[:60])).strip(" :*")


class PageBuilder:
    def __init__(self, src: Source, page: dict, errors: list[str]):
        self.src, self.page, self.errors = src, page, errors
        self.pid = f"P{page['num']:02d}"
        self.facts: list[dict] = []
        self.by_id: dict[str, dict] = {}

    def err(self, message: str) -> None:
        self.errors.append(f"{self.pid}: {message}")

    def block_fact(self, bid: str) -> dict:
        b, raw = self.src.outline[bid], self.src.raw[bid]
        quote = raw if len(raw) <= 160 else raw[:raw.rfind(" ", 0, 120) or 120]   # a locator; `text` carries the block
        found = {p for _, p in fc.periods(fc.norm(" ".join([b.text, *b.path])))}
        fact = {"id": self.src.label(bid).replace("-", "_"), "text": (f"{b.header} | " if b.header else "") + b.text,
                "entity": lead(b), "unit": "n/a", "period": ", ".join(sorted(found)) or "n/a",
                "scope": b.path[-1] if b.path else "n/a", "section": " › ".join(b.path), "status": "reported",
                "sources": [{"ref": bid, "quote": quote}]}
        return self.add(fact)

    def add(self, fact: dict) -> dict:
        if fact["id"] in self.by_id:
            n = 2
            while f"{fact['id']}_{n}" in self.by_id:
                n += 1
            fact["id"] = f"{fact['id']}_{n}"
        self.facts.append(fact)
        self.by_id[fact["id"]] = fact
        return fact

    def number_fact(self, bid: str, role: str, wanted: str, dims: dict[str, str]) -> dict | None:
        b = self.src.outline[bid]
        hit = number_token(b.text, wanted)
        if not hit:
            self.err(f"{self.src.label(bid)}: '{wanted}' is not a number of that block — copy it from `spec_build.py source`")
            return None
        raw, pos = hit
        after = re.sub(r"^/\d+(?:[.,]\d+)*", "", b.text[pos + len(raw):])   # 140/457 GP: both count GP
        unit = "%" if after.lstrip().startswith("%") else (re.match(r"\s*([^\W\d_][\w]*)", after) or [None, "n/a"])[1]
        clause = next((c for c in b.clauses() if fc.num_key(raw) in fc.number_set(c)), fc.norm(b.text))
        period = dims.get("period") or ", ".join(sorted({p for _, p in fc.periods(clause)})) or "n/a"
        category = dims.get("category") or lead(b)
        fact = {"id": f"{self.src.label(bid).replace('-', '_')}_{role}", "text": f"{category}: {raw}{'%' if unit == '%' else ' ' + unit}",
                "entity": dims.get("entity") or category, "unit": unit, "period": period,
                "scope": b.path[-1] if b.path else "n/a", "status": dims.get("status") or "reported",
                "category": category, "series": dims.get("series") or "A",
                "sources": [{"ref": bid, "quote": self.quote_around(bid, raw)}]}
        if re.fullmatch(r"\d+(?:[.,]\d+)?[KkMB]", wanted) or "/" in raw:
            fact.update(value=raw, numeric=False)
        else:
            for locale in ("vi", "en"):
                try:
                    fact.update(value=to_json_number(cc.parse_source_number(raw, locale)), raw=raw, locale=locale)
                    break
                except ValueError:
                    continue
            else:
                self.err(f"{self.src.label(bid)}: cannot read '{raw}' as a number")
                return None
        return self.add(fact)

    def quote_around(self, bid: str, raw: str) -> str:
        """A short exact excerpt of the block that contains the number token."""
        text = self.src.raw[bid]
        at = next((m.start() for m in re.finditer(re.escape(raw), text)), 0)
        start = text.rfind(" ", 0, max(0, at - 50)) + 1 if at > 50 else 0
        end = text.find(" ", at + len(raw) + 40)
        return text[start:end if end > 0 else len(text)]

    def build(self) -> tuple[dict, dict]:
        keys, page = self.page["keys"], self.page
        try:
            blocks = self.src.expand(keys.get("blocks", ""))
            optional = self.src.expand(keys.get("optional", "")) if keys.get("optional") else []
        except (KeyError, ValueError) as exc:
            self.err(f"unknown block {exc}")
            return {}, {}
        if not blocks and keys.get("rhythm", "dense") == "dense":
            self.err("no `- blocks:` line (only anchor/breathing pages — cover, chapter, ending — may show no source block)")
        shown = [self.block_fact(b) for b in blocks]
        self.page["_shown"] = len(shown)
        for b in optional:
            if b not in blocks:
                self.block_fact(b)
        template = keys.get("template", "none").strip() or "none"
        visualizations, derived = [], []
        if template != "none":
            if template not in CATALOG:
                self.err(f"template '{template}' is not in the catalog")
            else:
                visualizations = [self.visualization(template, shown)]
        for line in page["calc"]:
            if item := self.calculation(line):
                derived.append(item)
        title_fact_ids = [f["id"] for f in shown]
        title = ({"id": "c_title", "kind": "supported", "text": page["title"], "supports": title_fact_ids,
                  "reason": "Slide title summarising the source blocks of this slide"} if title_fact_ids else
                 {"id": "c_title", "kind": "editorial", "text": page["title"], "supports": [],
                  "reason": "Structural page title (cover, chapter or ending) showing no source fact"})
        conclusions = [
            title,
            {"id": "c_label", "kind": "editorial", "text": "Nhãn trình bày", "supports": [],
             "reason": "Neutral structural labels (section names, column heads, badges taken from the bound blocks)"},
            {"id": "c_src", "kind": "editorial", "text": "Nguồn tài liệu", "supports": [],
             "reason": "Source footer naming the document"},
        ]
        lock = {"page": self.pid, "svg": f"{page['num']:02d}_{slugify(page['title'])}.svg",
                "source_index_sha256": sha256(self.src.project / "sources/source_index.json"),
                "facts": self.facts, "derived": derived, "conclusions": conclusions, "unresolved": [],
                "visualizations": visualizations, "required": ["c_title", *title_fact_ids]}
        maps = {"page_rhythm": keys.get("rhythm", "dense"), "page_layouts": keys.get("layout", ""),
                "page_backgrounds": keys.get("background", ""), "page_charts": template if template != "none" else ""}
        return lock, maps

    def visualization(self, template: str, shown: list[dict]) -> dict:
        req = CATALOG[template]["data_requirements"]
        why = self.page["keys"].get("why", "")
        observations: list[dict] = []
        if req["family"] in ("structure", "milestones") and not self.page["data"]:
            observations = [{"value": f["id"]} for f in shown]
            if req["family"] == "milestones":
                for f in shown:
                    dates = [k for _, k in fc.numbers(f["text"]) if k.count("/") >= 1]
                    f["period"] = dates[0] if dates else f["period"]
        for line in self.page["data"]:
            parts = shlex.split(line)
            if not parts:
                continue
            try:
                bid = self.src.resolve(parts[0])
            except KeyError:
                self.err(f"data line names unknown block {parts[0]}")
                continue
            pairs = dict(p.split("=", 1) for p in parts[1:] if "=" in p)
            unknown = [k for k in pairs if k not in req["roles"] and k not in DIMENSION_KEYS]
            if unknown:
                self.err(f"{template} has roles {req['roles']}; '{', '.join(unknown)}' is not one of them")
            dims = {k: v for k, v in pairs.items() if k in DIMENSION_KEYS}
            row = {}
            for role in req["roles"]:
                if role not in pairs:
                    self.err(f"{template} needs '{role}=' on every data line ({parts[0]})")
                    continue
                if fact := self.number_fact(bid, role, pairs[role], dims):
                    row[role] = fact["id"]
            if row:
                observations.append(row)
        if req["family"] not in ("structure", "milestones") and not self.page["data"]:
            self.err(f"{template} is a {req['family']} chart: add one `- data:` line per mark")
        if req["semantic_checks"] and not why:
            self.err(f"{template} needs a `- why:` line: why the source supports {', '.join(dict.fromkeys(req['semantic_checks']))}")
        refs = [f["id"] for f in self.facts]
        viz = {"id": "v1", "template": template, "observations": observations,
               "evidence": {c: {"refs": refs, "reason": why} for c in dict.fromkeys(req["semantic_checks"])}}
        if req["family"] in ("composition", "pareto") or template == "stacked_area_chart":
            self.err(f"{template} needs explicit wholes (`totals`), which plan build does not write yet — "
                     "pick a comparison/progress template or write this page's lock by hand")
        return viz

    def calculation(self, line: str) -> dict | None:
        m = re.match(r"^(\w+)\s+(\w+)\s+(.+)$", line.strip())
        if not m or m.group(2) not in CALC_OPS:
            self.err(f"calc line '{line}': use `<id> <{'|'.join(CALC_OPS)}> <block>:<number> <block>:<number>`")
            return None
        cid, op = m.group(1), m.group(2)
        inputs = []
        for token in m.group(3).split():
            ref, _, wanted = token.partition(":")
            try:
                bid = self.src.resolve(ref)
            except KeyError:
                self.err(f"calc {cid}: unknown block {ref}")
                return None
            if fact := self.number_fact(bid, f"in{len(inputs) + 1}", wanted, {}):
                inputs.append(fact)
        if len(inputs) < 1:
            return None
        item = {"id": cid, "inputs": [f["id"] for f in inputs], "operation": op, "decimals": 1, "value": 0,
                "unit": "%" if op in ("percent",) else ("pp" if op == "percentage_points" else inputs[0]["unit"]),
                "entity": inputs[0]["entity"], "period": inputs[0]["period"], "scope": inputs[0]["scope"],
                "status": "derived", "meaning": self.page["keys"].get("why") or f"{op} of the listed source numbers",
                "compatibility": "inputs taken from the same source section"}
        args = [cc.number(f["value"]) for f in inputs]
        if op in ("percent", "ratio"):
            if len(args) != 2 or args[1] == 0:
                self.err(f"calc {cid}: {op} needs two inputs, the second not zero")
                return None
            exact = args[0] / args[1] * (100 if op == "percent" else 1)
        elif op == "sum":
            exact = sum(args)
        elif len(args) == 2:
            exact = args[0] - args[1]
        else:
            self.err(f"calc {cid}: {op} needs two inputs")
            return None
        rounded = exact.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        item["value"] = to_json_number(rounded)
        item["text"] = f"{op}({', '.join(f['text'] for f in inputs)}) = {str(rounded).replace('.', ',')}"
        return item


# ---------------------------------------------------------------- writers

def spec_lock_text(plan: dict, maps: dict[str, dict[str, str]], icons: tuple[str, list[str]]) -> str:
    h = plan["header"]
    density = "standard" if h.get("density", "dense").startswith("standard") else "dense"
    lib, names = icons
    out = ["# Execution Lock", "", "## canvas", "", "- viewBox: 0 0 1280 720", "- format: PPT 16:9", "",
           "## brand", "", "- profile: viettel_default", "- deep_blue_scope: chart_diagram_icon_catalog_background_only", "",
           "## colors", "", "- bg: #FFFFFF", "- surface: #F2F2F2", "- primary: #EE0033", "- chart_deep_blue: #12436D",
           "- text: #000000", "- text_secondary: #44494D", "- text_tertiary: #999999", "- border: #E6E6E6",
           "- success: #28A197", "- warning: #F46A25", "- chart_neutral: #6B7280", "",
           "## typography", "", '- font_family: "FS Magistral"',
           *[f"- {k}: {v}" for k, v in TYPOGRAPHY[density].items()], "",
           "## text_fit", "", "- card_padding: 20", "- chart_label_max_chars: 24", "- card_body_max_lines: 3",
           "- kpi_caption_max_lines: 2", "- footer_max_chars: 90", "- require_wrap_contract: true",
           "- title_zone_bottom: 255", ""]
    if lib:
        out += ["## icons", "", f"- library: {lib}", *(["- stroke_width: 2"] if lib == "tabler-outline" else []),
                f"- inventory: {', '.join(names)}", ""]
    for section in ("page_rhythm", "page_backgrounds", "page_layouts", "page_charts"):
        rows = [f"- {pid}: {value}" for pid, value in maps[section].items() if value]
        if rows:
            out += [f"## {section}", "", *rows, ""]
    mode = h.get("mode", "parallel")
    out += ["## execution", "", f"- generation_mode: {mode}", "- max_subagents: 6", "- max_pages_per_subagent: 6",
            "- anchor: main", "", "## forbidden", "", "- Mixing icon libraries", "- rgba()",
            "- `<style>`, `class`, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>`, `<symbol>`+`<use>`",
            "- `<g opacity>` (set opacity on each child element individually)",
            "- HTML named entities in text (`&nbsp;`, `&mdash;` …) — write raw Unicode; escape `& < > \" '` in XML", ""]
    return "\n".join(out)


def design_spec_text(plan: dict, built: list[tuple[dict, dict, dict]], src: Source) -> str:
    h = plan["header"]
    density = "standard" if h.get("density", "dense").startswith("standard") else "dense"
    body = TYPOGRAPHY[density]["body"]
    title = h.get("title", "Deck")
    out = [f"# {title} - Design Spec", "", "content_contract: 1", "",
           "## I. Project Information", "", "| Property | Value |", "| --- | --- |",
           f"| Project | {title} |", "| Canvas | PPT 16:9 (1280×720) |", f"| Page count | {len(built)} |",
           f"| Audience | {h.get('audience', 'n/a')} |", f"| Purpose | {h.get('purpose', 'n/a')} |",
           f"| Style | {h.get('style', 'n/a')} |", f"| Generation mode | {h.get('mode', 'parallel')} |", "",
           "## II. Canvas Specification", "", "PPT 16:9, viewBox `0 0 1280 720`, Viettel content safe area "
           "(templates/design_spec.md §II).", "",
           "## III. Visual Theme", "", "Locked Viettel light theme: red `#EE0033`, white/approved-gray surfaces, "
           "dark-neutral text; deep blue `#12436D` only for chart/diagram/icon marks and cataloged backgrounds "
           "(templates/design_spec.md §III).", "",
           "## IV. Typography System", "", f"FS Magistral Book/Medium/Bold (static TTF faces). {density.title()} "
           f"profile, body {body}px; sizes in spec_lock.md `typography` (templates/design_spec.md §IV).", "",
           "## V. Layout Principles", "", "Viettel shell, page rhythm per spec_lock.md `page_rhythm`, text-fit "
           "contract of executor-base.md §2.2 (templates/design_spec.md §V).", "",
           "## VI. Icon Usage Specification", "", f"Library: {h.get('icons', 'none')}.", "",
           "## VII. Visualization Reference List", "", "| Page | Template | Path | Why |", "| --- | --- | --- | --- |"]
    for page, lock, maps in built:
        if maps.get("page_charts"):
            out.append(f"| P{page['num']:02d} | {maps['page_charts']} | templates/charts/{maps['page_charts']}.svg | "
                       f"{page['keys'].get('why', '')} |")
    out += ["", "## VIII. Image Resource List", "", h.get("images", "none") + ".", "", "## IX. Content Outline", ""]
    part = None
    for page, lock, maps in built:
        if page["part"] != part:
            part = page["part"]
            if part:
                out += [f"### {part if part.lower().startswith('part') else 'Part: ' + part}", ""]
        k = page["keys"]
        out += [f"#### Slide {page['num']:02d} - {page['title']}", ""]
        for label, key in (("Job", "job"), ("Template", "template"), ("Blocks", "blocks"), ("Optional", "optional")):
            if k.get(key):
                out.append(f"- **{label}**: {k[key]}")
        out += ["", "```content-lock", json.dumps(lock, ensure_ascii=False, separators=(",", ":")), "```", ""]
    out += ["## X. Technical Constraints Reminder", "", "Native-PPTX-safe SVG only (shared-standards.md); Viettel "
            "chrome added by apply_brand_chrome.py; every visible text bound with data-claims "
            "(content-grounding §4).", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- build

def cmd_build(project: Path, dry_run: bool = False) -> int:
    plan_path = project / "plan.md"
    if not plan_path.exists():
        print(json.dumps({"error": f"write {plan_path} first (references/page-plan.md)"}))
        return 1
    plan = parse_plan(plan_path.read_text(encoding="utf-8"))
    src = Source(project)
    errors: list[str] = []
    warnings: list[str] = []
    built = []
    maps: dict[str, dict[str, str]] = {k: {} for k in ("page_rhythm", "page_backgrounds", "page_layouts", "page_charts")}
    nums = [p["num"] for p in plan["pages"]]
    if nums != list(range(1, len(nums) + 1)):
        errors.append(f"slides must be numbered P01…P{len(nums):02d} in order; got {', '.join(f'P{n:02d}' for n in nums)}")
    for page in plan["pages"]:
        lock, page_maps = PageBuilder(src, page, errors).build()
        if not lock:
            continue
        pid = lock["page"]
        for section, value in page_maps.items():
            maps[section][pid] = value
        if page_maps["page_rhythm"] not in ("anchor", "dense", "breathing"):
            errors.append(f"{pid}: rhythm must be anchor, dense or breathing")
        if page_maps["page_layouts"] and not (LAYOUTS / f"{page_maps['page_layouts']}.svg").exists():
            errors.append(f"{pid}: layout '{page_maps['page_layouts']}' is not a viettel_default template "
                          f"({', '.join(sorted(p.stem for p in LAYOUTS.glob('*.svg')))})")
        if page_maps["page_backgrounds"] and page_maps["page_backgrounds"] not in BACKGROUNDS:
            errors.append(f"{pid}: background '{page_maps['page_backgrounds']}' is not in backgrounds_index.json")
        if page_maps["page_backgrounds"] and page_maps["page_rhythm"] == "dense":
            warnings.append(f"{pid}: backgrounds belong to cover, chapter and ending pages only")
        count = fc.COUNT_RE.search(fc.norm(page["title"]))
        if count and int(count.group(1)) != page.get("_shown"):
            warnings.append(f"{pid}: title says '{count.group()}' but the slide lists {page.get('_shown')} blocks")
        built.append((page, lock, page_maps))
    # icons
    lib, names = "", []
    if (spec := plan["header"].get("icons", "")) and spec.lower() != "none":
        lib, _, rest = spec.partition(":")
        lib, names = lib.strip(), [n.strip() for n in rest.split(",") if n.strip()]
        report = icon_report([lib], names)
        if isinstance(report, str):
            errors.append(report)
        elif report:
            errors += [f"icon '{n}' is not in {lib}: use one of {', '.join(c) or '(none similar — drop it)'}"
                       for n, c in report.items()]
    # coverage: source sections with numbers that no slide shows
    used = {s["ref"] for _, lock, _ in built for f in lock["facts"] for s in f["sources"]}
    uncovered: dict[str, int] = {}
    for bid, b in src.outline.items():
        if bid not in used and fc.NUM_RE.search(b.text) and not b.title:          # numbers or dates
            key = " › ".join(b.path[-2:]) or "(top)"
            uncovered[key] = uncovered.get(key, 0) + 1
    if errors:
        print(json.dumps({"errors": errors, "warnings": warnings}, ensure_ascii=False, indent=1))
        return 1
    if dry_run:
        print(json.dumps({"ok": True, "slides": len(built), "warnings": warnings,
                          "uncovered_sections_with_numbers": uncovered}, ensure_ascii=False, indent=1))
        return 0
    (project / "design_spec.md").write_text(design_spec_text(plan, built, src), encoding="utf-8")
    (project / "spec_lock.md").write_text(spec_lock_text(plan, maps, (lib, names)), encoding="utf-8")
    gate = []
    try:
        cc.validate(project, stage="plan")
    except (ValueError, KeyError, TypeError) as exc:
        gate.append(str(exc))
    print(json.dumps({"written": ["design_spec.md", "spec_lock.md"], "slides": len(built), "warnings": warnings,
                      "uncovered_sections_with_numbers": uncovered, "plan_gate": gate or "pass"},
                     ensure_ascii=False, indent=1))
    return 1 if gate else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("source", "catalog", "build"))
    parser.add_argument("project", type=Path, nargs="?")
    parser.add_argument("--write", action="store_true", help="catalog: write templates/charts/catalog.md")
    parser.add_argument("--check", action="store_true", help="build: validate plan.md without writing files")
    args = parser.parse_args(argv)
    if args.command == "catalog":
        text = catalog_text()
        if args.write:
            (SKILL_DIR / "templates/charts/catalog.md").write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0
    if not args.project:
        parser.error(f"{args.command} needs <project>")
    project = args.project.resolve()
    return cmd_source(project) if args.command == "source" else cmd_build(project, args.check)


if __name__ == "__main__":
    sys.exit(main())
