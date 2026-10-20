## LLM 기반 제안요청서 RAG

### 📌 제출 자료 바로가기

| 자료 | 바로가기 | 확인할 내용 |
|---|---|---|
| **최종 기술 리포트** | [**FINAL-02 최종본 PDF**](technical-reports/00_FINAL02_최종기술리포트_20261020.pdf) | 2026-10-20 최종 구성·선정 이유·결과·한계 |
| 소스와 실행 안내 | [실행 소스](rfp_rag/) · [설치와 실행](#설치와-실행) | 비공개 입력 자료 준비와 실행 명령 |
| 과거 기술 리포트 | [PDF 폴더](technical-reports/) · [날짜·판본·출처 목록](docs/기술리포트목록.md) | 과거 실험과 현재 최종본을 구분 |
| 개인별 협업일지 | **아래 팀원별 전체 표** | 작성자별 원본으로 바로 이동 |

### 팀원별 협업일지

| 팀원 | 확인된 원본 링크 | 확인 범위 |
|---|---|---|
| 이민기 | [개인 협업일지 시트](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=2053649411) | 기존 개인 탭, 별도 담당자가 최근 기록을 정리한 원본 |
| 김현경 | [데일리 협업일지](https://app.notion.com/p/3eb67f39201180a4b1dbec087503807a?v=3eb67f39201180d583d7000c73a17268) · [실험 문서](https://app.notion.com/p/3ec67f3920118072b687d3aaed1e4428) | 일지 본문에서 작성자 확인, 현재 게스트 열람 확인 |
| 김민협 | [기존 개인 시트](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=924303621) | 탭 출처 확인, 최신 개인 원문 여부는 확인 필요 |
| 이원영 | [기존 개인 시트](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=1041212623) | 탭 출처 확인, 최신 개인 원문 여부는 확인 필요 |
| 권유진 | [기존 개인 시트](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=1632189499) | 탭 출처 확인, 최신 개인 원문 여부는 확인 필요 |

익명·평가자 계정의 접근은 미확인입니다. 공식 제출 안내의 개인별 원본 링크 요건에 맞춰 연결했으며, 시트형 일지의 PDF 변환·첨부는 아직 완료되지 않았습니다. GitHub에서는 목차·표·접기로 이동할 수 있게 구성했고 팀원의 원문은 수정하지 않았습니다. [접근 조건과 VM 종료 후 보존](docs/협업일지와보존.md)

---

## 프로젝트 소개

공공 입찰 제안요청서(RFP) 100건에서 질문과 관련된 근거를 찾아 한국어로 답하는 **LLM 기반 RAG 시스템**입니다. HWP·PDF의 글과 표를 읽고, 긴 문서를 나눈 뒤 검색한 근거를 생성 모델에 전달합니다. 요구사항·예산·일정처럼 문서에 흩어진 정보를 확인하는 것이 목표입니다.

문서 처리·청킹·임베딩·검색·재정렬·생성·평가를 나눠 각 단계의 변경을 비교할 수 있게 정리했습니다. 현재 실행은 **FINAL-02 하나**이며, 모델명과 실험 수치는 아래에 당시 설정 그대로 남겼습니다. 다른 모델로 확장할 연결 지점은 있지만 모든 LLM을 모델명만 바꿔 사용할 수 있는 구현은 아닙니다.

## 목차

[아키텍처](#아키텍처) · [설치와 실행](#설치와-실행) · [모델 교체와 확장](#모델-교체와-확장) · [선정과 평가 이력](#선정과-평가-이력) · [결과와 한계](#결과와-한계) · [출처와 공개 범위](#출처와-공개-범위)

## 아키텍처

| 단계 | 처리 흐름 |
|---|---|
| 문서 준비 | HWP·PDF → 파싱 캐시·메타데이터 → 청킹 → 문서 임베딩·FAISS 색인 |
| 질문 처리 | 질문 → 사업 식별 → Dense·키워드 검색 → RRF 결합 → 재정렬 → 근거 선택 |
| 생성·평가 | 질문 + 선택한 근거 → LLM 답변 → 검색 지표와 답변 품질을 나누어 평가 |

사업을 식별하지 못하거나 여러 사업이 모호하게 걸리면 전체 문서에서 검색합니다. 현재 FINAL-02에는 사업명 청크 헤더와 질문 분해를 사용하지 않습니다.

| 역할 | 아키텍처에서 하는 일 | 현재 FINAL-02 실험 구성 |
|---|---|---|
| 문서 처리·청킹 | 본문·표를 읽고 검색 단위로 분할 | HwpHwpxLoader·pymupdf4llm, 1000/200, 제공 파싱 캐시 |
| 임베딩·색인 | 문서와 질문을 같은 벡터 공간으로 변환 | `dragonkue/BGE-m3-ko`, 정규화, FAISS |
| 검색·결합 | 의미·키워드 후보를 모아 순위 결합 | Dense 20 + Kiwi BM25 20, RRF k=60 |
| 재정렬 | 질문과 후보의 관련성을 다시 비교 | `BAAI/bge-reranker-v2-m3`, 최종 문맥 6개 |
| 생성 | 근거와 프롬프트로 답변 작성 | `claude-haiku-4-5-20251001`, Anthropic 연결 |
| 답변 평가 | 기준 답변과 사실·근거 충실도 비교 | `gemini-3.1-flash-lite`, Gemini Judge·RAGAS 0.3.9 |
| 검색 평가 | 근거 순위와 최종 문맥 포함률 계산 | Hit@5·MRR·근거 재현율; 생성 모델과 별도 계산 |

<details>
<summary>소스 구조 보기</summary>

| 경로 | 하는 일 |
|---|---|
| `rfp_rag/config.py` | 현재 모델 ID와 청킹·검색·생성 설정 |
| `rfp_rag/parsing.py`, `data.py` | HWP·PDF·캐시 읽기, 평가셋·메타데이터 검증 |
| `rfp_rag/chunking.py`, `embedding.py` | 문서 분할과 임베딩 연결 |
| `rfp_rag/routing.py`, `retrieval.py` | 사업 식별, Dense·BM25·RRF 검색 |
| `rfp_rag/reranking.py` | 재정렬 모델 연결과 후보 정렬 |
| `rfp_rag/generation.py`, `pipeline.py` | 생성 연결·프롬프트·답변 캐시·결과 기록 |
| `rfp_rag/metrics.py`, `evaluation.py`, `experiments.py` | 검색 지표·Judge·RAGAS·체크포인트 |
| `prompts/final02.txt` | 제공된 FINAL-02 프롬프트 원문 |
| `tests/` | 네트워크 없는 합성 검증 |
| `technical-reports/` | PDF만 모은 최종·과거 기술 리포트 |
| `docs/` | 일반 실행·출처·검증·과거 기록 안내 |

</details>

## 설치와 실행

Python 3.11 이상을 기준으로 합니다. 아래 설치는 사용자가 실행할 절차입니다. 이번 문서 정리에서는 설치·모델 다운로드·유료 API를 실행하지 않았습니다. GPU 환경과 고정 패키지 조합의 새 설치 호환성은 별도 확인이 필요합니다.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
# 원본 재현 가이드가 지정한 별도 설치 방법
python -m pip install --no-deps langchain-hwp-hwpx-loader==0.1.1
```

`.env.example`을 참고해 로컬 `.env`에 현재 연결에 필요한 `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`를 설정합니다. 키를 README·이슈·커밋에 적지 않습니다. `summary`, `check`, `--help`는 키를 읽거나 모델을 시작하지 않습니다.

원본 제공자에게 허가받은 다음 자료를 별도로 준비합니다. 이 저장소에는 원문·메타데이터 행·평가 질문·답변·벡터가 없습니다.

```text
data/
  data_list.csv
  dev_benchmark_v1.1.json
  raw/files/                    # HWP·PDF 100건
    parsed_results/success_files.json
```

같은 실험을 재현하려면 제공된 파싱 캐시를 사용해야 합니다. 다시 파싱하면 본문과 청크 수가 달라질 수 있습니다. `ask`도 원본과 같은 100문서 선택을 위해 비공개 평가셋과 메타데이터를 사용합니다.

```sh
# 실제 모델 질문: 임베딩·재정렬 모델을 받고 생성 API를 호출할 수 있습니다.
python -m rfp_rag ask --query "이 사업의 주요 요구사항을 설명해 줘."

# 검색·답변·Judge를 앞 3문항만 실행: 유료 호출이 있는 실행 시험입니다.
python final02.py base --limit 3 --out-dir results/FINAL-02-test

# 전체 재평가는 호출량과 예산을 확인한 뒤 별도로 실행합니다.
python final02.py base
python final02.py ragas
python final02.py summary

# 설치·모델·API 없이 실행하는 검증
python -B -m unittest discover -s tests -v
python -B -m rfp_rag check
```

`--data-dir`, `--metadata-csv`, `--benchmark`, `--out-dir`로 경로를 지정할 수 있습니다. 문항별 체크포인트와 다른 설정의 결과 폴더 재사용 차단을 유지했습니다. 청크·모델·프롬프트를 바꾸면 새 결과 폴더를 사용하세요. RAGAS는 지표마다 새 Gemini 클라이언트를 만들어 원본의 이벤트 루프 처리를 유지합니다.

## 모델 교체와 확장

현재 모델 ID는 [RagSettings](rfp_rag/config.py)에 모여 있습니다. CLI에 `--model`이나 공급자 선택 옵션은 없으며, 설정 기본값을 편집하거나 Python에서 `RagSettings`와 파이프라인을 구성하는 방식입니다. 아래의 ‘ID 변경’은 **현재 어댑터와 호환되는 모델에 한정**하며 새 모델의 실행을 검증했다는 뜻은 아닙니다.

| 바꿀 부분 | 설정으로 바꿀 수 있는 범위 | 추가 수정·확인이 필요한 경우 |
|---|---|---|
| 임베딩 | `embedding_model` 및 배치·정규화 설정. 현재 `HuggingFaceEmbeddings`와 호환되는 모델 | 외부 임베딩 API는 `embedding.py` 연결·키·의존성 수정 필요. 차원·정규화가 다른 기존 벡터와 혼용 불가 |
| 검색 | `dense_k`, `bm25_k`, `rrf_k`, `bm25_mode`의 `kiwi`/`current` | 다른 검색 엔진·형태소 분석기는 `retrieval.py` 수정 필요. 검색 개수 변경도 새 파이프라인에서 적용 |
| 재정렬 | `reranker_model`, `reranker_batch_size`, `final_context_count`. 현재 `CrossEncoder.rank()`와 호환되는 모델 | 외부 API나 다른 출력 형식은 `reranking.py` 어댑터 필요. 현재는 `corpus_id`를 반환하는 순위 결과 사용 |
| 생성 LLM | `generation_model`과 토큰·시간 제한·재시도. 현재 `ChatAnthropic`이 지원하는 모델 ID | 다른 공급자는 `generation.py`의 클라이언트·키·API 인자·의존성과 응답 변환을 수정해야 함 |
| Judge LLM | `judge_model`. 현재 `gemini-` ID와 `ChatGoogleGenerativeAI` 연결 | 다른 공급자는 `evaluation.py`의 모델 검증·클라이언트·키를 수정하고 `{score, reason}` 응답 계약을 확인해야 함 |
| RAGAS 평가 LLM | `ragas_model`. 현재 `gemini-` ID와 Gemini 연결 | 다른 공급자는 `config.py` 검증과 `experiments.py`의 `make_llm()`·키·RAGAS 래퍼 호환성 확인 필요 |

임베딩이나 청킹을 바꾸면 **문서와 질문에 같은 새 임베딩을 적용하고 FAISS 색인을 다시 만들어야 합니다.** 현재 색인은 파이프라인 인스턴스 안에서 만들고 캐시합니다. 모델·검색 설정을 바꿀 때는 새 프로세스/파이프라인으로 시작해 기존 색인·검색 캐시·답변 캐시와 섞지 마세요. 평가도 새 `--out-dir`에서 진행해 이전 체크포인트와 구분합니다.

Python 생성자에는 `embeddings`, `reranker`, `chat_model` 주입 지점이 있습니다. 연결할 객체는 각각 임베딩 인터페이스, `rank()` 결과, `invoke()`와 메시지 `content` 계약을 만족해야 합니다. CLI가 임의 공급자의 객체를 자동으로 만들어 주지는 않습니다. 프롬프트의 `{context}`·`{query}`, 모델 입력 한도와 채점 기준도 함께 검토해야 합니다.

임베딩·재정렬 로더는 원본의 `trust_remote_code` 설정을 유지합니다. 실제 다운로드·실행 전에는 모델 revision과 제공 코드를 검토해야 합니다. 모델 교체는 이번 변경에 포함되지 않았으며 현재 기본값·프롬프트·성능 수치는 그대로입니다.

## 선정과 평가 이력

2026년 10월 20일 사용자가 FINAL-02를 최종 실행으로 선택했습니다. 기존 300문항 비교에는 FINAL-01과 FINAL-02의 답변 점수 차이가 통계적으로 유의하지 않다고 기록돼 있습니다. FINAL-02는 입력 문맥이 약 27% 짧고, 기록된 검색 시간 중앙값이 4.9초에서 약 1.7초로 작았습니다. 질문 분해 호출이 추가되지 않는 단순한 실행 구성을 선택했습니다.

두 구성의 성능이 같다고 입증한 결과는 아닙니다. 여러 절의 근거를 모으는 질문에서는 FINAL-01이 더 많은 근거를 확보한 기록도 있습니다. [최종 기술 리포트 PDF](technical-reports/00_FINAL02_최종기술리포트_20261020.pdf)에서 조건과 한계를 확인할 수 있습니다.

| 흐름 | 시도와 발견 | 최종 정리 |
|---|---|---|
| 초기 `07_verify` | KURE·Chroma·EXAONE, 질문 분기와 숫자 검증을 포함한 초기 실행 구조 | 이전 평가 조건의 기준으로 보존 |
| 기존 Version 1·2 | 사업 식별·700/100·BGE·FAISS·Kiwi BM25 등 팀원 구현을 비교 | FINAL-02와 동일한 구성으로 취급하지 않음 |
| 기존 Version 3·4 | HWP 보정·parent/child·OpenAI 또는 KoE5 검색 흐름을 접수 | 실제 확보한 코드와 평가한 성능의 범위를 구분 |
| 10문서·30문항 실험 | 임베딩·프롬프트·리랭커·청크 크기를 바꾸며 검색과 답변을 분리해 확인 | 작은 실험의 결과를 100문서 결과와 섞지 않음 |
| 100문서·300문항 검색 실험 | 더 큰 검색 범위에서 근거 누락과 문맥 길이를 확인 | 검색 전용 결과를 답변 정확도로 표현하지 않음 |
| FINAL-01 | parent/child·질문 분해, 흩어진 근거 수집에 강점 | 비교 근거로 보존 |
| FINAL-02 | 헤더·질문 분해 없이 1000/200·BGE 재순위·Haiku 생성 | 현재 기본 실행으로 채택 |

<details>
<summary>과거 문서와 고정 코드 보기</summary>

[시도와 평가 해석](docs/시도와선정.md) · [과거 문서 보관](docs/history/README.md) · [교체 전 고정 코드](https://github.com/mingilee97/rag-project-part3-2team-main/tree/0f77930191bcb5d5b12c13a8d52d08184154c2f6)

구버전 실행 코드는 현재 트리에서 제거했고 Git 이력은 보존합니다. 원본 문서·출처·고정 SHA·기존 권리표시는 과거 문서에서 계속 확인할 수 있습니다.

</details>

## 결과와 한계

아래는 제공된 FINAL-02 저장 결과를 재계산한 값입니다. 새로 모델을 실행한 결과가 아닙니다.

| 지표 | 결과 | 유효 문항 수 |
|---|---:|---:|
| Hit@5 | 0.9550 | 289 |
| MRR | 0.8618 | 289 |
| Gemini LLM-as-Judge | 0.9300 | 300 |
| Factual Correctness F1 | 0.5749 | 300 |
| Faithfulness | 0.9848 | 300 |
| 필요한 근거를 모두 전달 | 252/300 | 300 |
| 평균 문맥 길이 | 5,079.2167자 | 300 |
| 검색 시간 중앙값 | 1.704초 | 300 |

근거 문장이 청크에 연결되지 않은 11문항은 검색 순위 평균에서 제외합니다. 점수가 없는 문항을 0점으로 바꾸지 않았습니다. FINAL-01의 parent 순위와 FINAL-02의 일반 청크 순위를 그대로 비교하지 않습니다. 한 번의 기존 실행, LLM 채점, 파싱 캐시 차이 때문에 일반적인 우월성과 재현성을 단정할 수 없습니다.

이번 정리의 검증은 합성 테스트 12개, 원본 대비 답변·캐시 비교 6건, 함수·클래스 구조 23개 일치, 프롬프트 바이트 일치입니다. 실제 모델·GPU·API·전체 재평가는 하지 않았습니다. [검증 근거](docs/validation.json)

과거 PDF는 [날짜·판본별 목록](docs/기술리포트목록.md)에서 확인할 수 있습니다. 10월 14일 자료와 10월 16일 ‘최종 평가’라는 제목의 자료도 **FINAL-02 채택 이전 기록**입니다. 현재 최종본과 같은 평가 조건으로 합치지 않습니다.

## 출처와 공개 범위

FINAL-02 실행 원본은 이원영 님의 제공 묶음이며, 재현 가이드는 김현경 님 `final_pipeline`의 짧은 commit `7db81eb`을 사용했다고 적습니다. 전체 원격 SHA는 별도로 확인하지 못했습니다. [출처와 변경](docs/출처와변경.md) · [원본 파일 해시](docs/source-manifest.json) · [인수인계](docs/인수인계.md)

공개 파일은 코드·빈 설정 예시·집계값·작성 문서·확인된 링크입니다. 원문 RFP·파싱 본문·메타데이터 행·평가 질문·답변·문맥·벡터·가중치·개인 환경은 포함하지 않습니다. 원본에 없던 일반 오픈소스 라이선스는 붙이지 않았습니다.

이전 발표 폴더와 snapshot은 FINAL-02 ZIP에 없는 이전 저장소 자료로 확인해 현재 트리에서 제거했습니다. Git 이력과 사용자 PC의 별도 발표 원본은 보존합니다. 리포트는 PDF 폴더로 모으고 편집 원문은 사용자 PC 작업 폴더와 과거 Git 이력에 남겼습니다. 별도 저장소·VM·호스팅·접근 권한은 변경하지 않았습니다.
