"""공개 노트북의 local_model 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_local_model():
    global chat_model, language_model_name, llm, llm_pipeline, method, model, model_revision, tokenizer
    language_model_name = 'LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct-AWQ'
    model_revision = 'f2699f35d5b4ba511ab93826c22bd07370296b5c'
    model = AutoModelForCausalLM.from_pretrained(language_model_name, torch_dtype=torch.float16, trust_remote_code=True, device_map='auto', revision=model_revision)
    tokenizer = AutoTokenizer.from_pretrained(language_model_name, revision=model_revision)
    llm_pipeline = pipeline(task='text-generation', model=model, tokenizer=tokenizer, do_sample=False, repetition_penalty=1.2, return_full_text=False, max_new_tokens=220)
    llm = HuggingFacePipeline(pipeline=llm_pipeline)
    chat_model = ChatHuggingFace(llm=llm)
    method = 'basic'
