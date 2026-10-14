# 팀 공유 RAG 코드

사용자 기준 코드는 **Baseline**, 팀원 후보는 **Version 1~4**로 선택합니다. 총 5개 구성을 정리했습니다. 기본 생성기는 **Claude Haiku 4.5 API** (`claude-haiku-4-5-20251001`)입니다. 검색·청킹·임베딩은 원본을 유지하며 기존 modular 저장소와 합치지 않았습니다.

| 코드 폴더 | 차이 | 사용 상태 |
|---|---|---|
| [Baseline](Baseline/README.md) | 사용자 주력 07_verify: custom HWP·PyMuPDF, 1000/200, KURE-v1·Chroma, dense Top5, reranker off | 바로 실행 가능한 공유 코드; 각자 키·모델·데이터 준비 |
| [Version 1](Version_1/README.md) | business 식별, 700/100, BGE-m3-ko·FAISS, BM25 RRF·Alibaba 재순위 | 고정 원본 연결 후보; 재배포 권한 확인 필요 |
| [Version 2](Version_2/README.md) | Kiwi 토큰화, 700/100, BGE-m3-ko·FAISS, BM25 RRF·Alibaba 재순위 | 같은 상태 |
| [Version 3](Version_3/README.md) | parent-child 800/150·parent8000, OpenAI 임베딩, RRF·BGE 재순위·Top4 parent | 같은 상태; 원본 OpenAI 임베딩 조건 유지 |
| [Version 4](Version_4/README.md) | 500/100, KoE5·FAISS, dense Top4 또는 BM25 RRF Top5 | 같은 상태 |

Version 번호는 성능 순위가 아닙니다. 동일조건 성능 비교는 보류이며, 네 팀원 원본의 라이선스 파일이 확인되지 않아 코드 복사본을 이 변경에 새로 넣지 않았습니다. [고정 SHA·필수 출처·권한](Baseline/docs/팀-버전-출처.md)에 기록했습니다. 실제 코드 공유 가능 범위와 로컬 연결 조건을 구분했습니다.

**바로 보기:** [구조설계 요약 PDF](RAG_모델버전_구조설계_요약.pdf) · [발표 슬라이드 PDF](presentations/RAG_중간발표_아키텍처9장.pdf) · [발표자노트 PDF](presentations/발표자노트_아키텍처추가본.pdf) · [발표 원본 전체](presentations/README.md)

발표 자료는 기존 평가 시점 구성입니다. 배포 실행 기본은 Haiku 4.5이며 동일조건 품질 재평가 전입니다. EXAONE 과거 평가를 Haiku의 검증 성과로 표시하지 않았습니다.

## 선택·실행

```sh
python -B run.py --list
python -B run.py --version baseline
python -B run.py --version v1
```

실제 실행은 [Baseline 설치·키 설정·실행 안내](Baseline/README.md)를 따릅니다. `.env.example`에는 빈 `ANTHROPIC_API_KEY=`만 제공합니다. 팀원은 자기 키를 로컬 환경 변수에 입력합니다. `.env`는 Git에서 제외하며 자동으로 읽지 않습니다. 요약·질문·질문 분류·대화 재작성·비교 호출에는 Anthropic API 비용이 발생합니다.

원문·추출 본문·질의/답변·모델·벡터·키·개인 대시보드와 비공개 운영자료는 포함하지 않습니다. [기존 평가 요약](Baseline/docs/팀-버전-평가요약.md) · [검증과 인계](Baseline/docs/팀-버전-인계-20261014.md)
