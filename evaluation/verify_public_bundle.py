"""공개 허용목록·해시·선정 스키마·비밀 패턴을 검사한다. 검출 값은 출력하지 않는다."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
AREAS = ['candidates', 'dashboard', 'evaluation', 'versions']
SUFFIXES = {'.py', '.ts', '.css', '.mjs', '.html', '.md', '.json'}
SECRET_PATTERNS = [
    ('private-key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('openai-key', re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}')),
    ('github-token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{24,})')),
    ('google-key', re.compile(r'\bAIza[A-Za-z0-9_-]{30,}')),
    ('huggingface-token', re.compile(r'\bhf_[A-Za-z0-9]{24,}')),
    ('private-sheet-url', re.compile(r'https://docs\.google\.com/(?:spreadsheets|document|presentation)/d/')),
    ('personal-absolute-path', re.compile(r'(?:[A-Z]:[/\\]+Users[/\\]+[A-Z0-9_-]+[/\\]+|/(?:home|Users)/[A-Z0-9_-]+/)', re.I)),
    ('local-trace-asset', re.compile(r'(?:^|[/\\])(?:items\.local|.*\.local\.(?:json|jsonl|csv|npy|log))$')),
]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))


def main():
    issues, paths = [], []
    for area in AREAS:
        paths.extend(p for p in (ROOT / area).rglob('*') if p.is_file())
    paths += [ROOT / 'README.md', ROOT / 'AGENTS.md']
    paths += list((ROOT / 'docs').glob('*20261009.md'))
    paths += [ROOT / 'docs/버전-비교-근거.md', ROOT / '.github/workflows/review-bundle.yml']
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix not in SUFFIXES | {'.yml'} or path.stat().st_size > 1_000_000:
            issues.append({'file': rel, 'kind': 'forbidden-type-or-size'}); continue
        try: content = path.read_text(encoding='utf-8')
        except UnicodeError:
            issues.append({'file': rel, 'kind': 'non-text-asset'}); continue
        for kind, pattern in SECRET_PATTERNS:
            # 검출식과 설명에 포함된 이름은 실제 비밀 값으로 취급하지 않는다.
            if pattern.search(content) or (kind == 'local-trace-asset' and pattern.search(rel)):
                issues.append({'file': rel, 'kind': kind})
        if path.suffix == '.py':
            tree = ast.parse(content, filename=rel)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    names = [n.id for n in node.targets if isinstance(n, ast.Name)]
                    if any(name.endswith(('API_KEY', 'ACCESS_TOKEN', 'SECRET_KEY')) for name in names) and node.value.value.strip():
                        issues.append({'file': rel, 'kind': 'literal-secret-assignment'})
        if path.suffix == '.json': read(path)
    for version in read(ROOT / 'dashboard/versions/catalog.json')['versions']:
        manifest = read(ROOT / 'dashboard' / version['manifest'])
        assert len(manifest['published_components']) == 4
        assert not manifest['full_original_checkpoint_recoverable_from_public_repo']
        for item in manifest['published_components']:
            assert sha(ROOT / item['path']) == item['sha256'], item['path']
    candidate = read(ROOT / 'candidates/minhyup/10882e3/provenance.json')
    assert re.fullmatch(r'[a-f0-9]{40}', candidate['commit'])
    for item in candidate['files']:
        assert sha(ROOT / item['path']) == item['sha256'], item['path']
        body = (ROOT / item['path']).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() == item['original_git_blob_sha']
    cleaning = read(ROOT / 'candidates/hyunkyung/5e79101/provenance.json')
    assert sha(ROOT / 'candidates/hyunkyung/5e79101/cleaning.py') == cleaning['exported_file_sha256']
    models = read(ROOT / 'versions/models.json')
    selection = read(ROOT / 'versions/selection.json')
    assert models['final_model_selection'] == selection['status']
    assert selection['currently_retained_baseline'] == 'main-07_verify-423a32a'
    assert selection['adopted_new_candidate'] is None and not selection['production_changed']
    main = next(v for v in models['versions'] if v['role'] == 'currently_retained_baseline')
    assert hashlib.sha256((ROOT / main['config']).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == main['config_sha256_lf']
    results = read(ROOT / 'evaluation/aggregates/20261008-retrieval.json')
    assert results['bm25']['corpus_documents'] == 100 and results['dense']['corpus_documents'] == 14
    assert results['denominators']['eligible_quote_spans'] == 508 and results['denominators']['raw_present_spans'] == 491
    pilot = read(ROOT / 'evaluation/aggregates/20261009-bge-pilot.json')
    assert len(pilot['aggregates']) == 6 and pilot['generator_calls'] == 0 and pilot['gpu_calls'] == 0
    assert all(r['questions'] == 4 and r['budget_overflows'] == 0 for r in pilot['aggregates'])
    artifact_manifest = ROOT / 'versions/public-artifacts.json'
    if artifact_manifest.exists():
        for item in read(artifact_manifest)['files']:
            assert hashlib.sha256((ROOT / item['path']).read_bytes().replace(b'\r\n', b'\n')).hexdigest() == item['sha256_lf'], item['path']
    if issues:
        print(json.dumps({'status': 'blocked', 'issues': issues}, ensure_ascii=False))
        raise SystemExit(1)
    print(json.dumps({'status': 'passed', 'inspected_public_files': len(paths), 'ui_versions': 2,
        'secret_values_not_output': True, 'model_selection': selection['status']}, ensure_ascii=False))


if __name__ == '__main__': main()
