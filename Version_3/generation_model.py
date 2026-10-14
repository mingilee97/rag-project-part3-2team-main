"""공개 노트북의 generation_model 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_generation_model():
    global chat_model, llm
    llm = ChatOpenAI(model=LLM_MODEL, max_completion_tokens=OUTPUT_TOKEN_LIMIT, reasoning_effort='low')
    chat_model = llm
