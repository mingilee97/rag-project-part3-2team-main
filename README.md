# 팀 공유 RAG 코드

**Baseline은 기준 보존, Main은 팀 공동 개선, Version 1~4는 실제 원본 코드가 포함된 참고 후보입니다.** Baseline과 후보 4개를 합쳐 5개 구성을 정리했고, Main은 Baseline의 독립 작업 사본입니다. 기존 modular 저장소와 합치지 않았습니다. 답변 생성 기본은 Claude Haiku 4.5 API (`claude-haiku-4-5-20251001`)입니다.

| 폴더 | 역할 / 실제 차이 |
|---|---|
| [Baseline](Baseline/) | 사용자 주력 07_verify 기준 보존: olefile·PyMuPDF, 1000/200, KURE-v1·Chroma, dense Top5, reranker off |
| [Main](Main/) | 팀원 공동 수정 폴더. 초기 35파일을 Baseline과 바이트 동일한 독립 복사본으로 만들었습니다. |
| [Version 1](Version_1/README.md) | 실제 business 식별·700/100·BGE-m3-ko·FAISS·BM25 RRF·Alibaba 재순위 코드 |
| [Version 2](Version_2/README.md) | 실제 Kiwi BM25 비교·700/100·BGE-m3-ko·FAISS·RRF·Alibaba 재순위 코드 |
| [Version 3](Version_3/README.md) | 실제 HWP 로더 보정·Markdown PDF·800/150·parent8000·OpenAI 임베딩·RRF·BGE 재순위 코드 |
| [Version 4](Version_4/README.md) | 실제 HWP 로더 보정·PyPDFLoader·500/100·KoE5·FAISS·BM25 RRF 코드 |

원본 작성자·저장소·고정 SHA·기존 권리표시는 [SOURCE-NOTES](SOURCE-NOTES.md)와 각 Version/provenance.json에 보존합니다. 사용자 승인 후 실제 단계 파일을 포함했으며 별도 원본 다운로드나 수동 코드 복사가 필요하지 않습니다. Version 번호는 성능 순위가 아닙니다. 원래 생성 모델 초기화 파일은 역사적 설정으로 남기고 기본 실행에서는 Haiku만 연결합니다. 임베딩·검색·청킹은 임의로 통일하지 않았습니다.

**바로 보기:** [구조설계 PDF](RAG_모델버전_구조설계_요약.pdf) · [발표 슬라이드 PDF](presentations/RAG_중간발표_아키텍처9장.pdf) · [발표자노트 PDF](presentations/발표자노트_아키텍처추가본.pdf) · [발표 전체](presentations/README.md)

발표 자료는 기존 EXAONE 평가 시점 구성입니다. 배포 생성 기본은 Haiku 4.5이며 동일조건 품질 재평가 전입니다. Baseline/docs의 이전 권한 보류 문서는 당시 상태를 보존한 기록이며 최신 포함 범위는 SOURCE-NOTES를 따릅니다.

## 팀 공동 작업: Main

Main은 별도 실제 파일 35개로 복사했습니다. 심볼릭 링크·하드링크는 없으며 [초기 파일별 해시](baseline-main-snapshot.json)를 보존합니다. Main 코드·YAML 수정은 Baseline 파일을 바꾸지 않습니다. 각 폴더에서 별도 프로세스로 실행하세요. 기본 data 경로도 각 폴더 아래입니다. 같은 RFP_DATA_DIR 환경 변수를 명시하면 같은 외부 데이터를 참조하므로, 비교할 때 이를 직접 구분해야 합니다. 후보의 공통 연결 코드는 루트 version_runtime.py·version_inputs.py이고 Main/Baseline 코드와 분리했습니다.

```sh
cd Main
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m rfp_rag.ingest.chunk --exp 07_verify
python -m rfp_rag.index --exp 07_verify --embedder nlpai-lab/KURE-v1 --method fixed
python -m rfp_rag.ingest.enrich --exp 07_verify
python -m rfp_rag.pipeline --exp 07_verify --ask "사업 요구사항을 설명해 줘."
```

위 실제 실행 전에 자기 Anthropic 키를 환경 변수에 설정하고 본인 문서·모델을 준비합니다. `.env.example`은 빈 값이며 `.env`를 자동으로 읽지 않습니다. PowerShell의 안전한 입력 예시는 [Baseline 안내](Baseline/README.md)에 있습니다. 데이터는 `data/raw`에 두며 기존 Baseline/Main 청크 CLI는 100개 문서를 기준으로 합니다. CSV 열은 `파일명,공고 번호,발주 기관,사업명,사업 금액,입찰 참여 마감일,텍스트,공개 일자,입찰 참여 시작일,사업 요약`입니다.

## 참고 후보 선택·실행

저장소 루트에서 실행합니다.

```sh
python run.py --list
python -m pip install -r Version_1/requirements.txt
python Version_1/run.py --check
python Version_1/run.py --smoke
python Version_1/run.py --input-dir data/raw --metadata data/data_list.csv --ask "사업 요구사항을 설명해 줘."
```

Version 2는 같은 인자, Version 3~4는 metadata 없이 `--input-dir`와 `--ask`를 사용합니다. root run.py에도 `--version v1/v2/v3/v4 --check/--smoke/--ask`를 전달할 수 있습니다. Version 1~2에는 원래 사업 식별용 CSV 열 `공고 차수`도 필요하며 누락을 오류로 알립니다.

Version 1~2는 parser → cleaning → chunker → embedder → Haiku → retriever → generator, Version 3~4는 HWP parser fix → parser → chunker → embedder → Haiku → generator → retriever를 실제 실행합니다. 뒤 두 원본은 generation의 prompt를 retrieval에서 사용합니다. 원본 검수·역사적 모델 초기화 단계는 보존하지만 기본 질문 CLI에서 역사적 모델을 자동 시작하지 않습니다.

각자 ANTHROPIC_API_KEY를 설정합니다. Version 3은 원래 OpenAI 임베딩을 유지하므로 OPENAI_API_KEY도 필요할 수 있습니다. 버전의 `.env.example`은 모두 빈 값입니다. 실제 임베딩·요약·생성에는 API 비용 또는 모델 다운로드/GPU 자원이 필요합니다. 이번 작업에서는 API 호출·모델 다운로드·학습을 하지 않았습니다.

오프라인 검사: `python -B test_versions.py`, 각 Version의 `--smoke`, Main과 Baseline 각각의 `python -B test_core.py`. smoke는 원본 청킹·BM25·RRF·부모 확장·재순위·문맥 구성을 실행하며 로더·모델 공급자만 합성합니다. 실제 모델 품질·GPU 전체 실행·새 설치 환경의 완전한 호환성은 별도 확인이 필요합니다.
