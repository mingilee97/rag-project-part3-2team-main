# Baseline 코드

사용자 원래 주력 `07_verify`를 기준으로 합니다. 최초 실험의 `00_baseline`을 의미하지 않습니다. 원래 공유 추출 코드의 고정 SHA는 `bfca8f0508b65dfa97d9aa01da9a93ac188e68bd`이며, 이번 배포에서 생성 공급자만 Haiku 4.5로 변경했습니다. KURE-v1·Chroma·dense Top5·청크 1000/200·reranker off는 유지합니다.

`rfp_rag/`에 실제 파서·청킹·임베딩·검색·생성 코드가 있습니다. `team_versions/`는 모든 후보가 공유하는 선택 및 연결 인터페이스입니다. `version.json`은 과거 설정과 배포 생성 설정을 구분합니다.

이 폴더에서 설치하고 실행합니다.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
```

키는 개인 실행 환경에만 넣습니다. `.env.example`에는 `ANTHROPIC_API_KEY=`가 비어 있습니다. `.env`를 자동으로 읽지 않으므로 환경 변수로 설정하세요. PowerShell에서는 입력값이 화면에 보이지 않게 다음처럼 설정할 수 있습니다.

```powershell
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new('', (Read-Host '개인 Anthropic API 키' -AsSecureString)).Password
```

`data/raw/`에 본인이 사용할 HWP·PDF와 `data_list.csv`를 둡니다. CSV 필수 열은 기존 [원본 인계](docs/인수인계.md)를 따릅니다. 데이터와 색인을 함께 커밋하지 않습니다. 원래 CLI는 100개 문서를 기준으로 했습니다.

```sh
python -m rfp_rag.ingest.chunk --exp 07_verify
python -m rfp_rag.index --exp 07_verify --embedder nlpai-lab/KURE-v1 --method fixed
python -m rfp_rag.ingest.enrich --exp 07_verify
python -m rfp_rag.pipeline --exp 07_verify --ask "사업 요구사항을 설명해 줘."
```

색인 구축에는 준비된 KURE 모델이 필요하며 없으면 라이브러리가 다운로드할 수 있습니다. 요약·질문·분류·재작성·비교는 Anthropic API를 사용하며 비용이 발생합니다. 이번 작업에서는 다운로드와 API 호출을 하지 않았습니다.

배포 기본은 `configs/base.yaml`의 `anthropic / claude-haiku-4-5-20251001`입니다. 과거 EXAONE 설정은 `--exp 07_verify_exaone`으로 선택합니다. 발표·역사적 평가와 Haiku 배포를 혼동하지 않습니다. Haiku 동일조건 품질 재평가는 아직 하지 않았습니다.

공통 인터페이스: `VersionSession('baseline').run(stage, *원래_인자)`입니다. parser=`load_docs(data_dir)`, chunker=`chunk_fixed(document,size,overlap)`, embedder=`get_embeddings(cfg)`, retriever=`retrieve(cfg,question)`, generator=`pipeline.ask(question,state,cfg)`를 연결합니다.
