# VM·Colab 생성 평가 준비

사용자가 2026-10-09 로컬에서 어려운 설정을 기존 VM 또는 Colab에서 실행하도록 요청했다. 정상 로컬 검색은 유지한다. 이 문서는 실행 준비와 실제 실행을 구분한다. 새 VM 기동·유료 API·새 자격증명·키 이전은 실행하지 않았다. 현재 VM 연결·GPU 관리 정책·설치 상태와 Colab 세션 가용성은 아직 확인하지 못했다.

## 최소 코드와 의존성

공개 검토 브랜치의 `evaluation/generate_vm_components.py`, `evaluation/vm_service.py`, `evaluation/cpu_service.py`, `evaluation/vm-preflight.py`와 메인 `rfp_rag/{__init__,answer,providers,calllog,settings}.py`가 Linux VM GPU 생성 부품의 최소 실행 코드다. 기존 CPU 실행기도 별도로 보존했다. 전체 검색을 원격에서 다시 실행할 필요는 없다. 이미 같은 100문서로 계산한 context와 질문 체크포인트를 쓰면 된다. [패키지 허용목록](vm-package.json)은 코드15개만 담으며 원문 입력과 모델을 포함하지 않는다.

생성 코드의 외부 Python 의존성은 `langchain-core==1.6.6`, `PyYAML==6.0.3`이다. 이 버전은 현재 로컬에서 실제 확인한 값이다. 기존 VM/Colab에서 설치·실행 호환성을 확인한 값으로 표시하지 않는다. GPU 모델 실행은 Ollama가 담당하므로 이 생성 부품에는 Transformers·SentenceTransformers·Accelerate·PyTorch를 새로 설치할 필요가 없다. 먼저 다음 읽기 전용 검사로 기존 패키지를 확인한다.

```sh
python -B evaluation/vm-preflight.py
```

기존 환경에 패키지가 없다면 설치 범위와 디스크·네트워크 사용을 확인한 뒤 별도 환경에 준비한다. 전체 `requirements.txt`를 자동 설치하지 않는다. CPU transport는 표준 라이브러리 REST를 쓰므로 `langchain-ollama`와 외부 API SDK를 추가로 요구하지 않는다. 생성 모델은 기존 Ollama의 `exaone3.5:7.8b`를 사용한다. 모델이 없는 경우 다운로드 용량·저장 위치·승인된 범위를 먼저 확인하며 자동 `pull`이나 서버 설치를 하지 않는다.

## 비공개 입력과 전송 경계

생성에 필요한 비공개 입력은 확정 질문 파일, 검색의 `plan.local.json`, `items.local/`의 336체크포인트다. 문서 원본·KURE/BGE 가중치·검색 벡터는 생성만 실행할 때 필요하지 않다. 질문과 context에는 비공개 본문이 있으므로 공개 GitHub·공개 Colab notebook·공개 Drive 링크에 넣지 않는다. 대상 VM의 계정·접근 권한과 승인된 전송 경로를 확인한 후 필요한 파일만 옮겨야 한다. API 키·`.env`·SSH 키·브라우저 또는 런타임 계정 데이터를 포함하지 않는다.

파일을 VM에 준비한 뒤 입력 순서와 스키마를 다음 명령으로 확인한다. 출력에는 원문·문항 식별자·개인 경로·키가 없다.

```sh
python -B evaluation/vm-preflight.py --questions /authorized/confirmed-questions.jsonl --retrieval-run /authorized/full-cpu-100
python -B evaluation/vm-preflight.py --check-service --base-url http://127.0.0.1:11435
```

사전 점검은 모델을 적재하거나 질문하지 않는다. `/api/tags`와 `/api/ps`만 읽으며 서비스 URL은 인증정보 없는 loopback으로 제한한다. 모델 이름의 존재는 모델 가중치 digest 일치와 GPU 실행 준비의 증거가 아니다. 가중치 digest, Ollama 버전, GPU 종류·메모리, 관리 정책, 현재 적재 상태를 실행 전 별도 고정한다.

## 실행 조건과 체크포인트

기존 CPU evaluator는 VM/Colab에서도 `num_gpu=0`, CPU4스레드, context8192, 출력1500, seed42, temperature0을 유지한다. 키 없이 같은 메인 answer/verify 부품을 실행할 수 있다. 아래 명령은 CPU 참고용이며 GPU 실행 명령은 다음 절에 있다.

```sh
python -B evaluation/generate_cpu_components.py --questions /authorized/confirmed-questions.jsonl --retrieval-run /authorized/full-cpu-100 --output /authorized/new-generation-run --base-url http://127.0.0.1:11435
```

로컬 생성 출력에는 보류 표시 `STOP_REQUEST.local`이 있다. 그대로 보존하며 원격 실험에는 새 출력 폴더를 사용한다. CPU와 GPU를 같은 generation 체크포인트에 섞지 않는다. 같은 코드·source hashes·질문·검색 계획·모델 설정일 때만 재개한다. 현재 호출 뒤 중단하는 표시와 오류 분모 규칙은 CPU evaluator와 같다. 원시 답변은 비공개 `items.local/`에 저장하고 공개에는 집계만 사용한다.

