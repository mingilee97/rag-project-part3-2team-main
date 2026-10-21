## 📑 입찰메이트 RFP RAG

### 📌 제출 자료 바로가기

| 자료 | 바로가기 | 확인할 내용 |
|---|---|---|
| **최종 프로젝트 보고서** | [**최종 보고서 PDF · 공개용**](technical-reports/00_프로젝트_최종보고서_20261021_공개용.pdf) | 2026-10-21 최신 다운로드판 · 검색 시간 p95·최대값 포함 · 23쪽 |
| 모듈화·검증 기술 자료 | [FINAL-02 기술 리포트](technical-reports/00_FINAL02_최종기술리포트_20261020.pdf) | 2026-10-20 · 코드 모듈화·재현·오프라인 검증 근거 · 7쪽 · 보조 자료 |
| 소스와 실행 안내 | [실행 소스](rfp_rag/) · [설치와 실행](#설치와-실행) | 비공개 입력 자료 준비와 실행 명령 |
| 전체 보고서·기술 리포트 | [PDF 폴더](technical-reports/) · [날짜·판본·출처 목록](docs/기술리포트목록.md) | **총 14개** · 최종본과 과거 자료·공개용 사본 구분 |
| 실험 기록표 | [Google Sheets](https://docs.google.com/spreadsheets/d/16x-29flLEjQfMDl5mSvRzgBmKU4O-IBlRtxYxJqHb7E/edit?usp=sharing) | 실험 조건·관찰·판단 기록, 접근 권한은 별도 |
| 개인별 협업일지 | **아래 팀원별 전체 표** | 작성자별 일지 원본과 보조 기록으로 바로 이동 |

### 팀원별 협업일지

| 팀원 | 협업일지 원본 | 확인 범위 |
|---|---|---|
| 이민기 | [개인 협업일지 시트](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=2053649411) | 기존 개인 탭, 별도 담당자가 최근 기록을 정리한 원본 |
| 김현경 | [데일리 협업일지](https://app.notion.com/p/3eb67f39201180a4b1dbec087503807a?v=3eb67f39201180d583d7000c73a17268) · [실험 문서](https://app.notion.com/p/3ec67f3920118072b687d3aaed1e4428) | 일지 본문에서 작성자 확인, 현재 게스트 열람 확인 |
| 김민협 | [개인 협업일지 문서](https://docs.google.com/document/d/1Jsx4ESbBhTFP4R7UN_pCgxd9Jha1HFBjU6lJjErrhYc/edit?usp=sharing) · [이전 시트(보조)](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=924303621) | 김민협의 개인 협업일지로 사용자 확인 · 본문 열람 확인 |
| 이원영 | [프로젝트2 (2팀) 이원영 개인일지 (공유용)](https://docs.google.com/document/d/1RKp7OUprcmlTjm5N2BiX6yXr5PQxYqe09bHqKcNVwSA/edit?usp=sharing) · [이전 시트(보조)](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=1041212623) | 제목·본문 열람 확인 · 새 문서 비로그인 보기 확인(2026-10-21) |
| 권유진 | [권유진 Daily 협업일지](https://app.notion.com/p/AI_13_-Daily-3eae732bc80e80988fd4d696d6726479?source=copy_link) · [이전 시트(보조)](https://docs.google.com/spreadsheets/d/1sWL-WgSjILLUkuB_yw3edxLnqOATh7gCUG410d-JvrA/edit#gid=1632189499) | 작성자·2팀 확인 · 2026-10-21 비로그인 목록 및 일지 1건 열람 확인, 전체 항목 미검증 |

---

<details>
<summary>팀원별 담당</summary>

아래 역할은 다운로드 README와 제공된 프로젝트 보고서의 팀 구성 기록을 요약했습니다.

| 팀원 | 담당 내용 |
|---|---|
| 이민기(팀장) | 프로젝트 관리, 초기 기준 파이프라인·평가, 팀원 구성 비교, 발표·최종 저장소 정리 |
| 김현경 | 공통 `final_pipeline`, HWP·표 처리, 하이브리드 검색·프롬프트·질의 분해 실험, FINAL-01 |
| 김민협 | 개발 환경·평가 도구 연결, HWP 파서 보정, BM25·parent-child 청킹 실험 |
| 권유진 | 공통 개발 평가셋과 Holdout 평가셋 구축, 최종 기능별 진단 평가 |
| 이원영 | 재순위화·청킹·검색 전용 비교, FINAL-02 실행·평가와 재현 묶음, 프로젝트 보고서 |

</details>

## 프로젝트 소개

공공 입찰 제안요청서(RFP) 100건에서 질문과 관련된 근거를 찾아 한국어로 답하는 **LLM 기반 RAG 질의응답 시스템**입니다. 가상 입찰 컨설팅 기업 ‘입찰메이트’의 사내 서비스를 목표로, 컨설턴트가 요구사항·예산·일정처럼 문서에 흩어진 정보를 확인하는 상황을 다뤘습니다.

Codeit AI Engineer Bootcamp 13기 중급 프로젝트 · 파트3 2팀으로 진행했으며 기간은 **2026.09.30~2026.10.22**입니다. HWP 96건·PDF 4건의 본문과 표를 읽고, 긴 문서를 나눈 뒤 검색한 근거를 생성 모델에 전달합니다. 표 구조와 출처를 보존하고, 근거가 부족할 때 답변을 유보하며, 검색과 답변을 나누어 평가하는 것이 목표입니다. 파싱의 완전한 무손실이나 모든 질문에서의 정답을 보장하지 않습니다.

현재 실행 코드는 **FINAL-02 하나**입니다. 문서 처리·청킹·임베딩·검색·재정렬·생성·평가를 모듈로 나눠 변경을 비교할 수 있게 했습니다. 모델 교체 지점은 있지만 임의의 LLM을 이름만 바꿔 쓸 수 있는 구현은 아닙니다.

## 목차

[아키텍처](#아키텍처) · [개발 환경](#개발-환경) · [설치와 실행](#설치와-실행) · [모델 교체와 확장](#모델-교체와-확장) · [데이터와 평가](#데이터와-평가) · [실험과 최종 선정](#실험과-최종-선정) · [결과와 한계](#결과와-한계) · [보고서와 기록](#보고서와-기록) · [출처와 공개 범위](#출처와-공개-범위)

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

## 개발 환경

| 구분 | 구성 |
|---|---|
| 언어·프레임워크 | Python 3.11+, LangChain, sentence-transformers |
| 문서 처리 | HwpHwpxLoader, pymupdf4llm, 파싱 캐시 |
| 임베딩·색인 | Hugging Face 임베딩, FAISS |
| 키워드 검색 | rank-bm25, Kiwi(kiwipiepy) 형태소 분석 |
| 생성·평가 연결 | Anthropic 생성, Google Gemini Judge·RAGAS 0.3.9 |
| 실험 환경 기록 | GCP VM의 L4 GPU, Google Colab. 새 설치·GPU·API 호환성을 이번에 재검증한 것은 아님 |
| 협업 | GitHub, Google Sheets, Notion·Google Docs, Discord |

모델별 실제 기본값은 위 아키텍처 표와 [`RagSettings`](rfp_rag/config.py)에 있습니다.

## 설치와 실행

Python 3.11 이상을 기준으로 합니다. 아래 설치는 사용자가 실행할 절차입니다. 이번 문서 정리에서는 설치·모델 다운로드·유료 API를 실행하지 않았습니다. GPU 환경과 고정 패키지 조합의 새 설치 호환성은 별도 확인이 필요합니다.

```sh
git clone https://github.com/mingilee97/rag-project-part3-2team-main.git
cd rag-project-part3-2team-main
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

## 데이터와 평가

| 평가 묶음 | 범위 | 해석 범위 |
|---|---|---|
| 원본 문서 | 제안요청서 100건, HWP 96·PDF 4 | 원문·파싱 캐시의 버전이 달라지면 청크와 결과도 달라질 수 있음 |
| 개발 평가셋 `dev_benchmark_v1.1` | 100문서·300문항, `direct_fact`·`numeric_condition`·`multi_section` 각 100문항 | 구성 선택과 FINAL-01·02 비교에 사용. 정답 문장·근거 인용문은 공개하지 않음 |
| 작은 개발 실험 | 일부 문서·10문항 또는 10문서·30문항 등 | 큰 평가셋과 같은 모집단·조건으로 합치지 않음 |
| 검색 전용 RET 실험 | 100문서·300문항, 생성·Judge 호출 없이 검색 지표 측정 | 검색 순위·근거 포함량이며 답변 정확도와 구분 |
| 후속 Holdout 진단 | 제공 프로젝트 보고서에 따르면 42문항 중 정답 검증을 마친 30문항 사용 | 핵심 사실·복수 문서·답변 불가 각 10문항. 개발 평가셋의 300문항 결과와 별도 |

| 지표 | 무엇을 보는가 |
|---|---|
| Hit@5·MRR | 근거 인용문이 처음 나타난 청크의 순위. FINAL-02 저장 결과는 근거를 청크에 연결할 수 있었던 289문항 기준 |
| 근거 재현율·근거 전부 전달 | 필요한 근거가 최종 입력 문맥에 얼마나, 모두 포함됐는지 |
| LLM-as-Judge | 기준 답변과 생성 답변의 사실·필수 항목을 Gemini가 0~1로 평가 |
| Factual Correctness F1 | 기준 답변과 생성 답변의 사실 일치 정도 |
| Faithfulness | 생성 답변이 전달된 근거에 충실한 정도. 답변의 완전한 정확성과 같은 지표는 아님 |

## 실험과 최종 선정

다운로드 README와 제공 프로젝트 보고서의 기록을 기준으로 주요 흐름을 정리했습니다. 전체 실험·비교·진단 기록은 [실험 기록표](https://docs.google.com/spreadsheets/d/16x-29flLEjQfMDl5mSvRzgBmKU4O-IBlRtxYxJqHb7E/edit?usp=sharing)에 연결합니다. 기록 수를 모두 독립적인 모델 품질 실험 횟수로 계산하지 않으며, 이번 README 보완에서 새 실험을 실행하지 않았습니다.

| 시점·기록 | 바꾼 부분 | 당시 평가 범위 | 기록된 관찰·판단 |
|---|---|---|---|
| 10/08 · EXP-009 | 사업명으로 검색 범위 한정 | 99문서·10문항 | FC 0.354→0.838, Faithfulness 0.600→1.000. 사업별 검색 채택 |
| 10/08 · EXP-014 | BGE-m3-ko 임베딩 | 99문서·10문항 | FC 0.895 기록. 이 작은 실험의 결과를 모든 조건의 우월성으로 일반화하지 않음 |
| 10/11 · EXP-015 | Kiwi 형태소 BM25 | 3문서·30문항 | BM25 MRR@20 0.3906→0.6755. 키워드 검색 보완 |
| 10/15 · EXP-025 | 답변 프롬프트 | 10문서·30문항 | FC 0.4807→0.5417 기록 |
| 10/16 · RET-bge-700 | gte→BGE 재순위화 | 100문서·300문항, 검색만 | Hit@5 0.8788→0.9428, 타 사업 혼입 141→62문항 |
| 10/16 · RET-bge-1000 | 700/100→1000/200 | 100문서·300문항, 검색만 | 근거 전부 전달 241→259/297. 근거 정렬 분모 297은 최종 생성 평가의 300과 다름 |
| 10/16 · RET-bge-1000-header | 사업명 청크 헤더 | 100문서·300문항, 검색만 | 혼입 50→9이나 MRR 0.863→0.838. 최종 기본값에서 미채택 |
| 10/19 · FINAL-01 | parent-child·질의 분해 | 100문서·300문항, 답변 포함 | Judge 0.920, 평균 문맥 6,982자, 검색 중앙값 4.94초·p95 7.18초 |
| 10/19 · FINAL-02 | 일반 청크 1000/200, 한 번 검색 | 100문서·300문항, 답변 포함 | Judge 0.930, 평균 문맥 약 5,079자, 검색 중앙값 1.70초·p95 2.09초. **현재 최종 실행** |

실험마다 모델·문서 수·질문 수·정답 판정 단위가 달랐고 일부에서는 프롬프트와 청킹이 함께 바뀌었습니다. 모든 실험이 한 변수만 바뀐 통제 비교였다고 주장하지 않습니다. 검색 성능, 답변 점수, 입력 문맥 길이와 API 호출 수를 나눠 해석합니다.

### FINAL-02를 채택한 이유

팀은 2026-10-20 FINAL-02를 최종 실행으로 선택했습니다. 제공된 300문항 비교 기록에서 답변 지표 차이는 통계적으로 유의하지 않았으며, 이는 두 구성이 동등하다는 증명이 아닙니다. FINAL-02는 기록된 문맥이 약 27% 짧고 검색 중앙값이 4.94초보다 작은 1.70초였으며 질의 분해 호출이 없어 구성이 단순했습니다. 새로운 비용 절감률이나 속도 개선을 이번에 측정한 것은 아닙니다.

여러 절을 종합하는 `multi_section` 질문의 근거 전부 전달 비율은 FINAL-01이 0.77, FINAL-02가 0.69였습니다. 두 실행의 파싱 캐시는 다섯 문서에서 달랐고, 청킹과 질의 분해도 함께 바뀌어 원인을 각각 분리하지 못했습니다. parent 순위와 일반 청크 순위를 같은 Hit@5·MRR 경쟁표로 놓지 않습니다.

<details>
<summary>초기 기준 구성과 이전 코드 접수 이력</summary>

초기 `07_verify`의 KURE·Chroma·EXAONE, 팀원 Version 1~4의 파서·임베딩·청킹·검색 구성은 [시도와 선정 기록](docs/시도와선정.md)과 [과거 문서](docs/history/README.md)에 보존했습니다. 당시 구성을 현재 FINAL-02와 같은 버전으로 취급하지 않습니다. [교체 전 고정 코드](https://github.com/mingilee97/rag-project-part3-2team-main/tree/0f77930191bcb5d5b12c13a8d52d08184154c2f6)

</details>

## 결과와 한계

### 개발 평가셋 300문항 · FINAL-02

아래는 기존 FINAL-02 저장 결과의 집계와 최신 보고서 9.2절의 검색 시간 기록입니다. 새로 모델을 실행한 결과가 아닙니다.

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
| 검색 시간 p95 · 최신 보고서 | 2.09초 | 300 |
| 검색 시간 최대 · 최신 보고서 | 2.63초 | 300 |

최신 보고서의 검색 시간은 사업 식별부터 최종 문맥 선택까지이며, 답변 생성과 최초 색인 구축은 포함하지 않습니다. 보고서의 중앙값 1.70초는 위 1.704초를 소수 둘째 자리로 표시한 값입니다. FINAL-01의 p95는 7.18초이며, 질의 분해 호출을 포함하고 실행 장비도 Colab과 GCP VM으로 달라 모델·코드만의 속도 차이로 해석하지 않습니다. 이번 작업에서는 시간 지표를 다시 측정하지 않았습니다.

근거 문장이 청크에 연결되지 않은 11문항은 검색 순위 평균에서 제외합니다. 점수가 없는 문항을 0점으로 바꾸지 않았습니다. FINAL-01의 parent 순위와 FINAL-02의 일반 청크 순위를 그대로 비교하지 않습니다. 한 번의 기존 실행, LLM 채점, 파싱 캐시 차이 때문에 일반적인 우월성과 재현성을 단정할 수 없습니다.

FINAL-02 모듈화 당시 검증은 합성 테스트 12개, 원본 대비 답변·캐시 비교 6건, 함수·클래스 구조 23개 일치, 프롬프트 바이트 일치입니다. 실제 모델·GPU·API·전체 재평가는 하지 않았습니다. 문서 정리와 합성 테스트를 실제 모델 성능 검증으로 해석하지 않습니다. [검증 근거](docs/validation.json)

과거 PDF는 [날짜·판본별 목록](docs/기술리포트목록.md)에서 확인할 수 있습니다. 10월 14일 자료와 10월 16일 ‘최종 평가’라는 제목의 자료도 **FINAL-02 채택 이전 기록**입니다. 현재 최종본과 같은 평가 조건으로 합치지 않습니다.

### 후속 Holdout 진단 · 제공 프로젝트 보고서 기록

개발 평가셋으로 구성을 고른 뒤 검증한 30문항의 진단값입니다. 아래는 제공 프로젝트 보고서의 집계이며, 이번에 원문 문항을 공개하거나 재평가한 값이 아닙니다. 300문항 표의 Judge·F1과 동일한 지표로 합산하지 않습니다.

| 유형 | 문항 수 | Correctness | 검색 Hit@5 |
|---|---:|---:|---:|
| 핵심 사실 추출 | 10 | 0.890 | 80% |
| 복수 문서 종합 | 10 | 0.000 | 10% |
| 답변 불가 판단 | 10 | 1.000 | 해당 없음 |

답변 불가 문항은 정답 근거가 없어 검색 Hit@5를 계산하지 않았고 적절한 거절은 10/10으로 기록됐습니다. 이 결과는 복수 사업 질문의 라우팅·문서별 문맥 배분이 우선 개선 과제임을 보여 주는 제한된 진단으로 해석합니다.

### 남은 한계

- 복수 사업·여러 절의 근거 수집: 문서별 검색과 문맥 배분, 질문 유형별 주변 청크·parent 확장 검토가 필요합니다.
- 사업 식별: 제공 보고서에서는 300문항 중 48문항이 식별됐습니다. 나머지는 전체 문서 검색으로 돌아갔으며 별칭·약칭 보완이 필요합니다.
- 후속 질문: 현재 기본 실행은 단일 질문 단위입니다. 대화 맥락을 반영한 재작성은 현재 구현으로 주장하지 않습니다.
- 파싱·평가 신뢰도: 환경별 캐시 차이, 각 구성의 한 번 실행과 단일 LLM 채점의 한계가 있습니다. GPU·API 호환성과 새 모델 교체 후의 품질은 별도 검증 대상입니다.

## 보고서와 기록

- [PDF 14개 모음](technical-reports/) · [날짜·판본·출처 목록](docs/기술리포트목록.md)
- [실험 기록표](https://docs.google.com/spreadsheets/d/16x-29flLEjQfMDl5mSvRzgBmKU4O-IBlRtxYxJqHb7E/edit?usp=sharing) · [실제 설정](docs/final02-settings.json) · [FINAL-02 집계 CSV](docs/final02-summary.csv)

제출용 대표 문서는 마지막으로 다운로드한 보고서(검색 시간 분포 추가)를 기준으로 갱신한 상단의 **최종 프로젝트 보고서 공개용 PDF**입니다. 평가 데이터 보호를 위해 7쪽 질문·답변 예시와 6쪽에 반복된 같은 답변 수치만 제거했으며, 나머지 기술 내용·집계값·날짜·작성자 표기는 보존했습니다. 기존 7쪽 기술 리포트는 새 보고서가 참고하는 모듈화·검증 근거이므로 보조 자료로 구분합니다. [공개용 사본 검증 기록](docs/project-report-publication.json)

## 출처와 공개 범위

FINAL-02 실행 원본은 이원영 님의 제공 묶음이며, 재현 가이드는 김현경 님 `final_pipeline`의 짧은 commit `7db81eb`을 사용했다고 적습니다. 전체 원격 SHA는 별도로 확인하지 못했습니다. [출처와 변경](docs/출처와변경.md) · [원본 파일 해시](docs/source-manifest.json) · [인수인계](docs/인수인계.md)

공개 파일은 코드·빈 설정 예시·집계값·작성 문서·확인된 링크입니다. 원문 RFP·파싱 본문·메타데이터 행·평가 질문·답변·문맥·벡터·가중치·개인 환경은 포함하지 않습니다. 원본에 없던 일반 오픈소스 라이선스는 붙이지 않았습니다.

이전 발표 폴더와 snapshot은 FINAL-02 ZIP에 없는 이전 저장소 자료로 확인해 현재 트리에서 제거했습니다. Git 이력과 사용자 PC의 별도 발표 원본은 보존합니다. 리포트는 PDF 폴더로 모으고 편집 원문은 사용자 PC 작업 폴더와 과거 Git 이력에 남겼습니다. 별도 저장소·VM·호스팅·접근 권한은 변경하지 않았습니다.
