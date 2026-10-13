"""공개 노트북의 generation_model 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def render_chat_prompt(value):
    text = value.to_string() if hasattr(value, 'to_string') else str(value)
    return tokenizer.apply_chat_template([{'role': 'user', 'content': text}], tokenize=False, add_generation_prompt=True)

def generate_chat(value):
    rendered = render_chat_prompt(value)
    input_tokens = len(tokenizer(rendered, add_special_tokens=False)['input_ids'])
    limit = model.config.max_position_embeddings
    if input_tokens + MAX_NEW_TOKENS > limit:
        raise ValueError(f'입력 {input_tokens} + 출력 {MAX_NEW_TOKENS}토큰이 모델 한도 {limit}를 초과합니다. 검색 청크 수를 줄이세요.')
    return llm.invoke(rendered, pipeline_kwargs={'add_special_tokens': False})

def stage_generation_model():
    global MAX_NEW_TOKENS, bnb_config, chat_model, language_model_name, llm, llm_pipeline, model, tokenizer
    language_model_name = 'nlpai-lab/KULLM3'
    if not torch.cuda.is_available():
        raise RuntimeError('KULLM3 4bit 실행에는 CUDA용 PyTorch와 NVIDIA GPU가 필요합니다.')
    bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type='nf4', bnb_4bit_compute_dtype=torch.float16)
    tokenizer = AutoTokenizer.from_pretrained(language_model_name)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(language_model_name, quantization_config=bnb_config, device_map='auto')
    model.config.use_cache = True
    MAX_NEW_TOKENS = 512
    llm_pipeline = pipeline('text-generation', model=model, tokenizer=tokenizer, do_sample=False, repetition_penalty=1.2, return_full_text=False, max_new_tokens=MAX_NEW_TOKENS, use_cache=True, pad_token_id=tokenizer.pad_token_id)
    llm = HuggingFacePipeline(pipeline=llm_pipeline, model_id=language_model_name)
    chat_model = RunnableLambda(generate_chat)
