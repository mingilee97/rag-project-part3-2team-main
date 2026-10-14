"""Baseline/Main과 포함된 후보 버전을 선택한다. 실행은 명시적 --ask에 한정한다."""
from pathlib import Path
import sys

import argparse
import json

ROOT=Path(__file__).resolve().parent

def main():
    if '--version' in sys.argv and sys.argv.index('--version')+1<len(sys.argv) and sys.argv[sys.argv.index('--version')+1] in ('v1','v2','v3','v4'):
        from version_runtime import cli
        cli(); return
    parser=argparse.ArgumentParser()
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--version',choices=['baseline','main'])
    args=parser.parse_args()
    if args.version:
        folder='Baseline' if args.version=='baseline' else 'Main'
        print(json.dumps({'folder':folder,'config':json.loads((ROOT/folder/'version.json').read_text(encoding='utf-8'))},ensure_ascii=False,indent=2))
    else:
        print('baseline Baseline 기준 보존\nmain Main 팀 공동 개선')
        from version_runtime import config
        for version in ('v1','v2','v3','v4'):
            print(version,config(version)['label'],config(version)['status'])

if __name__ == '__main__':
    main()
