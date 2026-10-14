"""설정(provider)에 따라 채팅 모델과 임베딩을 만든다. 모델을 부를 때마다 calllog 에 한 줄이 남는다."""
import os
import json
import time

from langchain_core.callbacks import BaseCallbackHandler

from rfp_rag import calllog

NO_KEY = "OpenAI 키가 없습니다. 환경 변수 OPENAI_API_KEY를 설정하세요."


def _key(api_key, variable="OPENAI_API_KEY"):
    key = api_key or os.environ.get(variable)
    if not key:
        raise RuntimeError(NO_KEY if variable == "OPENAI_API_KEY" else
                           "Anthropic 키가 없습니다. 환경 변수 ANTHROPIC_API_KEY를 설정하세요.")
    return key


class _LogCalls(BaseCallbackHandler):
    """채팅 모델의 실제 호출과 사용량을 기록한다."""

    def __init__(self, provider, model, purpose):
        self.provider, self.model, self.purpose, self.t0 = provider, model, purpose, {}

    def on_chat_model_start(self, serialized, messages, *, run_id, **kw):
        self.t0[run_id] = time.time()

    def on_llm_end(self, response, *, run_id, **kw):
        u = getattr(response.generations[0][0].message, "usage_metadata", None) or {}
        calllog.log_call(self.provider, self.model, self.purpose, u.get("input_tokens", 0),
                         u.get("output_tokens", 0), time.time() - self.t0.pop(run_id, time.time()))


def get_llm(cfg, section="llm", json_schema=None, purpose=None, api_key=None):
    """cfg[section]으로 채팅 모델을 만든다.

    json_schema: 공급자별 구조화 출력을 기존 JSON 문자열 호출 규약에 맞춘다.
    """
    c = cfg[section]
    provider, model, purpose = c["provider"], c["model"], purpose or section
    cb = [_LogCalls(provider, model, purpose)]
    if provider == "anthropic":
        key = _key(api_key, "ANTHROPIC_API_KEY")
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, api_key=key, temperature=c.get("temperature", 0),
                            max_tokens=c.get("max_tokens", 1500), timeout=c.get("timeout", 120),
                            max_retries=0, callbacks=cb)
        if json_schema:
            from langchain_core.messages import AIMessage
            from langchain_core.runnables import RunnableLambda
            tool = {"name": "rag_response", "description": "주어진 RAG 응답 스키마를 채웁니다.",
                    "input_schema": json_schema}
            structured = llm.with_structured_output(tool, method="function_calling")
            return structured | RunnableLambda(lambda value: AIMessage(content=json.dumps(value, ensure_ascii=False)))
        return llm
    if provider == "local":
        from langchain_ollama import ChatOllama
        # reasoning=False: qwen3.5 같은 생각 모드 모델이 생각 글을 쓰느라 시간과 토큰을 쓰지 않게 끈다.
        return ChatOllama(model=model, base_url=c.get("base_url", "http://127.0.0.1:11434"),
                          temperature=c.get("temperature", 0), num_ctx=c.get("num_ctx", 8192),
                          reasoning=c.get("reasoning", False), format=json_schema, callbacks=cb,
                          keep_alive=c.get("keep_alive", "5m"), num_predict=c.get("num_predict", 1500))  # 쓰고 나면 5분 뒤 메모리에서 내린다
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=cfg["openai"]["chat_model"] if section == "llm" else model,
                         api_key=_key(api_key), temperature=c.get("temperature", 0), callbacks=cb)
        if json_schema:
            llm = llm.bind(response_format={"type": "json_schema",
                                            "json_schema": {"name": "answer", "schema": json_schema}})
        return llm
    raise ValueError(f"알 수 없는 provider: {provider} (anthropic | local | openai)")


def get_embeddings(cfg, api_key=None):
    c = cfg["embeddings"]
    if c["provider"] == "local":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=c["model"], model_kwargs={"device": c.get("device", "cuda")},
                                     encode_kwargs={"normalize_embeddings": True})
    if c["provider"] == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=cfg["openai"]["embedding_model"], api_key=_key(api_key))
    raise ValueError(f"알 수 없는 embeddings provider: {c['provider']} (local | openai)")
