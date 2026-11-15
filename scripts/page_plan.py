#!/usr/bin/env python3
"""Per-page planning for Executor Step 6: briefs, sub-agent groups, page state, per-page checks.

Never generates SVG. Subcommands (all take <project_path>):

  briefs         write briefs/NN.md + briefs/plan.json (anchor + balanced sub-agent groups)
  status         classify every page: done / missing / broken / stale / edited / unknown (+ extra files)
  record         mark pages done in page_state.json after they pass the per-file checker
  verify         after a wave: expected files exist, no extra SVGs, done pages untouched
  check          per-page self-check (checker + content lock + bindings); --lock-only while writing locks
  icons          spec_lock icon inventory names missing from the locked library (+ close real names)
"""
from __future__ import annotations

import argparse
import copy
import difflib
import functools
import hashlib
import json
import math
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_spec import parse_lock  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parents[1]
RULES_FILE = SKILL_DIR / "templates" / "page_brief_rules.md"
STYLES_FILE = SKILL_DIR / "templates" / "page_brief_styles.md"
_SERIES = ("series red → deep blue → teal → orange → purple #7C3AED, then #6B7280 for 'Khác'; label marks directly; "
           "growth the source states (tăng, vượt, +x%) teal, a decline or shortfall orange")
_TIMELINE = ("past milestones #999999, those the source calls done/hoàn thành teal, a red line at the report date, "
             "upcoming ones white with a deep-blue outline")
COLOR_RECIPES = {   # one line per chart family, in each page brief (rule 10 has the shared system)
    "progress": "actual solid over its plan/target in the same color at fill-opacity 0.25; rows in different units "
                "(trạm, km, cổng…) are drawn as % of their own plan, so every plan mark is one dashed #6B7280 line at the "
                "same x (100%) — never one absolute axis for mixed units; thin bars (≤ 24px) — the bar the title names red, the others deep blue; teal where "
                "the source says done/vượt/≥100% or growth, orange where it says chậm/cảnh báo/giảm",
    "kpi": "identical white cards (#E6E6E6 stroke); only the focal card gets a red top stripe and a red number, every "
           "other number black",
    "comparison": "red leads: context columns red at fill-opacity 0.4, the item the title names solid red; periods "
                  "side by side: the current one solid red, the earlier one or the plan deep blue at fill-opacity "
                  "0.45; a second measure deep blue; a growth label the source states (tăng, +x%) teal, a decline "
                  "orange; no gray columns; value labels at the bar ends, no legend for one series",
    "time": "current period red, 5–6px; earlier or comparison period deep blue at stroke-opacity 0.5, 2–3px; growth markers teal; label each line at its end "
            "instead of a legend; gridlines #E6E6E6",
    "milestones": _TIMELINE,
    "schedule": _TIMELINE,
    "composition": _SERIES + "; more than 6 parts → merge the smallest into 'Khác'",
    "matrix": "one hue (teal) whose fill-opacity grows with the value (0.08 → 0.9), black text on every cell; orange "
              "only on rows the source calls chậm/cảnh báo",
    "waterfall": "increase teal, decrease orange, totals deep blue; red only for the figure the title names",
    "pareto": "bars of the vital few red, the rest red at fill-opacity 0.4, the cumulative line deep blue; label the cut-off item",
    "funnel": "red stepping down in fill-opacity (1 → 0.3) stage by stage; the stage the title names keeps full red "
              "and a bold label",
    "structure": "tables: header #44494D with white bold text, zebra #F2F2F2, a percentage column may use the one-hue "
                 "teal scale; cards and steps per rule 10",
}


@functools.lru_cache(maxsize=1)
def _chart_index() -> dict:
    return json.loads((SKILL_DIR / "templates/charts/charts_index.json").read_text(encoding="utf-8"))["charts"]


def chart_family(template: str | None) -> str | None:
    return _chart_index().get(template or "", {}).get("data_requirements", {}).get("family")
SHARED_BRIEF = "_shared.md"
ICONS_DIR = SKILL_DIR / "templates" / "icons"
SLIDE_RE = re.compile(r"^#### Slide (\d+)\s*[-–—:]?\s*(.*?)\s*$")
PART_RE = re.compile(r"^### Part\b")
MIN_GROUP_PAGES = 3
BLOCK_ID_RE = re.compile(r"\bS[0-9a-f]{6,}-B\d{2,}\b")  # source_index.py block IDs
LOCK_RE = re.compile(r"^```content-lock\s*\n(.*?)^```\s*$", re.M | re.S)
COMMON_SECTIONS = ("canvas", "brand", "colors", "typography", "text_fit", "icons", "images", "forbidden")
PAGE_MAPS = ("page_rhythm", "page_backgrounds", "page_layouts", "page_charts")
EXECUTION_DEFAULTS = {"generation_mode": "sequential", "max_subagents": "6",
                      "max_pages_per_subagent": "8", "anchor": "main"}


