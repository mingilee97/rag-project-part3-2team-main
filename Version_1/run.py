"""Version 1의 설정을 표시한다. 외부 공급자는 실행하지 않는다."""
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Baseline'))
from team_versions import load_config
if __name__ == '__main__':
    print(json.dumps(load_config('v1'), ensure_ascii=False, indent=2))
