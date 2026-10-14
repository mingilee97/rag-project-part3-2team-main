"""선택과 import는 외부 모델을 실행하지 않는다. 원본 호출 규약은 유지한다."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = {'parser': 'parser', 'chunker': 'chunking', 'embedder': 'embedding',
          'retriever': 'retrieval', 'generator': 'generation'}


def load_config(version):
    if version not in {'baseline', 'v1', 'v2', 'v3', 'v4'}:
        raise ValueError('baseline 또는 v1부터 v4까지 선택하세요.')
    folder = 'Baseline' if version == 'baseline' else f'Version_{version[1:]}'
    return json.loads((ROOT / folder / 'version.json').read_text(encoding='utf-8'))


def _verified_bundle(config, bundle_root):
    if bundle_root is None:
        raise ValueError('권한을 확인한 로컬 모듈 폴더를 bundle_root로 전달하세요.')
    root = Path(bundle_root).resolve()
    pinned = json.loads((ROOT / 'Baseline/team_versions/source-lock.json').read_text(encoding='utf-8'))
    member, variant = config['runtime']['member'], config['runtime']['variant']
    directory = f'{member}/Version_3/{variant}'
    expected = {p: h for p, h in pinned['files'].items()
                if p == 'notebook_runtime.py' or p.startswith(directory + '/')}
    actual_paths = {p.relative_to(root).as_posix() for p in (root / directory).glob('*.py')}
    if actual_paths != {p for p in expected if p.startswith(directory + '/')}:
        raise ValueError('고정 원본과 모듈 파일 목록이 다릅니다.')
    for relative, digest in expected.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('모듈 경로가 로컬 폴더를 벗어났습니다.')
        content = path.read_bytes().replace(b'\r\n', b'\n')
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError(f'고정 원본과 파일 해시가 다릅니다: {relative}')
    return root / 'notebook_runtime.py'


class VersionSession:
    """공통 run/call 입구에서 각 원본의 인자와 반환값을 유지한다."""
    def __init__(self, version, *, bundle_root=None, reuse_authorized=False, providers=None):
        self.config = load_config(version)
        self.engine = None
        if version != 'baseline':
            if not reuse_authorized:
                raise PermissionError('팀원 원본의 재사용 권한이 확인되지 않았습니다. 출처 문서를 확인하세요.')
            runtime_path = _verified_bundle(self.config, bundle_root)
            spec = importlib.util.spec_from_file_location('_pinned_notebook_runtime', runtime_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            runtime = self.config['runtime']
            self.engine = module.NotebookRuntime(runtime['member'], runtime['variant'], providers or {})

    def run(self, stage, *args, **kwargs):
        if stage not in STAGES:
            raise ValueError('parser/chunker/embedder/retriever/generator 중 선택하세요.')
        if self.engine is not None:
            if args or kwargs:
                raise TypeError('노트북 입력과 공급자는 생성할 때 providers로 전달하세요.')
            return self.engine.run(STAGES[stage])
        module_name, function = self.config['modules'][stage]
        return getattr(importlib.import_module(module_name), function)(*args, **kwargs)

    def call(self, function, *args, **kwargs):
        if self.engine is None:
            raise ValueError('Baseline은 run으로 각 모듈의 원래 인자를 전달하세요.')
        return self.engine.call(function, *args, **kwargs)

    def connect_haiku(self, api_key=None):
        """원본 검색·청킹은 유지하고 준비한 노트북의 생성 공급자만 바꾼다."""
        if self.engine is None:
            raise ValueError('Baseline은 settings.load(07_verify)의 기본 Anthropic 공급자를 사용합니다.')
        from rfp_rag.providers import get_llm
        llm = get_llm({'llm': self.config['deployment_generator']}, api_key=api_key, purpose='team_generation')
        self.engine.namespace.update(chat_model=llm, llm=llm, method='basic')
        return llm
