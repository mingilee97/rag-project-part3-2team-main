# Version 2

실제 원본에서 분리한 단계 코드 8개를 이 폴더에 포함했습니다. 별도 원본 복사가 필요 없습니다. [version.json](version.json)은 과거 설정과 Haiku 배포 설정, [provenance.json](provenance.json)은 고정 SHA·원본 셀·AST와 파일 해시를 보존합니다. 필수 출처는 [SOURCE-NOTES](../SOURCE-NOTES.md)에 있습니다.

포함 파일: chunking.py · cleaning.py · embedding.py · generation.py · generation_model.py · parser.py · retrieval.py · verification.py

```sh
python -m pip install -r Version_2/requirements.txt
python Version_2/run.py --check
python Version_2/run.py --smoke
python Version_2/run.py --input-dir data/raw --metadata data/data_list.csv --ask "사업 요구사항을 설명해 줘."
```

위 명령은 저장소 루트에서 실행합니다. --check와 --smoke에는 키·모델 다운로드·API 호출이 없습니다. --ask는 실제 원본 파서·청킹·임베딩·검색을 실행하고 생성 공급자만 Haiku로 연결합니다. 개인 키·문서·모델을 준비해야 하며 API 비용이 발생할 수 있습니다. 원래 CUDA/FAISS/모델 조건을 임의 변경하지 않았습니다.

공통 세션은 `from version_runtime import VersionSession`, `VersionSession('v2', providers)`입니다. 직접 연결하지 않아도 CLI가 version_inputs.prepare로 실제 라이브러리와 입력을 준비합니다. 공통 run/call 입구는 포함된 원본 함수를 실행하며 동일한 결과를 내는 대체 알고리즘으로 바꾸지 않았습니다. Version 3의 components는 원본 청킹·재순위·문맥 구성 부품이며 중복 복사를 피하려고 공유합니다.

실제 모델 품질을 평가하지 않았습니다. 기존 EXAONE·Luna 평가 근거와 Haiku 변경 이후를 구분합니다. 현재 후보의 동일조건 성능 순위는 비교 보류입니다.
