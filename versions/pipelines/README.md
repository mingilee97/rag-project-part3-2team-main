# 파이프라인 버전 선택

최초 공개 Baseline과 접수한 팀원 부품을 고정합니다. Version 1·Version 2는 읽기 쉬운 접수 순서이며, 성능 순위나 자동 채택 순서가 아닙니다.

- [Baseline](Baseline/README.md): 최초 공개 실행 코드와 설정의 바이트를 보존했습니다.
- [김현경 Version 1](hyunkyung/Version_1/README.md): 5e79101 정제·어댑터.
- [김현경 Version 2](hyunkyung/Version_2/README.md): 17614c5 사업명 식별 함수와 기존 메인 연결 어댑터.
- [김민협 Version 1](minhyup/Version_1/README.md): 10882e3 청킹·재순위·문맥 원본.
- [김민협 Version 2](minhyup/Version_2/README.md): 기존 통제 비교의 공통 크기 제한 어댑터.
- [권유진](eugene/Version_1/README.md), [이원영](wonyoung/Version_1/README.md): 소스 미확보; 성능 판정 없음.

`python versions/pipelines/select.py --list`로 버전을 보고 `--version hyunkyung/Version_2 --check`로 파일 해시·문법을 검사합니다. 이 선택기는 모델 호출·색인 생성·운영 설정 변경을 하지 않습니다. 실제 실행은 각 README의 호출 규약과 Baseline 의존성을 사용합니다.

기존 부분 모듈화의 누락 원인은 공개 허용 범위가 정제 부품과 세 모듈에 한정됐고, 후속 접수가 비공개 로컬 통제 비교에만 남았기 때문입니다. 노트북의 모델 초기화·데이터 셀과 모든 단계가 자동 변환된 상태는 아닙니다. 확보된 공개 원본 노트북의 나머지 단계는 고정 원본 링크로 대조할 수 있습니다. 원문·출력 셀·키·비공개 이력은 복사하지 않았습니다.

김현경 원본: https://github.com/HyeongyeongKim/codeit_second_project/tree/17614c5005f5e0d78b2d20f466600a86ab5c5379

김민협 원본: https://github.com/seolwoom/rag-for-proposals/tree/10882e31f1945369b68e38843a8f64ea777d3ffb
