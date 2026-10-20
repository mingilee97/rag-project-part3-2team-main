"""원본 FINAL-02 프롬프트와 Claude 생성 연결."""
from pathlib import Path
ANSWER_RULES = (Path(__file__).resolve().parent.parent / "prompts/final02.txt").read_text(encoding="utf-8")

def create_chat_model(settings):
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=settings.generation_model, max_tokens=settings.generation_max_tokens,
                         timeout=settings.generation_timeout, max_retries=settings.generation_retries)

def _content(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()
    return ""
