# 오프라인 비교 재현

이 폴더에는 공개 가능한 집계와 CPU 전용 비교 코드를 보관한다. 실제 RFP 원문·질문·gold ID·벡터·답변은 GitHub에 포함하지 않는다. 따라서 저장소 clone만으로 과거 점수가 복원되지는 않는다. 권한이 있는 동일 로컬 자산과 집계에 기록한 해시가 필요하다.

## 가벼운 검사

```sh
python evaluation/test_cpu_service.py
python evaluation/test_cleaning_adapter.py
python evaluation/verify_public_bundle.py
node dashboard/test-example.mjs
python evaluation/cpu_service.py
python evaluation/full_cpu_compare.py --help
```

첫 네 검사는 모델을 호출하지 않는다. `cpu_service.py`의 기본 실행도 dry-run이다. `full_cpu_compare.py --help`는 모델 패키지를 불러오기 전에 인자 설명만 출력한다. 프로젝트의 기존 `test_core.py`도 실행해야 한다.

정제 후보의 [adapter.py](../candidates/hyunkyung/5e79101/adapter.py)는 메인의 문서 dict에서 메타데이터와 키를 보존하며 새 `text`만 만든다. `(새 문서, 진단)`을 반환하므로 새 문서는 메인 chunk 함수에 그대로 전달하고 진단은 별도 평가 기록으로 저장한다. 원본 함수는 `(cleaned, removed_lines)`를 반환하므로 본문 문자열만 입력 스키마에 옮겼다. 명시한 보호 구간이 원문에는 있고 정제 뒤 사라지면 그 문서는 원문을 반환한다. 보호 구간을 주지 않은 의미·표 구조까지 검증한 것은 아니다. 이 안전한 복귀는 통합 과정에서 추가한 동작이며 후보 원본의 성능 주장과 구분한다. 운영 ingestion에는 연결하지 않았다.

합성 UI를 볼 때는 저장소 루트에서 `python -m http.server 8091 --bind 127.0.0.1 --directory dashboard/example`를 실행하고 `http://127.0.0.1:8091`을 연다. 예시에는 실제 팀 데이터와 채택 동작이 없다. 브라우저 함수는 원본 TS의 순수 함수에서 생성했으며 React hook을 제외했다. 재생성은 설치된 TypeScript 경로를 인자로 `node dashboard/build-example.mjs <typescript.js>`를 실행한다. 이 명령은 패키지를 자동 설치하지 않는다.

## 100문서 검색 비교

실행 입력은 다음과 같다. `docs.jsonl`에는 메인 문서 스키마인 `doc_id,source_file,agency,title,text` 등이 필요하다. 질문은 `id,question,project_id,answer_doc_ids`와 인용/필수 사실을 담는다. 기존 14문서 벡터를 재사용하기 때문에 그때의 결과·alignment manifest·query vectors도 요구한다. 텍스트와 순서 및 파일 해시가 하나라도 다르면 실행을 중단한다.

```sh
python evaluation/full_cpu_compare.py \
  --docs /authorized/docs.jsonl \
  --questions /authorized/confirmed-questions.jsonl \
  --reference /authorized/dense-corrected-v2-results.json \
  --prior-results /authorized/dense-cpu-followup-results.json \
  --prior-alignment /authorized/chunk-order-manifest.json \
  --prior-vectors /authorized/dense-cpu-followup \
  --query-vectors /authorized/query-vectors.npy \
  --kure-snapshot /authorized/KURE-snapshot \
  --bge-snapshot /authorized/BGE-snapshot \
  --output /authorized/new-review-run
```

Windows PowerShell에서는 줄 연결 기호 대신 한 줄로 실행하거나 인자를 배열로 전달한다. 경로는 자신의 승인된 로컬 자산으로 바꾼다. `--guard-file`을 지정하면 기존 등록 평가의 가드 파일 해시도 실행 계획에 기록한다. 파일을 수정하거나 제거하지 않는다.

