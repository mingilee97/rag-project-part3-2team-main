"""외부 모델 호출 없이 합성 입력으로 메인 실행 흐름을 점검한다."""
import csv
import importlib
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pymupdf

from rfp_rag import answer, index, memory, pipeline, providers, retrieve, route, settings
from rfp_rag.ingest import chunk, clean, enrich


def main():
    root = Path(__file__).resolve().parent
    for path in (root / 'rfp_rag').rglob('*.py'):
        name = '.'.join(path.relative_to(root).with_suffix('').parts).removesuffix('.__init__')
        module = importlib.import_module(name)
        assert Path(module.__file__).resolve().is_relative_to(root)
    with patch.dict(os.environ, {'RFP_DATA_DIR': ''}):
        assert settings.load()['data_dir'] == root / 'data'
    with patch.dict(os.environ, {'RFP_DATA_DIR': 'relative-data'}):
        assert settings.load()['data_dir'] == root / 'relative-data'
    assert clean.page_num('Page 7\n본문 7\n7', 'pdf') == '본문 7'
    assert answer.unsupported('예산은 2000원이다.', '예산은 1000원이다.') == ['2,000']
    assert answer.unsupported('예산은 1000원이다.', '예산은 1000원이다.') == []

    with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'RFP_DATA_DIR': folder}):
        raw = Path(folder) / 'raw'
        raw.mkdir()
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((72, 72), 'Budget is 1000 won.\nSFR-001: login function.\n' + 'Main requirements. ' * 20)
            pdf.save(raw / 'sample.pdf')
        row = {'파일명': 'sample.pdf', '공고 번호': 'TEST-001', '발주 기관': '테스트기관',
               '사업명': '합성시스템', '사업 금액': '1000', '입찰 참여 마감일': '2030-01-01',
               '텍스트': '', '공개 일자': '', '입찰 참여 시작일': '', '사업 요약': ''}
        with (raw / 'data_list.csv').open('w', encoding='utf-8-sig', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
        cfg = settings.load('07_verify')
        assert cfg['data_dir'] == Path(folder) and cfg['pipeline']['verify']
        docs, chunks = chunk.build(cfg)
        assert len(docs) == 1 and not docs[0]['fallback']
        assert all(chunks.values()) and '1000' in docs[0]['text']
        assert route.name_filter('테스트기관 합성시스템') == ['TEST-001']
        assert 'TEST-001' in answer.doc_info(cfg)
        assert enrich.body_head('1. 사업개요\n본문').startswith('1. 사업개요')
        retrieved = [index.to_doc(chunks['fixed'][0])]
        fake_llm = SimpleNamespace(invoke=lambda messages: SimpleNamespace(content=json.dumps(
            {'answer': '예산은 1000원이다.', 'evidence_ids': [1], 'found': True})))
        fake_store = SimpleNamespace(get=lambda **kw: {'ids': kw['ids'], 'embeddings': [[1.0, 0.0] for _ in kw['ids']]})
        fake_emb = SimpleNamespace(embed_query=lambda question: [1.0, 0.0])
        cfg['pipeline'].update(route=False, use_enriched=False)
        with patch.object(retrieve, 'retrieve', return_value=retrieved), \
             patch.object(index, 'open_chroma', return_value=fake_store), \
             patch.object(index, 'get_embeddings', return_value=fake_emb), \
             patch.object(providers, 'get_llm', return_value=fake_llm) as model:
            state = memory.new_state()
            result = pipeline.ask('예산을 알려 줘.', state, cfg)
            assert result['found'] and result['answer'] == '예산은 1000원이다.'
            assert result['evidence'][0]['doc_id'] == 'TEST-001'
            assert result['given'] == result['evidence'] and state['history']
            calls = model.call_count
            weak_doc = index.to_doc(chunks['fixed'][0])
            weak_doc.metadata['score'] = 0.1
            rejected = pipeline._answer('질문', [weak_doc], cfg)
            assert not rejected['found'] and model.call_count == calls
        route._doc_table.cache_clear()
        answer._info.cache_clear()
    print('합성 입력 점검 통과: 모듈 연결, 설정, PDF 전처리, 청크, 이름 검색, 답변 근거, 약한 근거 거절, 대화 상태')


if __name__ == '__main__':
    main()
