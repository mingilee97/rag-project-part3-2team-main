# 포함한 후보 코드의 출처와 공유 승인

2026-10-14 사용자는 원본 코드 재배포 허용 여부 미확인 때문에 포함을 보류했다는 설명을 듣고 "괜찮으니까 진행해"라고 팀 자료의 공개 공유 진행을 승인했습니다. 이 요청 범위에서 네 실제 원본 단계 모듈을 포함했습니다. 별도 오픈소스 라이선스를 임의로 붙이지 않았습니다.

| 폴더 | 원본 작성자 계정 | 원본 저장소 | 고정 SHA |
|---|---|---|---|
| Version 1, 2 | HyeongyeongKim | HyeongyeongKim/codeit_second_project | 17614c5005f5e0d78b2d20f466600a86ab5c5379 |
| Version 3, 4 | seolwoom | seolwoom/rag-for-proposals | 10882e31f1945369b68e38843a8f64ea777d3ffb |

두 고정 트리의 LICENSE·COPYING·NOTICE 파일과 README에서 별도 라이선스 문구를 확인하지 못했습니다. 명시적인 제3자 재배포 금지 문구는 확인하지 못했습니다. 팀 자료 공유에 대한 사용자 승인을 기록하며, 이를 원본에 없던 일반 공개 라이선스로 표현하지 않습니다. 라이브러리·모델의 기존 라이선스는 각 원본을 따라야 합니다.

단계 코드는 기존 팀 공개 저장소의 [PR #1](https://github.com/mingilee97/rag-project-part3-2team-main/pull/1) 고정 접수 SHA `cf4171e577cd481054fdd0aceee79bf87d6f5518`에서 가져왔습니다. PR #1 전체를 병합하지 않고 네 variant의 코드 파일만 포함했습니다. 각 Version/provenance.json은 원본 노트북·셀 번호·함수 AST·원본/접수 해시와 변환 범위를 보존합니다. 추가 포함 단계 코드는 접수본과 LF 기준 바이트가 같습니다. 원본 전체 노트북·출력·실제 문서·질의/답변·개인 경로·키는 복사하지 않았습니다.

Version 3/components의 rag_chunking.py·rag_reranking.py·rag_context.py는 원본 고정 코드입니다. 공통 청킹·재순위·문맥 구성 알고리즘을 실제 호출하며 포장 함수로 대체하지 않았습니다. 원본 검수 함수와 역사적 모델 초기화 단계도 보존합니다. 새 기본 실행 입구는 원래 생성 모델 초기화 대신 Haiku 연결을 명시 호출합니다. 원래 모델/검색/임베딩/청킹 설정은 version.json의 historical_settings에 남깁니다.

Baseline과 그 내부 문서는 직전 공개본을 보존했습니다. 내부의 과거 권한 보류 기록은 이 승인 이전 상태입니다. 최신 포함 범위와 실행 방법은 루트 README와 이 문서를 기준으로 확인합니다. Main은 Baseline 35파일의 독립 복사본으로 시작합니다. Main의 수정은 Baseline 파일을 바꾸지 않습니다.
