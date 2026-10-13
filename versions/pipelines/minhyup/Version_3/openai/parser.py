"""공개 노트북의 parser 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_parser():
    global EXPECTED_FILE_COUNT, STOP_ON_LOAD_ERROR, doc, documents, empty_pdf_pages, file_path, file_paths, load_errors, loaded_files, loader, markdown_path, markdown_text, number, p, page_number, pages, pdf_markdown_report, pdf_pages, row, valid_documents
    EXPECTED_FILE_COUNT = 100
    STOP_ON_LOAD_ERROR = True
    if not FILES_DIR.is_dir():
        raise FileNotFoundError(f'문서 폴더가 없습니다: {FILES_DIR}')
    file_paths = sorted((p for p in FILES_DIR.rglob('*') if p.is_file() and p.suffix.lower() in {'.pdf', '.hwp'}), key=lambda p: str(p).lower())
    if not file_paths:
        raise ValueError('./files에서 PDF 또는 HWP 파일을 찾지 못했습니다.')
    if len(file_paths) != EXPECTED_FILE_COUNT:
        pass
    pages = []
    loaded_files = []
    load_errors = []
    empty_pdf_pages = []
    pdf_markdown_report = []
    for number, file_path in enumerate(file_paths, start=1):
        try:
            if file_path.suffix.lower() == '.pdf':
                pdf_pages = pymupdf4llm.to_markdown(str(file_path), page_chunks=True)
                documents = []
                markdown_path = MARKDOWN_DIR / file_path.relative_to(FILES_DIR).with_suffix('.pdf.md')
                markdown_text = '\n\n'.join((row['text'] for row in pdf_pages))
                for page_number, row in enumerate(pdf_pages):
                    documents.append(Document(page_content=row['text'], metadata={'page': page_number, 'markdown_path': str(markdown_path), 'markdown_table_count': markdown_table_count(row['text'])}))
                pdf_markdown_report.append({'source': str(file_path), 'markdown_path': str(markdown_path), 'page_count': len(pdf_pages), 'markdown_table_count': markdown_table_count(markdown_text)})
            else:
                loader = HwpHwpxLoader(file_path=file_path, mode='single', extract_options=ExtractOptions(table_style=TableStyle.MARKDOWN), include_tables=True, include_notes=True, on_encrypted='raise', on_invalid='raise', on_error='raise')
                documents = loader.load()
            valid_documents = []
            for doc in documents:
                if not doc.page_content.strip():
                    if file_path.suffix.lower() == '.pdf':
                        empty_pdf_pages.append({'source': str(file_path), 'page': doc.metadata.get('page')})
                    continue
                doc.metadata.update({'source': str(file_path), 'file_name': file_path.name, 'relative_path': file_path.relative_to(FILES_DIR).as_posix(), 'file_type': file_path.suffix.lower().lstrip('.')})
                valid_documents.append(doc)
            if not valid_documents:
                raise ValueError('추출된 텍스트가 없습니다. 스캔/OCR 또는 문서 형식을 확인하세요.')
            pages.extend(valid_documents)
            loaded_files.append(str(file_path))
        except Exception as exc:
            load_errors.append({'source': str(file_path), 'error': f'{type(exc).__name__}: {exc}'})
    if load_errors and STOP_ON_LOAD_ERROR:
        raise RuntimeError('읽기 실패 파일이 있습니다. document_load_report.json을 확인하고 재실행하세요.')
    if not pages:
        raise ValueError('청킹할 문서 텍스트가 없습니다.')
