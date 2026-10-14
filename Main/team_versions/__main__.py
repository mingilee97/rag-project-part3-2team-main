"""버전 선택·설정 확인만 수행한다. 실행 모델은 호출하지 않는다."""
import argparse
import json
from .runtime import load_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--version', choices=['baseline', 'v1', 'v2', 'v3', 'v4'])
    args = parser.parse_args()
    if args.version:
        print(json.dumps(load_config(args.version), ensure_ascii=False, indent=2))
    else:
        for version in ('baseline', 'v1', 'v2', 'v3', 'v4'):
            config = load_config(version)
            print(config['id'], config['label'], config['status'])


if __name__ == '__main__':
    main()
