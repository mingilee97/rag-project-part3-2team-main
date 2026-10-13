# hyunkyung/Version_2

출처: `HyeongyeongKim/codeit_second_project` · commit `17614c5005f5e0d78b2d20f466600a86ab5c5379`

구분: 형식만 변환 · 미채택; 기존 평가의 회귀 때문에 보류

## 원본 → 모듈

| 단계 | 실제 코드 |
|---|---|
| parser | 이 버전에서 미확보/미변환 |
| chunking | 이 버전에서 미확보/미변환 |
| embedding | 이 버전에서 미확보/미변환 |
| retrieval | [business_identifier.py](business_identifier.py) |
| generation | 이 버전에서 미확보/미변환 |
| verification | 이 버전에서 미확보/미변환 |

실행: resolve_project(question, doc_info, aliases=None). 합성 입력으로만 검사하며 평가 전 채택하지 않습니다.

확보되지 않은 부분:

- parser/chunking/embedding/generation/verification의 이 버전 독립 변환 미완료
- 원본 전역 카탈로그는 호출자가 전달해야 함
