# minhyup/Version_1

출처: `seolwoom/rag-for-proposals` · commit `10882e31f1945369b68e38843a8f64ea777d3ffb`

구분: 원본 보존 / 형식만 변환 · 미채택

## 원본 → 모듈

| 단계 | 실제 코드 |
|---|---|
| parser | 이 버전에서 미확보/미변환 |
| chunking | [rag_chunking.py](rag_chunking.py) |
| embedding | 이 버전에서 미확보/미변환 |
| retrieval | [rag_reranking.py](rag_reranking.py) |
| generation | [rag_context.py](rag_context.py) |
| verification | 이 버전에서 미확보/미변환 |

실행: python versions/pipelines/select.py --version minhyup/Version_1 --check; 실제 호출 규약은 각 함수와 source-provenance.json을 확인합니다.

확보되지 않은 부분:

- parser 단계 전체 파이프라인 연결 미완료
- embedding 단계 전체 파이프라인 연결 미완료
- verification 단계 전체 파이프라인 연결 미완료
