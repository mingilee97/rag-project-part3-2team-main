"""Version 2 원본 단계와 Haiku 생성 연결의 명시적 실행 입구."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version_runtime import cli
if __name__ == '__main__':
    cli('v2')
