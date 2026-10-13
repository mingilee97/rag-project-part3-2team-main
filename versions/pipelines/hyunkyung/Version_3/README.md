# 전체 공개 실행 코드 접수

Version 1·2는 보존했습니다. 이번 Version 3은 고정 공개 노트북의 실행 단계를 나눕니다. 원본 설정을 유지하며 품질 개선이나 채택을 뜻하지 않습니다.

공급자·입력 경로·문서·메타데이터는 호출자가 전달합니다. import만으로 키를 읽거나 모델을 내려받거나 API를 호출하지 않습니다. 각 variant/provenance.json에 원본 셀 번호, 함수 AST, 파일 해시와 변환 범위가 있습니다. 원본 전체 노트북·출력·실제 질의·평가 행은 포함하지 않습니다.

- RAGAS 점수 계산은 외부 평가 호출이므로 실행하지 않음; 원본 인용문 정규화·추출·대조 루프 보존
- business 원본 검수는 N=10과 질문 순서 일치를 요구; 정답 의미 판정과 구분

NotebookRuntime은 인스턴스마다 전역 상태를 분리합니다. parser → cleaning(있을 때) → chunking → embedding → retrieval → generation 순으로 명시 호출합니다. 김민협 흐름은 embedding → generation → retrieval 순서입니다. generation이 만든 prompt를 retrieval에서 재사용하기 때문입니다. 원본 클래스 생성자와 모델 초기화 코드는 별도 단계에 보존했으며 실제 공급자를 연결한 호출에는 비용·GPU 사용이 발생할 수 있습니다.
