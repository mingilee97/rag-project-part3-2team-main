"""대화 기억. state 는 그냥 dict 이다: {"history": [(질문, 답)...], "last_docs": [doc_id...]}.

- `rewrite`: 앞 대화를 이어 묻는 질문("그 사업 예산은?")을 혼자 읽어도 뜻이 통하는 질문으로 고친다(로컬 LLM, JSON 한 줄).
- `remember`: 답이 나온 뒤 기록하고, 방금 다룬 문서를 last_docs 에 둔다.
"""
import json
import re

MAX_TURNS = 6
# 7.8B 모델은 혼자 읽어도 되는 질문까지 앞 문서를 덧붙여 고치므로, 앞을 가리키는 낱말이 있을 때만 모델에게 맡긴다.
FOLLOWUP = re.compile(r"^(그럼|그러면|그리고|또|다음)|그\s?(사업|두|기관|문서|쪽|중|것)|거기|해당 (사업|문서)|이 사업|더 자세히|방금|앞서|위 (사업|문서)")
_SCHEMA = {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}
_PROMPT = """앞선 대화를 보고, 마지막 질문을 앞 대화 없이도 뜻이 통하는 질문 한 문장으로 고쳐 쓴다.
- "그 사업", "그쪽", "그중"처럼 앞을 가리키는 말은 앞 대화에 나온 기관명과 사업명으로 바꾼다.
- 앞 대화와 상관없는 새 질문이면 한 글자도 바꾸지 말고 그대로 돌려준다. 앞 문서를 덧붙이지 않는다.
  예) "사업 금액이 가장 큰 사업은?", "교육 관련 사업은 어떤 것들이 있어?" 는 그대로 둔다.
- 앞 대화의 문서를 가리키는 질문("그 사업", "그럼 예산은?", "더 자세히")만 기관명과 사업명을 넣어 고친다.
- "그쪽", "그중"이 가장 최근 답의 결론(예: "OO의 예산이 더 크다")이 고른 쪽을 가리키면, 그 결론이 고른 기관과 사업명을 쓴다.

직전에 다룬 문서:
{docs}

앞선 대화:
{history}

마지막 질문: {q}
JSON 한 줄로 {{"question": "고친 질문"}} 만 답한다."""


def _prev_answer(a):
    """앞 답에서 질문을 고칠 때 볼 부분. 비교 답은 결론이 맨 끝 "### 비교 요약"에 있어 첫 200자로는 잘리므로 그 부분을 준다."""
    i = a.find("### 비교 요약")
    return a[i:i + 300] if i >= 0 else a[:200]


def new_state():
    return {"history": [], "last_docs": []}


def rewrite(question, state, cfg, info):
    """앞 대화가 없으면 그대로. info: doc_id -> {agency, title, ...} (answer.doc_info)."""
    if not state.get("history") or not FOLLOWUP.search(question):
        return question
    from rfp_rag.providers import get_llm
    docs = "\n".join(f"- {info[d]['agency']} / {info[d]['title']}" for d in state.get("last_docs", []) if d in info) or "(없음)"
    hist = "\n".join(f"질문: {q}\n답: {_prev_answer(a)}" for q, a in state["history"][-2:])
    llm = get_llm(cfg, json_schema=_SCHEMA, purpose="rewrite")
    try:
        return json.loads(llm.invoke(_PROMPT.format(docs=docs, history=hist, q=question)).content)["question"].strip() or question
    except Exception:  # 고치지 못하면 원래 질문으로 간다
        return question


def remember(state, question, answer, doc_ids):
    state["history"] = (state.get("history", []) + [(question, answer)])[-MAX_TURNS:]
    if doc_ids:
        state["last_docs"] = list(doc_ids)




if __name__ == "__main__":
    print("memory 자체 점검 통과")
