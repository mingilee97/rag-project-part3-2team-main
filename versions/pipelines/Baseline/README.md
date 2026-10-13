# Baseline

출처: `mingilee97/rag-project-part3-2team-main` · commit `bfca8f0508b65dfa97d9aa01da9a93ac188e68bd`

구분: 원본 보존 · 유지한 기준; 확정 우승 모델 아님

## 원본 → 모듈

| 단계 | 실제 코드 |
|---|---|
| parser | [rfp_rag/ingest/load.py](rfp_rag/ingest/load.py) |
| chunking | [rfp_rag/ingest/chunk.py](rfp_rag/ingest/chunk.py) |
| embedding | [rfp_rag/index.py](rfp_rag/index.py) |
| retrieval | [rfp_rag/retrieve.py](rfp_rag/retrieve.py), [rfp_rag/route.py](rfp_rag/route.py), [rfp_rag/memory.py](rfp_rag/memory.py) |
| generation | [rfp_rag/answer.py](rfp_rag/answer.py), [rfp_rag/providers.py](rfp_rag/providers.py), [rfp_rag/pipeline.py](rfp_rag/pipeline.py) |
| verification | [rfp_rag/answer.py](rfp_rag/answer.py), [rfp_rag/pipeline.py](rfp_rag/pipeline.py) |

실행: Baseline 폴더에서 README의 07_verify 명령을 실행합니다. 모델 호출은 별도 승인 필요.

확보되지 않은 부분:

- 별도 원본 문서·모델·색인 필요