CPU4스레드 BF16·KURE normalize 뒤 float32로 저장한 벡터의 dot 전수 검색을 양쪽에 적용한다. 근사 최근접 검색(ANN)은 사용하지 않는다. BF16에서 정규화할 때 생긴 단위 길이 오차를 보존하므로 엄밀한 코사인으로 표시하지 않는다. 후보 기본 GPU/다운로드 loader를 실행하지 않는다. 메인과 후보 모두 prefix를 같은 검색 입력에 넣고 BGE에는 본문만 넣는다. 전역 부모 키로 문서 간 ID 충돌을 방지한다. BGE는 동일 pool20을 한 번씩 점수화하고 child top5 또는 parent4에 재사용한다. 총 근거 예산은 같은 4,000 o200k, 부모당 2,000이다.

공개 재현 코드 v2는 KURE revision `8b418a58414668e75532ed045c22d9ca018ae2b2`, BGE revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` 이름의 로컬 snapshot과 기존 CPU BF16 벡터 조건을 모델 로딩 전에 확인한다. 캐시 폴더 이름 확인은 가중치의 독립 출처 검증을 대신하지 않는다. 실행 중인 비공개 v1 코드를 수정하지 않았으며 v1 체크포인트를 v2 계획으로 덮어쓰지 않는다. v2 재현에는 새 출력 폴더를 사용한다.

완료 배치마다 vector flush 이후 checkpoint를 저장하며, 문항/variant별 JSON을 원자적으로 저장한다. 같은 명령으로 재개하면 조건·소스 해시를 확인하고 완료 부분을 건너뛴다. 출력 경로는 저장소 밖 또는 Git에서 제외한 `data/` 아래만 허용한다. `aggregate.json` 외에도 원문을 담는 `items.local` 등이 생기므로 평가 출력 폴더 전체를 Git에 추가하지 않는다.

## CPU 생성과 가드

Ollama의 기존 모델을 준비한 후 승인된 별도 loopback 서비스에서 합성 readiness만 검사할 수 있다.

```sh
python evaluation/cpu_service.py --run --base-url http://127.0.0.1:11435
```

`num_gpu=0`을 명시하고 실제 적재 후 `size_vram=0`을 확인한다. CPU 전용 여부를 확인할 수 없으면 실패한다. 기존 설정 공급자는 `num_gpu`를 전달하지 않으므로 YAML에 옵션만 넣고 CPU라고 주장하지 않는다.

본 비교의 생성 evaluator는 메인 답변/규칙 검증 부품을 사용한 별도 프로토콜이다. 기존 Windows 등록 평가 가드를 우회한 공식 전체 평가로 표시하지 않는다. 독립 semantic judge를 부르지 않았으며 `judge_score=null`을 유지한다. RAGAS·Claude·OpenAI를 새로 호출하거나 키를 설치하지 않는다. 출력 한도에서 끊긴 응답, transport 오류, VRAM 확인 실패는 정상 성공의 0점으로 바꾸지 않는다.

같은 168질문·전체 100문서 검색 체크포인트에서 세 답변 처리를 실행하려면 다음 명령을 사용한다. 검색 문항 체크포인트가 아직 없으면 60초 간격으로 기다리며, 생성·검색 CPU 작업은 각각4스레드로 실행한다. 완료 항목은 같은 명령으로 재개할 때 건너뛴다.

```sh
python evaluation/generate_cpu_components.py --questions /authorized/confirmed-questions.jsonl --retrieval-run /authorized/new-review-run --output /authorized/new-generation-run --base-url http://127.0.0.1:11435
```

중단하려면 생성 출력 폴더에 빈 `STOP_REQUEST.local` 파일을 만든다. 현재 호출이 끝난 뒤 체크포인트를 저장하고 멈춘다. 재개 전에는 이 표시를 확인하고 사용자가 원할 때 제거한다. 오류 유형은 원문 없는 별도 분모로 기록한다. 실행 중 스크립트나 입력을 바꾸지 않는다.