# ---------------------------------------------------------------- parsing

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slugify(title: str) -> str:
    text = unicodedata.normalize("NFKD", title.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")[:60] or "page"


def parse_slides(design_spec: Path, svg_dir: Path | None = None) -> list[dict]:
    """One dict per `#### Slide NN - Title` section, in order, with its part index and verbatim text."""
    slides: list[dict] = []
    part, section, current, in_fence = 0, "", None, False
    for line in design_spec.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("#"):
            match = SLIDE_RE.match(line)
            if match or line.startswith(("# ", "## ", "### ", "#### ")):
                current = None
            if PART_RE.match(line):
                part += 1
                section = re.sub(r"^### Part\b\s*\d*\s*[:.\-–—]?\s*", "", line).strip()
            if match:
                num = int(match.group(1))
                current = {"num": num, "title": match.group(2), "part": part, "section": section, "lines": []}
                slides.append(current)
        if current is not None:
            current["lines"].append(line)
    pages, bad_json = [], []
    for slide in slides:
        text = "\n".join(slide["lines"]).rstrip() + "\n"
        lock_match = LOCK_RE.search(text)
        try:
            lock = json.loads(lock_match.group(1)) if lock_match else {}
        except json.JSONDecodeError as exc:
            bad_json.append(f"Slide {slide['num']:02d}: {exc.msg} (lock line {exc.lineno}, col {exc.colno})")
            continue
        pid = lock.get("page") or f"P{slide['num']:02d}"
        svg = lock.get("svg")
        if not svg:
            # Legacy (no content-lock): keep an existing NN_*.svg name, else derive one from the title.
            existing = sorted(svg_dir.glob(f"{slide['num']:02d}_*.svg")) if svg_dir and svg_dir.exists() else []
            svg = existing[0].name if len(existing) == 1 else f"{slide['num']:02d}_{slugify(slide['title'])}.svg"
        pages.append({"id": pid, "num": slide["num"], "title": slide["title"], "part": slide["part"],
                      "section": slide["section"], "text": text, "svg": svg})
    if bad_json:
        raise SystemExit("Invalid content-lock JSON in design_spec.md:\n" + "\n".join(bad_json))
    return pages


def lock_sections(spec_lock: Path) -> dict[str, str]:
    """Raw markdown of each `## section` in spec_lock.md."""
    sections: dict[str, str] = {}
    name = None
    for line in spec_lock.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            sections[name] = line + "\n"
        elif name:
            sections[name] += line + "\n"
    return sections


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.svg_dir = self.root / "svg_output"
        self.briefs_dir = self.root / "briefs"
        self.state_path = self.root / "page_state.json"
        self.pages = parse_slides(self.root / "design_spec.md", self.svg_dir)
        if not self.pages:
            raise SystemExit("design_spec.md has no '#### Slide NN - Title' sections")
        lock_path = self.root / "spec_lock.md"
        self.lock = parse_lock(lock_path) if lock_path.exists() else {}
        self.lock_raw = lock_sections(lock_path) if lock_path.exists() else {}
        execution = {**EXECUTION_DEFAULTS,
                     **{k: re.sub(r"\s+#.*$", "", v) for k, v in self.lock.get("execution", {}).items()}}
        self.mode = execution["generation_mode"]
        self.max_subagents = max(1, int(execution["max_subagents"]))
        self.max_pages = max(1, int(execution["max_pages_per_subagent"]))
        # The checker and exporter map an SVG to its page by the numeric filename prefix.
        bad = [f"{p['id']}: {p['svg']}" for p in self.pages if not p["svg"].startswith(f"{p['num']:02d}_")]
        if bad:
            raise SystemExit("SVG filename must start with the slide number (NN_*.svg); fix the content-lock "
                             "'svg' field in design_spec.md: " + ", ".join(bad))
        self.by_id = {p["id"]: p for p in self.pages}

    def page_map(self, section: str, pid: str) -> str:
        return self.lock.get(section, {}).get(pid, "").strip()

    def weight(self, page: dict) -> float:
        rhythm = self.page_map("page_rhythm", page["id"]) or "dense"
        chart = self.page_map("page_charts", page["id"])
        if rhythm in ("anchor", "breathing"):
            return 0.5
        if chart:
            return 1.3 if "table" in chart else 1.5
        return 1.0

    def is_frame(self, page: dict) -> bool:
        return self.page_map("page_rhythm", page["id"]) == "anchor"

    def lock_sha(self, page: dict) -> str:
        maps = {m: self.page_map(m, page["id"]) for m in PAGE_MAPS}
        return sha256_text(page["text"] + json.dumps(maps, sort_keys=True))

    def resolve_template(self, value: str, kind: str) -> str:
        if not value:
            return ""
        name = f"{value}.svg"
        candidates = {
            "layout": [self.root / "templates" / name, SKILL_DIR / "templates/layouts/viettel_default" / name],
            "background": [self.root / "templates/backgrounds" / name,
                           SKILL_DIR / "templates/layouts/viettel_default/backgrounds" / name],
            "chart": [SKILL_DIR / "templates/charts" / name],
        }[kind]
        for path in candidates:
            if path.exists():
                return str(path)
        return f"MISSING: {candidates[0]}"

    def svg_path(self, page: dict) -> Path:
        return self.svg_dir / page["svg"]

    def load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"version": 1, "pages": {}}

    def save_state(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def load_plan(self) -> dict:
        path = self.briefs_dir / "plan.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def parse_ids(project: Project, raw: str | None) -> list[str]:
    if not raw:
        return []
    if raw == "all":
        return [p["id"] for p in project.pages]
    ids = []
    for token in raw.split(","):
        token = token.strip()
        pid = token if token.upper().startswith("P") else f"P{int(token):02d}"
        if pid.upper() not in {k.upper() for k in project.by_id}:
            raise SystemExit(f"Unknown page: {token}")
        ids.append(next(k for k in project.by_id if k.upper() == pid.upper()))
    return ids


def checker_errors(svg: Path) -> list[str]:
    from svg_quality_checker import SVGQualityChecker
    return SVGQualityChecker().check_file(str(svg)).get("errors", [])


EMPTY_LOCK = {"facts": [], "derived": [], "conclusions": [], "unresolved": [], "visualizations": [], "required": []}
# Plain-language fixes for content_check's terse messages, so nobody reads the script to decode them.
LOCK_HINTS = {
    "quote not found": "copy the quote verbatim from `source_index.py <project> --list` (or `--show <block-id>`) output, "
                       "markup and HTML tags included",
    "Unknown source ref": "use a block ID printed by `source_index.py <project> --list`; never write block IDs from memory",
    "Raw numeric token absent": "`raw` must appear verbatim inside one of the fact's quotes",
    "Invalid Vietnamese number": "locale vi reads '.' as thousands and ',' as decimals (1.234,5); a dot decimal such as "
                                 "271.7 needs locale en; K/M/B-suffixed tokens (593K) need numeric:false with the token as value",
    "Normalized number differs": "`value` must equal `raw` parsed in its locale (vi 1.406 → 1406; en 271.7 → 271.7)",
    "lacks": "data-driven templates need that dimension field (e.g. category) on every input fact",
    "Calculation inputs have mixed units": "every derived input needs the same unit",
}


def lock_hint(exc: Exception) -> str:
    msg = str(exc)
    if isinstance(exc, KeyError):
        msg = f"missing field {msg}" + (": every derived input must be a numeric fact (value, raw, locale)"
                                         if msg == "'value'" else "")
    hint = next((h for key, h in LOCK_HINTS.items() if key in msg), "")
    return f"{msg} — {hint}" if hint else msg


def lock_errors(lock: dict, blocks: dict, catalog: dict, index_sha: str) -> list[str]:
    """Every fact's mechanical error with its ID (one fact at a time through content_check), plus the index hash."""
    import content_check as cc
    errors = []
    if lock.get("source_index_sha256") != index_sha:
        errors.append(f"source_index_sha256 must be {index_sha} (SHA-256 of the sources/source_index.json file itself)")
    for fact in lock.get("facts", []):
        try:
            cc.check_page(dict(EMPTY_LOCK, facts=[fact]), blocks, catalog)
        except (ValueError, KeyError, TypeError, cc.InvalidOperation) as exc:
            msg, fid = lock_hint(exc), f"{fact.get('id', '?')}: "
            errors.append(msg if msg.startswith(fid) else fid + msg)
    return errors


def content_errors(project: Project, pids: list[str], with_svg: bool = True) -> dict[str, str]:
    """Per-page content_check (lock + SVG bindings) so one page's error never hides another's; a page with
    several broken facts lists all of them (newline-separated). Empty for legacy projects without content locks."""
    import content_check as cc
    try:
        locks = cc.load_contract(project.root)
    except ValueError as exc:
        return {pid: f"content contract: {exc}" for pid in pids}
    if locks is None:
        return {}
    blocks = cc.read_blocks(project.root)
    catalog = json.loads(cc.CATALOG.read_text(encoding="utf-8"))["charts"]
    index_sha = sha256_file(project.root / "sources" / "source_index.json")
    by_id, errors = {lock["page"]: lock for lock in locks}, {}
    for pid in pids:
        lock, svg = by_id.get(pid), project.svg_path(project.by_id[pid])
        if lock is None:
            errors[pid] = "no content-lock block for this page"
            continue
        if found := lock_errors(lock, blocks, catalog, index_sha):
            errors[pid] = "\n".join(found)
            continue
        try:
            values = cc.check_page(lock, blocks, catalog)
            if with_svg and svg.exists():
                cc.svg_check(svg, lock, values)
                leaked = sorted(set(BLOCK_ID_RE.findall("".join(ET.parse(svg).getroot().itertext()))))
                if leaked:
                    errors[pid] = (f"visible text shows internal source block IDs {', '.join(leaked)}: "
                                   "remove them (never show source/lock IDs on a slide)")
        except (ValueError, KeyError, TypeError, ET.ParseError, cc.InvalidOperation) as exc:
            errors[pid] = lock_hint(exc)
    return errors


# ---------------------------------------------------------------- status

def classify(project: Project, state: dict | None = None, *, run_checker: bool = True) -> dict:
    state = state or project.load_state()
    result: dict = {"pages": {}, "extra": []}
    for page in project.pages:
        svg, rec = project.svg_path(page), state["pages"].get(page["id"])
        if not svg.exists():
            status = "missing"
        else:
            try:
                ET.parse(svg)
                parsed = True
            except ET.ParseError:
                parsed = False
            if not parsed:
                status = "broken"
            elif rec is None:
                status = "unknown"
            elif rec.get("lock_sha") != project.lock_sha(page):
                status = "stale"
            elif rec.get("svg_sha") != sha256_file(svg):
                status = "edited"
            else:
                status = "done"
        entry = {"status": status, "file": page["svg"]}
        if run_checker and status in ("unknown", "edited"):
            errors = checker_errors(svg)
            entry["errors"] = len(errors)
            if status == "unknown" and errors:
                entry["status"] = "broken"
        result["pages"][page["id"]] = entry
    expected = {p["svg"] for p in project.pages}
    if project.svg_dir.exists():
        result["extra"] = sorted(p.name for p in project.svg_dir.glob("*.svg") if p.name not in expected)
    return result


def cmd_status(project: Project, args) -> int:
    result = classify(project)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        counts: dict[str, list[str]] = {}
        for pid, entry in result["pages"].items():
            counts.setdefault(entry["status"], []).append(pid)
        for status in ("done", "edited", "unknown", "missing", "broken", "stale"):
            if status in counts:
                print(f"{status:8} {len(counts[status]):3}  {', '.join(counts[status])}")
        if result["extra"]:
            print(f"extra    {len(result['extra']):3}  {', '.join(result['extra'])}  (not in design_spec; blocks export)")
    return 1 if result["extra"] else 0


# ---------------------------------------------------------------- grouping

def partition(items: list[dict], weights: dict[str, float], cap_pages: int, min_groups: int = 1) -> list[list[dict]]:
    """Contiguous groups, ≤ cap_pages each, minimising the heaviest. Up to min_groups groups, but each keeps
    ≥ MIN_GROUP_PAGES pages: a sub-agent's ~6 min start-up costs as much as drawing 3 pages.
    Prefers to cut at a Part boundary once a group is ≥ 75% of the capacity."""
    if not items:
        return []
    target = max(math.ceil(len(items) / cap_pages), min(min_groups, math.ceil(len(items) / MIN_GROUP_PAGES)))

    def greedy(cap_w: float, prefer_parts: bool) -> list[list[dict]]:
        groups, load = [[]], 0.0
        for item in items:
            group, w = groups[-1], weights[item["id"]]
            part_cut = prefer_parts and bool(group) and item["part"] != group[-1]["part"] and load >= 0.75 * cap_w
            if group and (load + w > cap_w + 1e-9 or len(group) >= cap_pages or part_cut):
                groups.append([])
                load = 0.0
            groups[-1].append(item)
            load += w
        return groups

    def best(prefer_parts: bool) -> list[list[dict]]:
        lo, hi = max(weights[i["id"]] for i in items), sum(weights[i["id"]] for i in items)
        for _ in range(50):
            mid = (lo + hi) / 2
            if len(greedy(mid, prefer_parts)) <= target:
                hi = mid
            else:
                lo = mid
        return greedy(hi, prefer_parts)

    groups = best(prefer_parts=True)
    return groups if len(groups) <= target else best(prefer_parts=False)


AGENDA_TEMPLATES = {"agenda_list"}
FRAME_LAYOUTS = {"01_cover", "02_chapter", "02_toc", "04_ending"}


def fact_count(page: dict) -> int:
    match = LOCK_RE.search(page["text"])
    try:
        return len(json.loads(match.group(1)).get("facts", [])) if match else 0
    except json.JSONDecodeError:
        return 0


def choose_anchor(project: Project, status: dict) -> dict:
    """A representative content page every sub-agent can match: the richest data chart (most facts; timelines
    count as structure), then a structure template, then any content page — never the agenda, a
    cover/chapter/ending shell or a frame page. A page already drawn and recorded wins within its pool."""
    content = [p for p in project.pages if not project.is_frame(p)
               and (project.page_map("page_rhythm", p["id"]) or "dense") == "dense"
               and project.page_map("page_layouts", p["id"]) not in FRAME_LAYOUTS
               and project.page_map("page_charts", p["id"]) not in AGENDA_TEMPLATES]
    chart = lambda p: project.page_map("page_charts", p["id"])
    sparse = ("structure", "milestones")
    data = [p for p in content if chart(p) and chart_family(chart(p)) not in sparse]
    structure = [p for p in content if chart(p) and chart_family(chart(p)) in sparse]
    for pool in (data, structure, content, project.pages):
        pool = sorted(pool, key=lambda p: -fact_count(p))  # stable: page order among equals
        done = [p for p in pool if status["pages"][p["id"]]["status"] in ("done", "edited")]
        if done or pool:
            return (done or pool)[0]
    return project.pages[0]


# ---------------------------------------------------------------- briefs

def shared_brief_text(project: Project) -> str:
    """Rules + spec_lock sections common to every page: written once, read once per agent."""
    rules = RULES_FILE.read_text(encoding="utf-8") if RULES_FILE.exists() else ""
    common = "".join(project.lock_raw.get(s, "") for s in COMMON_SECTIONS)
    style = deck_style(project)
    return f"{rules.rstrip()}\n\n{style + chr(10) * 2 if style else ''}# Spec lock (shared)\n\n{common.rstrip()}\n"


def deck_style(project: Project) -> str:
    """The `## A|B|C` block of page_brief_styles.md matching the Style row of design_spec.md, or ''."""
    match = re.search(r"^\|\s*Style\s*\|\s*([ABC])\b", (project.root / "design_spec.md").read_text(encoding="utf-8"),
                      re.M)
    if not match or not STYLES_FILE.exists():
        return ""
    parts = re.split(r"^## ([ABC])\s*$", STYLES_FILE.read_text(encoding="utf-8"), flags=re.M)
    return dict(zip(parts[1::2], parts[2::2])).get(match.group(1), "").strip()


def brief_text(project: Project, page: dict, anchor: dict | None) -> str:
    pid = page["id"]
    anchor_line = ("this page IS the anchor (main agent draws it first)" if anchor is None or anchor["id"] == pid
                   else str(project.svg_path(anchor)))
    return (
        f"# Page {pid} — {page['title']}\n\n"
        f"- shared rules + spec_lock sections (read once before your first page): "
        f"{project.briefs_dir / SHARED_BRIEF}\n"
        f"- output: {project.svg_path(page)}\n"
        f"- rhythm: {project.page_map('page_rhythm', pid) or 'dense'}\n"
        f"- section (footer band, binds c_label): {page.get('section') or 'none'}\n"
        f"- background: {project.resolve_template(project.page_map('page_backgrounds', pid), 'background') or 'none'}\n"
        f"- layout: {project.resolve_template(project.page_map('page_layouts', pid), 'layout') or 'none (adaptive Viettel composition)'}\n"
        f"- chart: {project.resolve_template(project.page_map('page_charts', pid), 'chart') or 'none'}\n"
        f"- color recipe: {COLOR_RECIPES.get(chart_family(project.page_map('page_charts', pid)), _SERIES)}\n"
        f"- anchor_to_match: {anchor_line}\n"
        f"- spec_lock: {project.root / 'spec_lock.md'}\n\n"
        f"## Content lock and outline (verbatim from design_spec.md)\n\n{page['text']}"
    )


def draw_context(project: Project, group: list[dict], anchor: dict | None, lang: str) -> str:
    owned = "\n".join(f"- {p['id']} -> {project.svg_path(p)}  (brief: {project.briefs_dir / (p['id'] + '.md')})"
                      for p in group)
    anchor_txt = str(project.svg_path(anchor)) if anchor else "none"
    return (
        f"You are a sub-agent drawing Viettel slide SVGs. Project: {project.root}. Skill dir: {SKILL_DIR}.\n"
        f"Pages you own — you may write ONLY these files:\n{owned}\n"
        f"First read {project.briefs_dir / SHARED_BRIEF} once (rules, binding pattern, shared spec_lock sections). "
        f"Read only: that file, your briefs, {project.root / 'spec_lock.md'}, the anchor SVG {anchor_txt}, and the "
        "template files listed in each brief. Never open files of another project (other folders under projects/): "
        "their pages carry other decks' content. Do not read SKILL.md or references/ unless a brief lacks information "
        "you need; if you do, list the files you read in your final answer. Never open the skill's scripts "
        "(page_plan.py, content_check.py, svg_quality_checker.py or any other .py): the shared rules and the check "
        "output tell you what to fix. Every other file in the project is read-only.\n"
        "For each page, in order: re-read its brief and spec_lock.md, hand-write the SVG (one page per write; never "
        "generate SVG with a script), match the anchor's title/header/footer/card/table style, bind every text to its "
        "content-lock IDs (shared rule 1 and the binding pattern), then run "
        f"`python3 {SKILL_DIR}/scripts/page_plan.py check {project.root} --pages <PID>` (per-file checker + "
        "content bindings + fact checks: period labels, statuses, section names, ratios, title counts traced to "
        "your bound source) and fix until it prints an empty list; at most 2 fix attempts per finding. Never "
        "render, screenshot or call an image/vision tool to inspect a page: the check is the inspection, and a "
        "browser render of raw SVG does not show the exported wrapping. After your last page passes, answer at once. For a page "
        f"whose brief lists a chart, verify its geometry per {SKILL_DIR}/workflows/verify-charts.md "
        "for that page only.\n"
        "Never: write any file not listed above; run the checker on the whole project or with --export; run "
        "apply_brand_chrome.py, svg_to_pptx.py or content_check.py; edit SVGs with a script.\n"
        "Final answer: for each page the absolute path written, its `verify-charts:` result line (chart pages), any "
        "remaining checker errors (rule + element), and "
        f"any content-lock item you could not represent. Answer in {lang}."
    )


def cmd_briefs(project: Project, args) -> int:
    status = classify(project, run_checker=bool(args.only))
    if args.pages:
        targets = parse_ids(project, args.pages)
    elif args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        targets = [pid for pid, e in status["pages"].items() if e["status"] in wanted]
    else:
        targets = [p["id"] for p in project.pages]
    anchor = choose_anchor(project, status)
    if not args.pages and status["pages"][anchor["id"]]["status"] in ("done", "edited") and anchor["id"] in targets:
        targets.remove(anchor["id"])  # drawn earlier (e.g. an interrupted run): keep it as the reference
    if not targets:
        print("Nothing to draw: no page matches the selection.")
        return 0
    contract = re.search(r"^content_contract:\s*1\s*$", (project.root / "design_spec.md").read_text(encoding="utf-8"), re.M)
    unlocked = [pid for pid in targets if not has_lock(project.by_id[pid])]
    if contract and unlocked:
        print("Refused: no content-lock block for " + ", ".join(unlocked)
              + " — write each page's content lock in design_spec.md first (content-grounding §2), then re-run briefs")
        return 1
    anchor_needs_draw = anchor["id"] in targets
    project.briefs_dir.mkdir(exist_ok=True)
    (project.briefs_dir / SHARED_BRIEF).write_text(shared_brief_text(project), encoding="utf-8")
    weights = {p["id"]: project.weight(p) for p in project.pages}
    plan_pages = {}
    for pid in targets:
        page = project.by_id[pid]
        (project.briefs_dir / f"{pid}.md").write_text(brief_text(project, page, anchor), encoding="utf-8")
        plan_pages[pid] = {"file": page["svg"], "brief": str(project.briefs_dir / f"{pid}.md"),
                           "lock_sha": project.lock_sha(page)}
    rest = [project.by_id[pid] for pid in targets if pid != anchor["id"]]
    rest.sort(key=lambda p: p["num"])
    # One contiguous partition: frame pages ride along with their neighbours, so a ≤ 49-page deck is one wave.
    groups = partition(rest, weights, project.max_pages, project.max_subagents)
    waves, lang = [], args.lang
    for index, group in enumerate(groups):
        if index % project.max_subagents == 0:
            waves.append([])
        waves[-1].append({"group": f"G{index + 1}", "pages": [p["id"] for p in group],
                          "weight": round(sum(weights[p["id"]] for p in group), 2),
                          "context": draw_context(project, group, anchor, lang)})
    plan = {"version": 1, "created_at": datetime.now(timezone.utc).isoformat(), "project": str(project.root),
            "skill_dir": str(SKILL_DIR), "generation_mode": project.mode,
            "max_subagents": project.max_subagents, "max_pages_per_subagent": project.max_pages,
            "anchor": {"page": anchor["id"], "file": anchor["svg"], "needs_draw": anchor_needs_draw},
            "pages": plan_pages, "waves": waves,
            # Pages outside this plan must keep these bytes until the plan's waves finish (verify).
            "frozen": {p["id"]: sha256_file(project.svg_path(p)) for p in project.pages
                       if p["id"] not in plan_pages and project.svg_path(p).exists()}}
    (project.briefs_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    print(f"anchor: {anchor['id']} ({anchor['svg']}){' — draw it first' if anchor_needs_draw else ' — exists'}")
    for n, wave in enumerate(waves, 1):
        print(f"wave {n}: " + "  ".join(f"{g['group']}[{','.join(g['pages'])}] w={g['weight']}" for g in wave))
    if waves and project.mode == "parallel":
        print(f"dispatch: {len(waves[0])} separate sub-agent calls in one turn (NetMind: {len(waves[0])} delegate_task "
              "calls, each with ONE task = one group's context) — never one call holding several groups")
    print(f"plan: {project.briefs_dir / 'plan.json'}")
    return 0


# ---------------------------------------------------------------- record / verify

def cmd_record(project: Project, args) -> int:
    state, plan = project.load_state(), project.load_plan()
    plan_locks = {pid: e["lock_sha"] for pid, e in plan.get("pages", {}).items()}
    refused = []
    for pid in parse_ids(project, args.pages):
        page, svg = project.by_id[pid], project.svg_path(project.by_id[pid])
        current = project.lock_sha(page)
        expected = plan_locks.get(pid) or state["pages"].get(pid, {}).get("lock_sha") or current
        if not svg.exists():
            refused.append(f"{pid}: missing SVG")
        elif current != expected and not args.accept_lock:
            refused.append(f"{pid}: content lock changed since this page was drawn (stale) — redraw it, or "
                           "--accept-lock once the SVG was updated to the new lock")
        elif errors := checker_errors(svg):
            refused.append(f"{pid}: {len(errors)} checker error(s)")
        elif error := content_errors(project, [pid]).get(pid):
            refused.append(f"{pid}: content check: {error}")
        else:
            state["pages"][pid] = {"file": page["svg"], "lock_sha": current, "svg_sha": sha256_file(svg),
                                   "recorded_at": datetime.now(timezone.utc).isoformat()}
    project.save_state(state)
    for line in refused:
        print(f"NOT RECORDED {line}")
    print(f"recorded {len(parse_ids(project, args.pages)) - len(refused)} page(s) in {project.state_path}")
    return 1 if refused else 0


FIXABLE_FACT_WARNINGS = ("period-dropped", "ratio-noun")   # the drawer can fix these on the page itself


def chrome_key(svg: Path) -> str | None:
    """The page's viettel-brand-chrome group with the page-number digits blanked, or None when absent."""
    try:
        root = ET.parse(svg).getroot()
    except (ET.ParseError, OSError):
        return None
    group = next((el for el in root.iter() if el.get("id") == "viettel-brand-chrome"), None)
    if group is None:
        return None
    group = copy.deepcopy(group)
    for el in group.iter():
        if el.get("data-chrome") == "page-number":
            el.text = ""
            for child in el:
                child.text = ""
        el.tail = None
    return re.sub(r"\s+", " ", ET.tostring(group, encoding="unicode"))


def chrome_drift(project: Project, pid: str) -> str | None:
    """Every page carries the anchor's brand chrome unchanged (only the page number differs)."""
    anchor = (project.load_plan().get("anchor") or {}).get("page")
    if not anchor or anchor == pid or anchor not in project.by_id:
        return None
    mine, ref = project.svg_path(project.by_id[pid]), project.svg_path(project.by_id[anchor])
    if not (mine.exists() and ref.exists()):
        return None
    want, have = chrome_key(ref), chrome_key(mine)
    if want and have != want:
        return (f"chrome: the <g id=\"viettel-brand-chrome\"> group differs from the anchor {anchor} ({ref.name}) — "
                "copy the anchor's group unchanged on every page, chapter and ending pages included; only the "
                "page-number digits change")
    return None


ACCENT_COLORS = {"#EE0033", "#28A197", "#F46A25", "#10B981", "#059669"}   # emerald may replace teal in charts
FRAME_GROUP_IDS = ("header", "footer", "bg", "background", "decor", "viettel-brand-chrome")
CONTENT_BOTTOM_MIN = 470  # a dense page whose content ends above this leaves its lower third empty
CONTENT_TOP_MAX = 250     # content area starts at y=132; a first element below this leaves a band empty under the title


def visual_findings(project: Project, page: dict, svg: Path) -> list[str]:
    """Shared rule 10 on dense content pages: a focal accent in the content (accent text ≥ 22px, an accent bar,
    card or icon ≥ 10px thick, a marker r ≥ 10 — thin stripes and dots do not count) and text down to the lower
    third. ponytail: translate() is the only transform followed."""
    if (project.page_map("page_rhythm", page["id"]) or "dense") != "dense":
        return []
    try:
        root = ET.parse(svg).getroot()
    except ET.ParseError:
        return []
    accent, bottom, top = False, 0.0, 720.0

    def num(el: ET.Element, name: str, default: float = 0.0) -> float:
        try:
            return float(re.sub(r"[^\d.\-]", "", el.get(name, "")) or default)
        except ValueError:
            return default

    def walk(el: ET.Element, dy: float, size: float) -> None:
        nonlocal accent, bottom, top
        gid = (el.get("id") or "").lower()
        if el.get("data-chrome") or any(k in gid for k in FRAME_GROUP_IDS):
            return
        if m := re.search(r"translate\(\s*[-\d.]+[\s,]*([-\d.]*)", el.get("transform", "")):
            dy += float(m.group(1) or 0)
        size = num(el, "font-size", size)
        tag = el.tag.rsplit("}", 1)[-1]
        if {(el.get(a) or "").strip().upper() for a in ("fill", "stroke")} & ACCENT_COLORS:
            accent = accent or {
                "text": size >= 22,
                "rect": min(num(el, "width"), num(el, "height")) >= 10,
                "use": num(el, "width") >= 24,
                "circle": num(el, "r") >= 10,
                "ellipse": min(num(el, "rx"), num(el, "ry")) >= 10,
                "path": True, "polygon": True,
            }.get(tag, False)
        if tag == "text" and "".join(el.itertext()).strip() and num(el, "y") + dy < 660:
            bottom = max(bottom, num(el, "y") + dy)
        if tag in ("text", "rect", "use", "circle", "image") and 140 < num(el, "y", num(el, "cy")) + dy < 660:
            top = min(top, num(el, "y", num(el, "cy")) + dy)    # below the subtitle line
        for child in el:
            walk(child, dy, size)

    walk(root, 0.0, 16.0)
    found = []
    if not accent:
        found.append("visual: no focal accent in the content — give the page its key number or phrase in red "
                     "#EE0033 at ≥ 22px bold, or a red bar, card stripe or icon ≥ 10px; color the statuses the source "
                     "states (teal #28A197 done, orange #F46A25 cảnh báo/chậm/nguy cơ) (shared rule 10)")
    if top > CONTENT_TOP_MAX and top < 720:
        found.append(f"visual: the content starts at y={top:.0f} — leave no empty band under the title; start the "
                     "first row or card at y≈140–180 and use the height for bigger rows (shared rule 10)")
    if bottom and bottom < CONTENT_BOTTOM_MIN:
        found.append(f"visual: the last text ends at y={bottom:.0f} — the content area runs to y≈650; enlarge rows, "
                     "cards and numbers to fill it, never leave the lower third empty (shared rule 10)")
    return found


def cmd_check(project: Project, args) -> int:
    """Per-page self-check: checker + content lock + bindings; an SVG not written yet is reported, never an empty list.
    --lock-only: content locks only (plan gate while writing design_spec.md), every listed page in one run."""
    pids = parse_ids(project, args.pages)
    content = content_errors(project, pids, with_svg=not args.lock_only)
    report = {}
    for pid in pids:
        svg = project.svg_path(project.by_id[pid])
        drawn = [] if args.lock_only else (
            [f"svg missing: {svg.name} not written yet"] if not svg.exists() else
            [f"svg empty: {svg.name} has no content — write the page again"] if not svg.stat().st_size else
            checker_errors(svg))
        report[pid] = list(drawn) + ([f"content: {e}" for e in content[pid].split("\n")] if pid in content else [])
        if not args.lock_only and (drift := chrome_drift(project, pid)):
            report[pid].append(drift)
        if not args.lock_only and svg.exists():
            report[pid] += visual_findings(project, project.by_id[pid], svg)
    if not args.lock_only:
        import fact_check
        findings, _ = fact_check.audit(project.root, set(pids))
        for f in findings:
            if f["level"] == "error" or f["rule"] in FIXABLE_FACT_WARNINGS:
                report[f["page"]].append(f"fact {f['level']}: {f['rule']} — {f['detail']} — text '{f['text'][:70]}'")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(report.values()) else 0


def icon_report(libs: list[str], names: list[str]) -> dict[str, list[str]] | str:
    """Names the locked libraries do not have, each with up to 4 real close names; or an error string."""
    if not libs or not all((ICONS_DIR / lib).is_dir() for lib in libs):
        return f"icons library must be one of {sorted(p.name for p in ICONS_DIR.iterdir() if p.is_dir())}"
    available = sorted({p.stem for lib in libs for p in (ICONS_DIR / lib).glob("*.svg")})
    missing = {}
    for name in (n.strip().split("/")[-1] for n in names):
        if name and name not in available:
            words = [w for w in name.split("-") if len(w) >= 3]
            close = [a for a in available if any(w in a.split("-") for w in words)][:4]
            close += [a for a in difflib.get_close_matches(name, available, 4, 0.6) if a not in close][:4 - len(close)]
            missing[name] = close
    return missing


def cmd_icons(project: Project, args) -> int:
    """spec_lock `## icons` inventory names that do not exist in the locked library, with close real names."""
    icons = project.lock.get("icons", {})
    libs = [v.strip() for v in (icons.get("library", ""), icons.get("brand_library", "")) if v and v.strip()]
    report = icon_report(libs, icons.get("inventory", "").split(","))
    if isinstance(report, str):
        print(json.dumps({"spec_lock": f"## {report}"}))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 1 if report else 0


def cmd_verify(project: Project, args) -> int:
    plan = project.load_plan()
    waves = plan.get("waves", [])
    if args.wave:
        waves = [waves[args.wave - 1]]
    expected = [pid for wave in waves for group in wave for pid in group["pages"]]
    report: dict = {"missing": [], "broken": [], "checker_errors": {}, "content_errors": {}, "extra": [],
                    "changed_outside_plan": []}
    for pid in expected:
        svg = project.svg_path(project.by_id[pid])
        if not svg.exists():
            report["missing"].append(pid)
            continue
        try:
            ET.parse(svg)
        except ET.ParseError:
            report["broken"].append(pid)
            continue
        if errors := checker_errors(svg):
            report["checker_errors"][pid] = len(errors)
    parsed = [pid for pid in expected if pid not in report["missing"] and pid not in report["broken"]]
    report["content_errors"] = content_errors(project, parsed)
    for pid, digest in plan.get("frozen", {}).items():
        svg = project.svg_path(project.by_id[pid]) if pid in project.by_id else None
        if svg is None or not svg.exists() or sha256_file(svg) != digest:
            report["changed_outside_plan"].append(pid)
    names = {p["svg"] for p in project.pages}
    if project.svg_dir.exists():
        report["extra"] = sorted(p.name for p in project.svg_dir.glob("*.svg") if p.name not in names)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    hard = report["missing"] or report["broken"] or report["extra"] or report["changed_outside_plan"]
    return 1 if hard else 0


def has_lock(page: dict) -> bool:
    return bool(LOCK_RE.search(page["text"]))


# ---------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("briefs", "status", "record", "check", "verify", "icons"):
        p = sub.add_parser(name)
        p.add_argument("project", type=Path)
        if name == "briefs":
            p.add_argument("--lang", default="the user's language (match design_spec.md)")
        if name == "briefs":
            p.add_argument("--only", help="comma list of statuses to draw, e.g. missing,broken,stale")
            p.add_argument("--pages", help="comma list of page IDs or numbers, or 'all'")
        if name in ("record", "check"):
            p.add_argument("--pages", required=True, help="comma list of page IDs or numbers, or 'all'")
        if name == "check":
            p.add_argument("--lock-only", action="store_true",
                           help="content locks only, no SVG checks (while writing design_spec.md)")
        if name == "record":
            p.add_argument("--accept-lock", action="store_true",
                           help="record stale pages against the current lock (only after updating their SVG)")
        if name == "status":
            p.add_argument("--json", action="store_true")
        if name == "verify":
            p.add_argument("--wave", type=int, help="1-based wave index (default: every wave in plan.json)")
    args = parser.parse_args(argv)
    project = Project(args.project)
    handler = {"briefs": cmd_briefs, "status": cmd_status, "record": cmd_record, "check": cmd_check,
               "verify": cmd_verify, "icons": cmd_icons}[args.command]
    return handler(project, args)


if __name__ == "__main__":
    sys.exit(main())
