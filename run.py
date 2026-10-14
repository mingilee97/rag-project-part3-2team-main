"""Baseline 공통 선택기를 사용한다. 이 명령은 모델을 호출하지 않는다."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'Baseline'))
from team_versions.__main__ import main

if __name__ == '__main__':
    main()
