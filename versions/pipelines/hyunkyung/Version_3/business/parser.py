"""공개 노트북의 parser 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def normalize_filename(name):
    name = str(name).rsplit('.', 1)[0]
    name = unicodedata.normalize('NFKC', name)
    return re.sub('\\s+', ' ', name).strip()

def stage_parser():
    global column, documents, extension, full_path, loaded_files, loader, metadata, metadata_columns, name, options, result_df, row, text
    loaded_files = []
    for name in sorted_file_names:
        full_path = os.path.join(folder, name)
        extension = name.rsplit('.', 1)[-1].lower()
        if extension == 'pdf':
            text = pymupdf4llm.to_markdown(full_path)
        elif extension in 'hwp':
            options = ExtractOptions(table_style=TableStyle.MARKDOWN)
            loader = HwpHwpxLoader(full_path, mode='single', extract_options=options)
            text = loader.load()[0].page_content
        loaded_files.append((name, text))
    metadata_columns = ['공고 번호', '공고 차수', '사업명', '사업 금액', '발주 기관', '공개 일자', '입찰 참여 시작일', '입찰 참여 마감일', '파일명']
    documents = []
    for name, text in loaded_files:
        result_df = df[df['파일명'].apply(normalize_filename) == normalize_filename(name)]
        if result_df.empty:
            continue
        row = result_df.iloc[0]
        metadata = {column: row[column] for column in metadata_columns}
        documents.append(Document(page_content=text, metadata=metadata))
