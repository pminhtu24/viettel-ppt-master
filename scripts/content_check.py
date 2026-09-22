#!/usr/bin/env python3
"""Validate source-grounded slide contracts, bindings and review receipts (stdlib)."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import math
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET

from source_index import read_blocks, sha256

CATALOG = Path(__file__).resolve().parents[1] / 'templates/charts/charts_index.json'
LOCK_RE = re.compile(r'^```content-lock\s*\n(.*?)^```\s*$', re.M | re.S)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(not isinstance(value, bool) and value is not None, 'Missing value is not zero')
    result = Decimal(str(value))
    require(result.is_finite(), 'Non-finite numeric value')
    return result


def parse_source_number(raw, locale):
    raw = raw.strip().replace('\u00a0', '').replace(' ', '').rstrip('%')
    require(locale in ('vi', 'en'), 'Numeric facts need locale vi or en')
    if locale == 'vi':
        require(bool(re.fullmatch(r'[+-]?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?', raw)), 'Invalid Vietnamese number')
        raw = raw.replace('.', '').replace(',', '.')
    else:
        require(bool(re.fullmatch(r'[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', raw)), 'Invalid English number')
        raw = raw.replace(',', '')
    return number(raw)


def calculate(item, values):
    args = [number(values[key]['value']) for key in item['inputs']]
    op = item['operation']
    require(args, 'Calculation has no inputs')
    if op == 'sum':
        result = sum(args)
    elif op in ('difference', 'remainder', 'ratio', 'percent', 'percentage_points'):
        require(len(args) == 2, f'{op} needs two inputs')
        if op in ('ratio', 'percent'):
            require(args[1] != 0, 'Division by zero')
            result = args[0] / args[1] * (100 if op == 'percent' else 1)
        else:
            result = args[0] - args[1]
        if op == 'remainder':
            require(result >= 0, 'Negative remainder')
    elif op == 'convert_unit':
        require(len(args) == 1, 'Unit conversion needs one input')
        result = args[0] * number(item['factor'])
        require(item.get('conversion_basis'), 'Unit conversion needs a documented basis')
    else:
        raise ValueError(f'Unsupported operation: {op}')
    places = item.get('decimals', 1)
    require(type(places) is int and 0 <= places <= 8, 'Invalid rounding precision')
    rounded = result.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    require(number(item['value']) == rounded, f"Incorrect calculation: {item['id']} expected {rounded}")
    return result


def evidence(item, blocks):
    require(isinstance(item.get('sources'), list) and item['sources'], 'Fact needs source excerpts')
    for ref in item['sources']:
        require(ref['ref'] in blocks, f"Unknown source ref: {ref['ref']}")
        require(bool(ref['quote'].strip()) and ref['quote'] in blocks[ref['ref']], 'Quote not found in referenced block')


def chart_check(viz, values, catalog):
    key = viz['template']
    if key == 'none':
        require(viz.get('reason') in ('insufficient-data', 'source-conflict', 'incompatible-data', 'no-template-match', 'not-needed'), 'Explain visualization fallback')
        return
    require(key in catalog, f'Unknown template: {key}')
    rules = catalog[key]['data_requirements']
    rows = viz['observations']
    require(isinstance(rows, list) and rows, 'Chart has no observations')
    family = rules['family']
    require(len({json.dumps(row, sort_keys=True) for row in rows}) == len(rows), 'Duplicate chart observation')
    for row in rows:
        require(all(role in row for role in rules['roles']), f'{key} missing roles {rules["roles"]}')
        for role, ref in row.items():
            require(ref in values, f'Unknown chart data ID: {ref}')
            require(values[ref].get('status') not in ('unverified', 'conflict', 'missing'), f'Unverified chart input: {ref}')
        first = values[row[rules['roles'][0]]]
        for dimension in rules['dimensions']:
            require(bool(first.get(dimension)), f'{key} lacks {dimension}')
        if family not in ('structure', 'milestones', 'schedule'):
            for ref in row.values():
                number(values[ref]['value'])
    for check in rules['semantic_checks']:
        proof = viz.get('evidence', {}).get(check, {})
        require(proof.get('reason') and proof.get('refs'), f'{key}: missing evidence for {check}')
        require(all(ref in values for ref in proof['refs']), f'{key}: unknown evidence IDs')
    primary = [values[row[rules['roles'][0]]] for row in rows]
    nums = [number(v['value']) for v in primary] if family not in ('structure', 'milestones', 'schedule') else []
    if family in ('comparison', 'composition', 'funnel', 'pareto', 'waterfall', 'flow'):
        require(len({v['unit'] for v in primary}) == 1, 'Mixed units in one quantitative encoding')
    if family in ('composition', 'funnel', 'pareto', 'flow') or key in ('area_chart', 'stacked_area_chart'):
        require(all(v >= 0 for v in nums), 'Negative part/area/flow value')
    if family == 'time':
        by_series = {}
        for value in primary:
            by_series.setdefault(value['series'], []).append(value)
        for series in by_series.values():
            require(len({v['period'] for v in series}) >= 2, 'Time series needs at least two real observations')
            require(len({(v['unit'], v['scope'], v['entity']) for v in series}) == 1, 'Incompatible time observations')
            require(len({v['period'] for v in series}) == len(series), 'Duplicate time point')
        if key != 'dual_axis_line_chart':
            require(len({v['unit'] for v in primary}) == 1, 'Different units require separate axes')
    if family == 'funnel':
        require(len(nums) >= 2 and all(a >= b for a, b in zip(nums, nums[1:])), 'Funnel must have ordered non-increasing stages')
    if family == 'progress':
        for row in rows:
            actual = values[row['value']]
            if 'target' not in row:
                require(actual['unit'] == '%', 'Progress needs an observed percentage or target')
                continue
            target = values[row['target']]
            require(number(target['value']) > 0, 'Progress target must be positive')
            require(all(actual[f] == target[f] for f in ('unit', 'entity', 'period', 'scope')), 'Incompatible actual and target')
            # Values above target are valid; rendering must not silently clamp.
    if family in ('composition', 'pareto') or key == 'stacked_area_chart':
        totals = viz.get('totals', [])
        require(totals, 'Composition needs explicit whole(s)')
        covered = []
        for total in totals:
            require(total['whole'] in values, 'Unknown whole')
            parts = total['parts']; covered.extend(parts)
            require(parts and len(parts) == len(set(parts)), 'Duplicate/empty composition parts')
            require(all(ref in values for ref in parts), 'Unknown composition part')
            whole = values[total['whole']]
            require(all(values[ref]['unit'] == whole['unit'] for ref in parts), 'Part/whole units differ')
            require(number(whole['value']) > 0, 'Composition whole must be positive')
            require(sum(number(values[ref]['value']) for ref in parts) == number(whole['value']), 'Parts do not reconcile to whole; record source conflict')
        require(set(covered) <= {row['value'] for row in rows}, 'Composition leaves unmapped parts')
        roots = ({total['whole'] for total in totals} - set(covered)) if key == 'treemap_chart' else set()
        require({row['value'] for row in rows} <= set(covered) | roots, 'Composition has uncovered observations')
    if family == 'distribution':
        for row in rows:
            ordered = [number(values[row[r]]['value']) for r in rules['roles']]
            require(ordered == sorted(ordered), 'Invalid quartile order')
    if family == 'xy' and key == 'bubble_chart':
        require(all(number(values[r['size']]['value']) >= 0 for r in rows), 'Negative bubble size')
    if family == 'schedule':
        for row in rows:
            start = datetime.fromisoformat(str(values[row['start']]['value']))
            end = datetime.fromisoformat(str(values[row['end']]['value']))
            require(start <= end, 'Schedule end precedes start')
    if family == 'waterfall':
        require(len(nums) >= 3, 'Waterfall needs start, changes, end')
        require(primary[0]['status'] == 'start' and primary[-1]['status'] == 'end', 'Waterfall anchors missing')
        require(nums[0] + sum(nums[1:-1]) == nums[-1], 'Waterfall does not reconcile')
    if family == 'flow':
        balance = {}
        for value, amount in zip(primary, nums):
            balance[value['entity']] = balance.get(value['entity'], Decimal(0)) - amount
            balance[value['category']] = balance.get(value['category'], Decimal(0)) + amount
        internal = {v['entity'] for v in primary} & {v['category'] for v in primary}
        require(all(balance[node] == 0 for node in internal), 'Unexplained Sankey loss/gain')
    if key in ('dumbbell_chart', 'butterfly_chart'):
        groups = {}
        for value in primary:
            groups.setdefault(value['category'], set()).add(value['series'])
        require(all(len(group) == 2 for group in groups.values()), 'Paired comparison lacks two observed states')


def load_contract(project):
    text = (project / 'design_spec.md').read_text(encoding='utf-8')
    matches = LOCK_RE.findall(text)
    declared = re.search(r'^content_contract:\s*(\S+)\s*$', text, re.M)
    require(not declared or declared[1] == '1', 'Unsupported content contract version')
    if not declared and not matches:
        return None
    require(declared and matches, 'Incomplete content contract: marker and page locks required')
    pages = [json.loads(match) for match in matches]
    require(len({p['page'] for p in pages}) == len(pages), 'Duplicate page IDs')
    require(len({p['svg'] for p in pages}) == len(pages), 'Duplicate SVG filenames')
    for page in pages:
        require(Path(page['svg']).name == page['svg'] and page['svg'].endswith('.svg'), 'SVG must be a basename')
    return pages


def check_page(page, blocks, catalog):
    for field in ('facts', 'derived', 'conclusions', 'unresolved', 'visualizations', 'required'):
        require(isinstance(page[field], list), f'Missing list: {field}')
    values = {}
    for fact in page['facts']:
        require(fact['id'] not in values, 'Duplicate fact ID')
        evidence(fact, blocks)
        for field in ('text', 'entity', 'unit', 'period', 'scope', 'status'):
            require(isinstance(fact[field], str) and fact[field], f'Fact needs {field}; use explicit n/a if inapplicable')
        if 'value' in fact and fact['value'] is not None and fact.get('numeric', True):
            parsed = parse_source_number(fact['raw'], fact['locale'])
            require(parsed == number(fact['value']), 'Normalized number differs from raw source')
            require(any(fact['raw'].strip().rstrip('%') in re.findall(r'(?<![\w])[-+]?\d+(?:[.,]\d+)*', ref['quote']) for ref in fact['sources']), 'Raw numeric token absent from quoted source')
        elif fact.get('value') is not None:
            require(isinstance(fact['value'], str) and not re.fullmatch(r'[+-]?[\d.,]+', fact['value']), 'Numeric value cannot opt out of source-number validation')
        values[fact['id']] = fact
    for item in page['derived']:
        require(item['id'] not in values, 'Duplicate derived ID')
        require(all(key in values for key in item['inputs']), 'Unknown/forward calculation input')
        require(all(values[key]['status'] not in ('unverified', 'conflict', 'missing') for key in item['inputs']), 'Calculation uses uncertain source')
        require(item.get('meaning') and item.get('compatibility'), 'Calculation needs meaning and compatibility explanation')
        for field in ('entity', 'unit', 'period', 'scope', 'status', 'text'):
            require(item.get(field), f'Derived fact needs {field}')
        inputs = [values[key] for key in item['inputs']]
        if item['operation'] != 'convert_unit':
            require(len({x['unit'] for x in inputs}) == 1, 'Calculation inputs have mixed units')
        if item['operation'] == 'percentage_points':
            require(all(x['unit'] == '%' for x in inputs) and item['unit'] == 'pp', 'Percentage points require percentage inputs and pp output')
        if item['operation'] == 'percent':
            require(item['unit'] == '%', 'Percent calculation must use % unit')
        exact = calculate(item, values)
        values[item['id']] = dict(item, value=exact, display_value=item['value'])
    for conclusion in page['conclusions']:
        require(conclusion['id'] not in values, 'Duplicate conclusion ID')
        require(conclusion.get('text') and conclusion.get('reason'), 'Conclusion needs text and support explanation')
        kind = conclusion.get('kind', 'supported')
        require(kind in ('supported', 'editorial', 'model-analysis'), 'Unknown conclusion kind')
        if kind != 'editorial':
            require(conclusion.get('supports') and all(key in values for key in conclusion['supports']), 'Unsupported conclusion')
        if kind == 'model-analysis':
            require(conclusion.get('user_request') and conclusion.get('display_label'), 'Model analysis must be requested and visibly identified')
        values[conclusion['id']] = conclusion
    for issue in page['unresolved']:
        require(issue.get('description') and issue.get('resolution') in ('excluded', 'flagged', 'user-resolved'), 'Unresolved conflict handling missing')
        require(not issue.get('material') or issue['resolution'] == 'user-resolved', 'Material conflict requires user clarification')
    require(all(key in values for key in page['required']), 'Unknown required content ID')
    require(len({v['id'] for v in page['visualizations']}) == len(page['visualizations']), 'Duplicate visualization ID')
    for viz in page['visualizations']:
        chart_check(viz, values, catalog)
    return values


def svg_check(path, page, values):
    root = ET.parse(path).getroot()
    require(root.get('data-content-contract') == '1', 'SVG lacks content contract marker')
    seen = set()
    seen_numbers = set()
    visible_text = {}
    elements = {}
    charts = {v['id']: v for v in page['visualizations'] if v['template'] != 'none'}
    seen_charts = set()
    def walk(element, inherited=(), hidden=False):
        hidden = hidden or element.get('display') == 'none' or element.get('visibility') == 'hidden' or element.get('opacity') == '0' or element.tag.rsplit('}', 1)[-1] in ('defs', 'metadata', 'title', 'desc')
        refs = tuple(element.get('data-claims', '').split()) or inherited
        require(all(ref in values for ref in refs), 'SVG references unknown claims')
        if element.get('id'):
            require(element.get('id') not in elements, 'Duplicate SVG element ID')
            elements[element.get('id')] = element
        if element.get('data-chart'):
            require(element.get('data-chart') in charts, 'Unplanned chart in SVG')
            seen_charts.add(element.get('data-chart'))
        tag = element.tag.rsplit('}', 1)[-1]
        if tag == 'text' and ''.join(element.itertext()).strip():
            if not hidden:
                seen.update(refs)
            chrome = element.get('data-chrome')
            if chrome:
                text = ''.join(element.itertext()).strip()
                require((chrome == 'page-number' and text.isdigit()) or
                        (chrome == 'logo' and text.lower() == 'viettel'), 'Invalid chrome exemption')
            else:
                text = ''.join(element.itertext())
                require(refs, f'Unbound SVG text: {text[:80]}')
                numeric_tokens = lambda t: set(re.findall(r'(?<![\w])[-+]?\d+(?:[.,]\d+)*', t))
                allowed = set()
                for ref in refs:
                    item = values[ref]
                    allowed.update(numeric_tokens(item.get('text', '')))
                    if item.get('raw'):
                        allowed.add(item['raw'].rstrip('%'))
                    if isinstance(item.get('value'), (int, float)):
                        allowed.update(numeric_tokens(str(item['value'])))
                # Preserve alternate locale formatting without permitting a new value.
                def numeric_key(token):
                    try:
                        return parse_source_number(token, page.get('display_locale', 'vi'))
                    except ValueError:
                        return token
                displayed = {numeric_key(t) for t in numeric_tokens(text)}
                if not hidden:
                    for ref in refs:
                        item = values[ref]
                        visible_text.setdefault(ref, []).append(text)
                        if item.get('value') is not None and item.get('numeric', True):
                            if number(item.get('display_value', item['value'])) in displayed:
                                seen_numbers.add(ref)
                require(displayed <= {numeric_key(t) for t in allowed},
                        f'Unapproved numeric token in SVG: {text[:80]}')
        for child in element:
            walk(child, refs, hidden)
    walk(root)
    require(set(page['required']) <= seen, 'Required content missing from SVG')
    require(seen_charts == set(charts), 'Planned chart missing from SVG')
    for ref in page['required']:
        item = values[ref]
        if item.get('value') is not None and item.get('numeric', True):
            require(ref in seen_numbers, f'Required numeric value not visible: {ref}')
    for ref, item in values.items():
        if item.get('kind') == 'model-analysis' and ref in seen:
            require(item['display_label'] in ' '.join(visible_text.get(ref, [])), 'Model analysis label not visible')
    # Optional machine-verifiable scalar geometry, with inputs from the lock, never labels.
    # Other geometry is verified using verify-charts and recorded in the semantic review.
    for viz in charts.values():
        for mark in viz.get('geometry', []):
            require(mark['element'] in elements, 'Missing chart mark')
            require(mark['fact'] in values, 'Unknown geometry input')
            lo, hi = map(number, mark['domain'])
            a, b = map(number, mark['range'])
            require(hi > lo, 'Invalid geometry domain')
            ratio = (number(values[mark['fact']]['value']) - lo) / (hi - lo)
            if mark.get('scale', 'linear') == 'area-radius':
                require(ratio >= 0, 'Negative area scale')
                ratio = Decimal(str(math.sqrt(float(ratio))))
            else:
                require(mark.get('scale', 'linear') == 'linear', 'Unsupported geometry scale')
            expected = a + ratio * (b - a)
            actual = number(elements[mark['element']].get(mark['attribute']))
            require(abs(expected - actual) <= Decimal('0.5'), f"Chart geometry differs from locked data: {mark['element']}")


def snapshot(project, pages):
    paths = [project / 'design_spec.md', project / 'sources/source_index.json']
    if (project / 'spec_lock.md').exists():
        paths.append(project / 'spec_lock.md')
    paths += [project / 'svg_output' / p['svg'] for p in pages]
    index = json.loads(paths[1].read_text(encoding='utf-8'))
    paths += [project / s['path'] for s in index['sources'].values()]
    return {p.relative_to(project).as_posix(): sha256(p) for p in paths}


def validate(project, stage='export'):
    project = Path(project).resolve()
    spec = project / 'design_spec.md'
    pages = load_contract(project) if spec.exists() else None
    if pages is None:
        readme = project / 'README.md'
        required = readme.exists() and bool(re.search(r'^- Content contract:', readme.read_text(encoding='utf-8'), re.M))
        require(not required, 'New project requires version-1 content locks; cannot export as legacy')
        marked = any('data-content-contract' in p.read_text(encoding='utf-8') for p in (project / 'svg_output').glob('*.svg'))
        require(not marked and not (project / 'content_review.json').exists(), 'Grounded project lost its content contract')
        return None
    blocks = read_blocks(project)
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))['charts']
    if stage != 'plan':
        actual = {p.name for p in (project / 'svg_output').glob('*.svg')}
        require(actual == {p['svg'] for p in pages}, 'SVG inventory differs from content lock')
    for page in pages:
        require(page.get("source_index_sha256") == sha256(project / "sources/source_index.json"), "Content lock source index changed; re-ground before updating hash")
        try:
            values = check_page(page, blocks, catalog)
            if stage != 'plan':
                svg_check(project / 'svg_output' / page['svg'], page, values)
        except (ValueError, KeyError, TypeError, InvalidOperation) as exc:
            raise ValueError(f"{page['page']}: {exc}") from exc
    if stage == 'export':
        receipt = json.loads((project / 'content_review.json').read_text(encoding='utf-8'))
        require(receipt['version'] == 1 and receipt['hashes'] == snapshot(project, pages), 'Missing/stale content review; re-review after changes')
        review_entries(receipt['pages'], pages)
    return pages


def review_entries(entries, pages):
    require(set(entries) == {p['page'] for p in pages}, 'Review must cover every page')
    for page in pages:
        result = entries[page['page']]
        require(result.get('status') == 'pass' and result.get('reviewer') and result.get('notes'), 'Review requires reviewer, notes and pass status')
        required = ['source_meaning', 'numbers_units', 'scope_period_status', 'titles_conclusions', 'required_content', 'visual_encoding']
        require(all(result.get(check) is True for check in required), 'Semantic review incomplete')
        charts = {v['id'] for v in page['visualizations'] if v['template'] != 'none'}
        require(set(result.get('charts', {})) == charts, 'Chart review incomplete')
        require(all(isinstance(v, str) and v.strip() for v in result.get('charts', {}).values()), 'Chart review needs evidence/formulas or structural rationale')


def export_gate(svg_files):
    """Shared library entrypoint: fail closed for grounded projects, warn for legacy."""
    try:
        roots = {Path(path).resolve().parent.parent for path in svg_files}
        if len(roots) != 1:
            require(all(validate(root) is None for root in roots), 'Cannot mix grounded export projects')
            print('[WARN] Legacy export: content has not passed source-grounded verification.')
            return True
        project = roots.pop()
        pages = validate(project)
        if pages is None:
            print('[WARN] Legacy export: content has not passed source-grounded verification.')
        else:
            require({Path(p).resolve() for p in svg_files} ==
                    {(project / 'svg_output' / p['svg']).resolve() for p in pages}, 'Export subset differs from reviewed deck')
        return True
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, InvalidOperation) as exc:
        print(f'[ERROR] Content gate: {exc}')
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--stage', choices=['plan', 'svg', 'export'], default='export')
    parser.add_argument('--record-review', type=Path, help='Reviewed page findings JSON, keyed by page ID; never auto-approve')
    args = parser.parse_args()
    try:
        pages = validate(args.project, 'svg' if args.record_review else args.stage)
        if args.record_review:
            require(pages is not None, 'Legacy project has no content lock to review')
            entries = json.loads(args.record_review.read_text(encoding='utf-8'))
            review_entries(entries, pages)
            receipt = {'version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
                       'hashes': snapshot(args.project.resolve(), pages), 'pages': entries}
            (args.project / 'content_review.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print('PASS' if pages is not None else 'LEGACY: no source-grounded content contract')
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, InvalidOperation) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
