"""공개 노트북의 generation 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def format_docs(docs):
    return '\n\n'.join((doc.page_content for doc in docs))

def stage_generation():
    global prompt, retrieval_chain, template
    template = '\n아래에 주어진 맥락을 이용해 질문에 대해 답변해 줘.\n주어진 맥락으로 답변이 어려운 상황이라면, 그냥 모른다고 답하면 되고 억지로 답변을 꾸며 내지 마.\n최대한 자세하게 답변해 줘.\n반드시 한국어로 답변해야 해.\n\n맥락:\n{context}\n\n질문:\n{question}\n'
    prompt = PromptTemplate.from_template(template)
    retrieval_chain = {'context': retriever | format_docs, 'question': RunnablePassthrough()} | prompt | chat_model | StrOutputParser()