## GPU 실행의 준비와 비교 한계

CPU 클라이언트는 VRAM 사용이 감지되면 실패한다. 새 GPU transport는 Linux VM/Colab 전용이며 Windows와 WSL을 거부한다. 모델은 Ollama0.35.1의 `exaone3.5:7.8b`, GGUF Q4_K_M, digest `c7c4e3d1ca22fe9225f18b35eb719f67e2ca96a42e7fd17294a45b83ba8fbf03`로 고정했다. 가중치 layer는 `fffbdeec0c334b27ebb42cbdd75a3e869cf9a3efc45abd7b3e6d739343089038`, 4,770,650,016바이트다. 실제 model/server digest를 확인하지 못하면 첫 질문 전에 중단한다. GPU 적재를 실제 `/api/ps`의 양수 VRAM으로 확인하지 못하면 해당 호출은 실패한다. 다른 모델이 적재된 서비스에도 실행하지 않는다.

Windows의 GPU50% 제한을 해제한 승인으로 해석하지 않는다. 새 transport의 `num_gpu=999`는 모든 layer의 GPU 적재를 요청하는 값이다. 실제 전체 layer 적재나 GPU 사용률50%와 VRAM50%를 함께 보장하는 설정으로 표시하지 않는다. VM 자원 관리 정책은 인프라 작업이 따로 확인하며 이 코드가 GPU 사용률 제한을 집행했다고 주장하지 않는다. 서비스는 전용 loopback 포트, 병렬1, 적재 모델1로 구성하고 기존 서비스에 간섭하지 않는다.

승인된 VM에서 고정 모델과 Ollama가 준비되면 합성 probe를 먼저 실행한다. API 키는 필요 없다. 이 probe는 실제 GPU 호출1회·출력 최대16토큰이다.

```sh
python -B evaluation/vm_service.py --execution-environment vm --base-url http://127.0.0.1:11435 --run-probe
```

전체100문서 검색의 입력을 준비한 뒤 GPU pilot12입력을 실행한다. 결과를 먼저 보고 문항을 바꾸지 않는다.

```sh
python -B evaluation/generate_vm_components.py --execution-environment vm --scope pilot4 --questions /authorized/confirmed-questions.jsonl --retrieval-run /authorized/retrieval --output /authorized/new-vm-gpu-pilot --base-url http://127.0.0.1:11435
```

전체504입력에는 같은 명령의 `--scope full`과 새 `--output /authorized/new-vm-gpu-full`을 사용한다. 같은 output에 pilot/full 또는 CPU/GPU를 섞으면 계획 검사에서 거부한다. Colab일 때는 `--execution-environment colab`을 명시한다. evaluator schema는 `vm-gpu-answer-component-v1`이며 기존 등록 가드는 그대로 보존한다. Linux 여부와 사용자가 지정한 실행 환경을 기록하지만 cloud 계정 소유권을 코드가 독립 검증했다고 표시하지 않는다.

GPU pilot의 질문은 결과를 보기 전에 첫 네 사업의 첫 질문4개로 고정하고 같은 세 처리의 12입력을 실행한다. GPU 전용 모델 digest와 설정을 기록한 뒤 같은 GPU 조건에서 처리끼리 비교한다. CPU pilot과 GPU 결과의 지연시간을 알고리즘 개선으로 단정하지 않는다. 전체504입력의 추가 소요 시간과 과금은 해당 pilot의 실제 관측으로 갱신한다. 독립 semantic judge는 호출하지 않았으므로 실행 성공·숫자 규칙 검사·문자열 포함 회수를 답변 정확도로 부르지 않는다.

기존 VM을 켜거나 자원을 늘리면 region·machine·GPU·디스크·네트워크·시작 및 종료 범위와 증분 비용 확인이 먼저 필요하다. 기존 기록의 L4/4CPU/16GB가 현재 상태라는 보장은 없다. Colab GPU 종류·메모리·할당·세션 시간과 비용은 계정 및 시점에 따라 달라진다. [Colab 공식 FAQ](https://research.google.com/colaboratory/faq.html#resource-limits)의 제한을 참고하며 무료 세션이나 특정 GPU 배정을 확정하지 않는다.

## 반환할 결과

원격 실행이 가능하면 evaluator schema·Git commit·모델 digest·입력 SHA·자원 및 설정·성공/오류 분모·처리별 실제 지연·독립 judge 미실행 상태가 있는 집계 JSON을 반환한다. 기존 전체 검색 집계의 treatment 이름과 질문 정렬을 유지한다. source answer 파일은 CRLF/LF 정규화 해시와 SYSTEM/schema 해시도 기록해 플랫폼 차이를 구분한다. 모델 선정과 운영 `07_verify` 채택은 별도 결정이며 원격 평가만으로 대시보드 채택 상태를 바꾸지 않는다.
