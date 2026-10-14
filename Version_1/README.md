# Version 1

설정·출처·고정 SHA는 [version.json](version.json)에 있습니다. 공통 실행 연결은 `Baseline/team_versions/runtime.py`를 사용합니다. 사람 이름을 폴더명이나 표시 이름에 붙이지 않았습니다. 필수 attribution은 [출처 문서](../Baseline/docs/팀-버전-출처.md)에 보존합니다.

이 폴더는 고정 원본을 연결하는 후보 시작점입니다. 재배포 권한 미확인으로 원본 코드 복사본은 포함하지 않았습니다. 허용 범위를 확인한 로컬 모듈 사본을 연결할 때 파일 목록·해시를 검증합니다. 자동 다운로드나 모델 실행은 없습니다.

모듈 연결:
- parser: `hyunkyung/Version_3/business/parser.py`
- chunker: `hyunkyung/Version_3/business/chunking.py`
- embedder: `hyunkyung/Version_3/business/embedding.py`
- retriever: `hyunkyung/Version_3/business/retrieval.py`
- generator: `hyunkyung/Version_3/business/generation.py`

```sh
python -B run.py
```

이 명령은 설정만 표시합니다. 실제 실행은 [공통 연결 안내](../Baseline/docs/팀-버전-선택.md)를 따릅니다. 답변 공급자만 `session.connect_haiku()`로 선택합니다. 원본 파서·청킹·임베딩·검색과 원래 인자·반환값은 유지합니다. 각자 Anthropic 키를 로컬로 입력해야 하며 API 비용이 발생합니다. 원본 전체 품질과 Haiku 변환 후 품질은 미평가입니다.
