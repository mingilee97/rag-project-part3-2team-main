# minhyup/Version_2

출처: `seolwoom/rag-for-proposals` · commit `10882e31f1945369b68e38843a8f64ea777d3ffb`

구분: 알고리즘 개선 후보; 개선 효과 미입증 · 미채택

## 원본 → 모듈

| 단계 | 실제 코드 |
|---|---|
| parser | 이 버전에서 미확보/미변환 |
| chunking | [rag_chunking.py](rag_chunking.py), [chunking.py](chunking.py) |
| embedding | 이 버전에서 미확보/미변환 |
| retrieval | 이 버전에서 미확보/미변환 |
| generation | 이 버전에서 미확보/미변환 |
| verification | 이 버전에서 미확보/미변환 |

실행: from versions.pipelines.minhyup.Version_2.chunking import chunk_teammate; chunk_teammate(doc,1000,200). 품질 평가를 호출하지 않습니다.

확보되지 않은 부분:

- 독립 embedding/retrieval/generation/verification 연결 미완료
