"""공개 노트북의 cleaning 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_cleaning():
    global document, text
    for document in documents:
        text = document.page_content.replace('\r\n', '\n')
        text = re.sub('[ \\t]+', ' ', text)
        document.page_content = re.sub('\\n{3,}', '\n\n', text).strip()
