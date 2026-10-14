"""포함된 원본 단계 모듈을 실행한다. 실제 공급자는 명시적으로 준비한다."""
import argparse
import ast
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import time
from typing import List
import unicodedata

ROOT=Path(__file__).resolve().parent
STAGES={'parser':'parser','chunker':'chunking','embedder':'embedding','retriever':'retrieval','generator':'generation'}

def config(version):
    if version not in {'v1','v2','v3','v4'}: raise ValueError('v1..v4 중 선택하세요.')
    return json.loads((ROOT/f'Version_{version[1:]}'/'version.json').read_text(encoding='utf-8'))

def verify(version):
    folder=ROOT/f'Version_{version[1:]}'
    provenance=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    for name,digest in provenance['bundled_files'].items():
        path=folder/name
        if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=digest:
            raise ValueError(f'고정 접수 코드와 다릅니다: {name}')
    return provenance

class VersionSession:
    def __init__(self,version,providers=None):
        self.config=config(version)
        provenance=verify(version)
        self.namespace=dict(defaultdict=defaultdict,datetime=datetime,timezone=timezone,json=json,
            os=os,Path=Path,re=re,struct=struct,time=time,List=List,unicodedata=unicodedata)
        from langchain_core.embeddings import Embeddings
        self.namespace['Embeddings']=Embeddings
        self.namespace.update(providers or {})
        self.stages=set()
        for name in sorted(provenance['bundled_files']):
            path=ROOT/f'Version_{version[1:]}'/name
            tree=ast.parse(path.read_text(encoding='utf-8'))
            if any(not isinstance(n,(ast.FunctionDef,ast.ClassDef)) and not
                   (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))
                   for n in tree.body): raise ValueError('단계 모듈에 자동 실행 구문이 있습니다.')
            exec(compile(tree,str(path),'exec'),self.namespace)
            self.stages.add(path.stem)
    def run(self,stage):
        name=STAGES.get(stage,stage)
        if name not in self.stages: raise ValueError('이 원본에 없는 단계입니다.')
        self.call('stage_'+name)
        return self.namespace
    def call(self,name,*args,**kwargs):
        function=self.namespace.get(name)
        if not callable(function) or name.startswith('__'): raise ValueError('원본 함수를 선택하세요.')
        return function(*args,**kwargs)
    def connect_haiku(self):
        sys.path.insert(0,str(ROOT/'Baseline'))
        from rfp_rag.providers import get_llm
        model=get_llm({'llm':self.config['deployment_generator']},purpose='team_generation')
        self.namespace.update(chat_model=model,llm=model,method='basic')
        return model
    def execute(self,question):
        version=self.config['id']
        if version in ('v3','v4'): self.run('parser_fix')
        self.run('parser')
        if version in ('v1','v2'): self.run('cleaning')
        self.run('chunker'); self.run('embedder'); self.connect_haiku()
        if version in ('v1','v2'):
            self.run('retriever'); self.run('generator')
            if version=='v2':
                return self.call('answer_question',question,bm25_mode='kiwi')
            return self.call('answer_question',question)
        self.run('generator'); self.run('retriever')
        return self.namespace['hybrid_retrieval_chain'].invoke(question)

def cli(fixed_version=None):
    parser=argparse.ArgumentParser()
    if fixed_version is None: parser.add_argument('--version',choices=['v1','v2','v3','v4'],required=True)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--input-dir',type=Path)
    parser.add_argument('--metadata',type=Path)
    parser.add_argument('--ask')
    args=parser.parse_args(); version=fixed_version or args.version
    if args.smoke:
        from version_smoke import smoke
        print(json.dumps(smoke(version),ensure_ascii=False)); return
    if args.ask:
        if args.input_dir is None: parser.error('--input-dir가 필요합니다.')
        if not os.environ.get('ANTHROPIC_API_KEY'): parser.error('ANTHROPIC_API_KEY를 로컬 환경에 설정하세요.')
        from version_inputs import prepare
        session=VersionSession(version,prepare(version,args.input_dir,args.metadata))
        print(json.dumps(session.execute(args.ask),ensure_ascii=False,default=str)); return
    if args.check:
        provenance=verify(version)
        print(json.dumps({'version':version,'files':len(provenance['bundled_files']),'status':'passed','model_calls':0})); return
    print(json.dumps(config(version),ensure_ascii=False,indent=2))
