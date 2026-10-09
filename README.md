# RAG Project · 메인 코드

공공 입찰 제안요청서(RFP)에서 근거를 찾아 한국어로 답하는 실행 코드다. HWP·PDF 전처리, 청크 생성, 색인, 검색, 대화 기억, 질문 분류, 답변 생성과 숫자·날짜 검증을 포함한다.

메인 실행 코드와 설정에 더해, 2026-10-09 사용자 요청으로 공개 가능한 UI 부품·후보 코드·비교 집계·재현 도구를 별도 검토 브랜치에 정리했다. 원본 문서, 추출한 글, 모델 가중치, 실제 질문과 답변, 개인 일정, DB와 비밀 값은 포함하지 않는다. 기존 작업 저장소의 Git 이력도 가져오지 않았다. 기존 메인 인계는 [인수인계](docs/인수인계.md), 새 비교의 상태와 복원 범위는 [버전 검토 인계](docs/버전-검토-인계-20261009.md)에 있다.

## UI 버전과 모델 선정

UI 버전은 [UI 목록](dashboard/versions/catalog.json), 모델·알고리즘 후보는 [모델 목록](versions/models.json)에서 따로 관리한다. UI 선택이 모델 채택을 뜻하지 않는다. 현재 새 모델 선정은 [pending](versions/selection.json)이며 메인 `07_verify`를 유지한다. 실측 범위와 한계는 [비교 근거](docs/버전-비교-근거.md), 같은 조건으로 다시 실행하는 방법은 [재현 절차](evaluation/README.md)에 있다.

공개한 대시보드 파일은 원본과 바이트가 같은 순수 날짜·연결선 함수 및 스타일이다. [합성 UI 예시](dashboard/example/index.html)는 실제 팀 데이터나 운영 API 없이 이 부품을 보여 준다. 전체 운영 앱을 복원하거나 배포하지 않는다.

## 설치

Python 3.11 환경에서 저장소 루트로 이동해 실행한다.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install torch
python -m pip install -r requirements.txt
```

GPU를 사용할 때는 장비와 맞는 PyTorch 빌드를 설치해야 한다. 기본 질문 임베딩은 CPU를 사용한다. 실행에 필요한 모델은 별도로 준비한다. Ollama를 실행한 뒤 아래 모델을 받는다.

```sh
ollama pull exaone3.5:7.8b
```

## 입력 데이터

기본 데이터 폴더는 저장소 루트의 `data/`다. 다른 위치를 사용하려면 환경 변수 `RFP_DATA_DIR`를 설정한다. 데이터 폴더는 Git에서 제외한다.

`data/raw/`에 HWP·PDF와 UTF-8 CSV인 `data_list.csv`를 둔다. CSV 열 이름은 다음과 같다.

```text
파일명,공고 번호,발주 기관,사업명,사업 금액,입찰 참여 마감일,텍스트,공개 일자,입찰 참여 시작일,사업 요약
```

`파일명`은 원본 파일 이름이다. `사업 금액`은 숫자이며, `텍스트`는 파일이 잠겼거나 읽히지 않을 때 사용할 대체 본문이다. 원래 파이프라인은 문서 100건을 기준으로 만들었으며 청크 생성 CLI도 100건을 확인한다.

## 실행

```sh
python -m rfp_rag.ingest.chunk --exp 07_verify
python -m rfp_rag.index --exp 07_verify --embedder nlpai-lab/KURE-v1 --method fixed
python -m rfp_rag.ingest.enrich --exp 07_verify
python -m rfp_rag.pipeline --exp 07_verify --ask "사업의 주요 요구사항을 정리해 줘." "그 사업의 예산은 얼마야?"
```

위 순서로 글과 청크를 만들고, 색인을 만든 뒤, 문서 요약을 준비하고 질문한다. 색인 단계에서 임베딩 모델을 내려받을 수 있다. 요약과 질문 단계는 모델을 호출한다. 질문을 여러 개 주면 한 대화로 처리한다.

기본 모델은 `exaone3.5:7.8b`, 임베딩은 `nlpai-lab/KURE-v1`, 검색은 dense 상위 5개, 청크는 1,000자와 겹침 200자다. `07_verify` 설정은 질문 분류·근거 검증·문서 요약 사용을 켠다. 설정은 `configs/base.yaml`에서 바꾼다. OpenAI를 선택할 때는 `OPENAI_API_KEY` 환경 변수로 키를 전달하며, 해당 호출에는 API 사용료가 발생할 수 있다.

## 점검

```sh
python test_core.py
```

합성 입력으로 PDF 전처리·청크 생성·검색 연결·답변 근거 검증·대화 상태를 확인한다. 외부 모델이나 API를 호출하지 않는다. 실제 데이터와 모델의 성능 평가를 대신하지 않는다.
