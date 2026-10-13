"""버전 목록·출처·파일 해시를 확인합니다. 모델이나 원본 노트북을 실행하지 않습니다."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = Path(__file__).with_name('index.json')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--version')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    versions = json.loads(INDEX.read_text(encoding='utf-8'))['versions']
    if args.list or not args.version:
        for version in versions:
            print(version['id'], version['change_kind'], version['adoption'])
        return
    match = next((v for v in versions if v['id'] == args.version), None)
    if match is None:
        parser.error('등록하지 않은 버전입니다.')
    if args.check:
        for item in match['files']:
            file = ROOT / item['module']
            assert hashlib.sha256(file.read_bytes()).hexdigest() == item['sha256'], item['module']
            if file.suffix == '.py':
                ast.parse(file.read_text(encoding='utf-8'))
        print(json.dumps({'status': 'passed', 'version': match['id'], 'files': len(match['files']), 'model_calls': 0}, ensure_ascii=False))
    else:
        print(json.dumps(match, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
