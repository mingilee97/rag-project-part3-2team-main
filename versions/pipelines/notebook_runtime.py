"""접수 코드의 상태와 공급자를 인스턴스마다 분리한다. 외부 공급자는 자동 연결하지 않는다."""
import ast
from collections import defaultdict
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import re
import struct
import time
from typing import List
import unicodedata

ROOT = Path(__file__).resolve().parent
VARIANTS = {'hyunkyung': {'business', 'kiwi'}, 'minhyup': {'openai', 'local'}}


class NotebookRuntime:
    def __init__(self, member, variant, providers):
        if member not in VARIANTS or variant not in VARIANTS[member]:
            raise ValueError('등록한 공개 노트북 흐름을 선택하세요.')
        self.member, self.variant = member, variant
        self.namespace = dict(defaultdict=defaultdict, datetime=datetime, timezone=timezone,
                              json=json, os=os, Path=Path, re=re, struct=struct, time=time,
                              List=List, unicodedata=unicodedata)
        self.namespace.update(providers)
        self.stages = set()
        for path in sorted((ROOT / member / 'Version_3' / variant).glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            if any(not isinstance(n, (ast.FunctionDef, ast.ClassDef)) and
                   not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))
                   for n in tree.body):
                raise ValueError('접수 모듈에 자동 실행 구문이 있습니다.')
            # 고정 접수 파일의 정의만 로드한다. 입력·공급자 코드를 문자열로 실행하지 않는다.
            exec(compile(tree, str(path), 'exec'), self.namespace)
            self.stages.add(path.stem)

    def run(self, stage):
        if stage not in self.stages:
            raise ValueError('이 원본에 없는 단계입니다.')
        function = self.namespace.get('stage_' + stage)
        if function is None:
            raise ValueError('함수만 있는 단계입니다. call로 원본 함수를 호출하세요.')
        function()
        return self.namespace

    def call(self, function, *args, **kwargs):
        target = self.namespace.get(function)
        if not callable(target) or function.startswith('__'):
            raise ValueError('등록한 원본 함수를 선택하세요.')
        return target(*args, **kwargs)


def minhyup_components():
    """명시적으로 선택했을 때만 원본 청킹·문맥·재순위 부품을 가져온다."""
    prefix = 'versions.pipelines.minhyup.Version_3.'
    chunking, reranking, context = [importlib.import_module(prefix + name)
                                   for name in ('rag_chunking', 'rag_reranking', 'rag_context')]
    return {**{name: getattr(chunking, name) for name in ('build_parent_children', 'expand_parents', 'markdown_table_count')},
            **{name: getattr(reranking, name) for name in ('rerank_to_parents', 'RERANKER_MODEL', 'CANDIDATE_K', 'PARENT_K')},
            **{name: getattr(context, name) for name in ('format_context', 'CONTEXT_TOKEN_BUDGET', 'LLM_MODEL', 'OUTPUT_TOKEN_LIMIT')}}
