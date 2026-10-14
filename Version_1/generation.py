"""공개 노트북의 generation 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def answer_question(query, search_method=None):
    selected_method = method if search_method is None else search_method
    project_key, search_text, found, reranked_docs = retrieve_and_rerank(query, selected_method)
    context = '\n\n'.join((f'[{j}] 메타데이터: {doc.metadata}\n본문: {doc.page_content}' for j, doc in enumerate(reranked_docs, start=1)))
    answer = chat_model.invoke(answer_rules.format(context=context, query=query)).content.strip()
    return {'query': query, 'identified_agency': project_key[0], 'identified_project': project_key[1], 'search_text': search_text, 'answer': answer, 'contexts': [doc.page_content for doc in reranked_docs], 'chunk_ids': [doc.metadata['chunk_id'] for doc in reranked_docs]}

def stage_generation():
    global answer_rules, hyde_search_rules
    hyde_search_rules = '너는 RFP에서 관련 문단을 찾기 위한 가상 안내문 작성자야.\n실제 답변이 아니라 검색에 쓸 안내문 1문장만 작성해.\n- 질문의 핵심 주제어를 그대로 포함해.\n- 질문과 관계없는 다른 사업이나 항목으로 이동하지 마.\n- 확인되지 않은 금액, 날짜, 법률, 자격 조건을 단정하지 마.\n- 제목, 목록, 따옴표, 추가 설명을 쓰지 마.\n\n예시:\n질문: 이 사업의 입찰 참여 자격은 무엇인가요?\n가상 안내문: 이 사업의 입찰 참여 자격에 관한 조건이 안내되어 있다.'
    answer_rules = '\n너는 RFP 문서의 사실 확인 담당자다. 아래 <문서>에 적힌 내용만으로 <질문>에 답한다.\n\n규칙:\n1. 질문이 여러 항목을 묻는다면 항목별로 근거를 따로 찾는다.\n2. 질문의 사업명과 다른 사업의 정보는 사용하지 않는다.\n3. 각 항목에 대해 문서에서 직접 인용할 수 있는 문구를 먼저 제시한다.\n4. 직접 인용할 근거가 없는 항목은 추측하지 말고 "제공된 문서에서 확인할 수 없습니다"라고 쓴다.\n5. 금액, 기간, 날짜, 비율, 인력, 제출 조건은 문서의 표현을 그대로 옮긴다. 계산하거나 일반적인 관행으로 빈칸을 채우지 않는다.\n6. 답변의 각 사실 바로 뒤에 근거 문서 번호 [1]처럼 붙인다.\n7. HyDE 검색 문장과 모델의 사전 지식은 근거로 사용하지 않는다.\n\n출력 형식:\n근거:\n- 항목명: [문서 번호] "문서에서 그대로 가져온 짧은 문구"\n- 근거가 없는 항목명: 확인 불가\n\n답변:\n근거가 확인된 내용만 간결하게 답한다. 근거가 없는 항목은 확인할 수 없다고 밝힌다.\n\n<문서>\n{context}\n</문서>\n\n<질문>\n{query}\n</질문>\n'
