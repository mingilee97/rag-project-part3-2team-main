"""공개 노트북의 generation_model 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_generation_model():
    global chat_model, method
    method = 'basic'
    if not os.getenv('OPENAI_API_KEY'):
        pass
    chat_model = ChatOpenAI(model='gpt-5-mini-2025-08-07')
