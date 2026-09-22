#!/usr/bin/env python3
"""Index immutable normalized-source spans; never rewrite source text."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_blocks(text):
    """Keep HTML table rows and Markdown rows addressable, including empty cells."""
    # Whole lines retain captions/context; table rows add precise locators without
    # removing the full table block (needed for merged/nested header relationships).
    for block in re.finditer(r'[^\n]+', text):
        if block.group().strip():
            yield block.start(), block.end()
    for row in re.finditer(r'<tr\b[^>]*>[\s\S]*?</tr>', text, re.I):
        yield row.start(), row.end()


def build_index(project):
    project = Path(project).resolve()
    records = {}
    paths = sorted((project / 'sources').rglob('*.md'))
    if not paths:
        raise ValueError('No normalized Markdown sources; preserve originals in sources/')
    for path in paths:
        content = path.read_text(encoding='utf-8')
        if not content.strip():
            raise ValueError(f'Empty source: {path}')
        relative = path.relative_to(project).as_posix()
        source_id = 'S' + hashlib.sha256(relative.encode()).hexdigest()[:12]
        records[source_id] = {
            'path': relative, 'sha256': sha256(path),
            'blocks': {f'{source_id}-B{i:04}': [start, end]
                       for i, (start, end) in enumerate(source_blocks(content), 1)},
        }
    result = {'version': 1, 'sources': records}
    (project / 'sources' / 'source_index.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def read_blocks(project):
    project = Path(project).resolve()
    index = json.loads((project / 'sources/source_index.json').read_text(encoding='utf-8'))
    if index['version'] != 1:
        raise ValueError('Unsupported source index')
    blocks = {}
    for record in index['sources'].values():
        path = (project / record['path']).resolve()
        if not path.is_relative_to(project / 'sources'):
            raise ValueError('Source path escapes sources/')
        if sha256(path) != record['sha256']:
            raise ValueError(f'Source changed; rebuild and re-ground content: {path.name}')
        text = path.read_text(encoding='utf-8')
        for key, (start, end) in record['blocks'].items():
            if not 0 <= start < end <= len(text):
                raise ValueError(f'Invalid source span: {key}')
            blocks[key] = text[start:end]
    return blocks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--show', help='Print one exact indexed block')
    args = parser.parse_args()
    if args.show:
        print(read_blocks(args.project)[args.show])
    else:
        index = build_index(args.project)
        print(f"Indexed {len(index['sources'])} sources")
