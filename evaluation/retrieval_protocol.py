"""이전 벡터와 새 모델 캐시의 조건이 일치하는지 모델 실행 전에 확인한다."""
from pathlib import Path

KURE_REVISION = '8b418a58414668e75532ed045c22d9ca018ae2b2'
BGE_REVISION = '953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e'
SEARCH_DEFINITION = 'exhaustive dot product on nominally normalized BF16-derived float32 vectors; no ANN'


def validate_reuse_protocol(previous_conditions, kure_snapshot, bge_snapshot):
    expected = {'model': 'nlpai-lab/KURE-v1', 'revision': KURE_REVISION,
                'device': 'cpu', 'parameter_dtype': 'torch.bfloat16',
                'normalize_embeddings': True, 'batch_size': 8,
                'torch_threads': 4, 'max_seq_length': 8192}
    for key, value in expected.items():
        if previous_conditions.get(key) != value:
            raise ValueError(f'기존 벡터의 {key} 조건이 현재 비교와 다릅니다')
    for path, revision, model_name in [(kure_snapshot, KURE_REVISION, 'KURE'),
                                       (bge_snapshot, BGE_REVISION, 'BGE')]:
        snapshot = Path(path).resolve()
        if snapshot.name != revision or not (snapshot / 'config.json').is_file():
            raise ValueError(f'{model_name} 캐시는 고정 revision 이름의 snapshot과 config.json이 필요합니다')
    # 폴더 이름 검사는 캐시 선택 오류를 막는다. 가중치의 독립 출처 검증을 대신하지 않는다.
    return {'embedding_revision': KURE_REVISION, 'reranker_revision': BGE_REVISION,
            'snapshot_revision_names_verified': True, 'model_weights_independently_hashed': False,
            'search_definition': SEARCH_DEFINITION, 'exact_cosine': False,
            'bf16_norm_rounding_preserved': True}
