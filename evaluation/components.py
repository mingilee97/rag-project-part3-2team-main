"""검색 부품 비교의 공통 스키마·원문 근거 보존·예산 검사. 합성 selftest 포함."""
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rfp_rag.ingest.chunk import chunk_fixed
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'candidates/minhyup/10882e3'))
from rag_chunking import build_parent_children
from rag_context import format_context, count_tokens

def norm(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFC', text)).lower()

def fact_norm(text):
    return re.sub(r'[\s,]', '', unicodedata.normalize('NFC', text)).lower()

def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None

def source_of(q):
    return q.get('_original') or q.get('_source') or q

def anchors(q):
    src = source_of(q)
    parts = []
    for value in src.get('evidence_quotes', []):
        if not isinstance(value, str):
            continue
        quoted = [a or b for a,b in re.findall(r'“([^”]+)”|"([^"\n]+)"', value)]
        for part in quoted or [value]:
            if re.search(r'\.{3,}|…', part):
                continue
            if len(re.sub(r'[\W_]+', '', part)) >= 12:
                parts.append(norm(part))
    return list(dict.fromkeys(parts))

def facts(q):
    src = source_of(q)
    return src.get('required_facts') or q.get('key_facts') or []

def covered(items, texts, alternatives=False):
    normalize = fact_norm if alternatives else norm
    bodies = [normalize(t) for t in texts]
    return [any(normalize(alt) in body for body in bodies for alt in (x.split('|') if alternatives else [x]))
            for x in items]

def alignment(rows):
    digest=hashlib.sha256()
    for row in rows:
        payload=json.dumps(row,ensure_ascii=False,sort_keys=True).encode()
        digest.update(str(len(payload)).encode()+b':'+payload)
    return digest.hexdigest()

def build(docs):
    fixed,children,details,parents=[],[],{},{}
    errors={'main_offset':0,'candidate_offset':0,'parent_link':0,'main_body':0}
    splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200,add_start_index=True)
    for doc in docs:
        prefix=f"[{doc['agency']}] {doc['title']}\n"
        main_rows=chunk_fixed(doc,1000,200)
        offset_rows=splitter.create_documents([doc['text']])
        assert len(main_rows)==len(offset_rows)
        for row,body in zip(main_rows,offset_rows):
            start=body.metadata['start_index'];end=start+len(body.page_content)
            errors['main_body']+=row['text']!=prefix+body.page_content
            errors['main_offset']+=doc['text'][start:end]!=body.page_content
            fixed.append(row)
            details[('main',row['chunk_id'])]={'source_group':doc['doc_id'],'start':start,'end':end,
                'doc_id':doc['doc_id'],'source':doc['source_file'],'section_title':row.get('section_path','')}
        local_parents,local_children=build_parent_children([Document(page_content=doc['text'],metadata={
            'source':doc['source_file'],'doc_id':doc['doc_id']})],1000,200,8000)
        for local_id,parent in local_parents.items():
            key=(doc['doc_id'],local_id)
            assert key not in parents
            parents[key]=parent
        for child in local_children:
            ident=f"{doc['doc_id']}:candidate:{child.metadata['chunk_id']}"
            parent_key=(doc['doc_id'],child.metadata['parent_id'])
            errors['parent_link']+=parent_key not in parents
            errors['candidate_offset']+=parents[parent_key].page_content[
                child.metadata['start_index']:child.metadata['end_index']]!=child.page_content
            children.append({'doc_id':doc['doc_id'],'chunk_id':ident,'text':prefix+child.page_content})
            details[('candidate',ident)]={'source_group':parent_key,'parent_key':parent_key,
                'doc_id':doc['doc_id'],'source':doc['source_file'],
                'start':child.metadata['start_index'],'end':child.metadata['end_index'],
                'section_title':child.metadata.get('section_title',''),
                'pages':child.metadata.get('pages',[]),'original_child_id':child.metadata['chunk_id']}
    assert not any(errors.values()),errors
    return {'main_fixed1000_200':fixed,'minhyup_child1000_200':children},details,parents,errors

def header(doc,rank):
    m=doc.metadata
    return (f"[근거 {rank}] 파일: {m.get('file_name',m.get('source',''))}\n"
            f"섹션: {m.get('section_title','')}\n"
            f"매칭 child 페이지(0부터): {m.get('matched_child_pages',[])}\n")

def bounded(docs,budget,per_parent):
    saved={}
    def trace(frame,event,arg):
        if frame.f_code is format_context.__code__ and event=='return':
            saved['parts']=list(frame.f_locals.get('parts',[]))
        return trace
    previous=sys.gettrace()
    sys.settrace(trace)
    try:
        text=format_context(docs,token_budget=budget,per_parent_budget=per_parent,debug=False)
    finally:
        sys.settrace(previous)
    parts=saved.get('parts',[])
    assert text=='\n\n'.join(parts)
    assert count_tokens(text)<=budget
    bodies=[]
    for rank,(doc,part) in enumerate(zip(docs,parts),1):
        prefix=header(doc,rank)
        assert part.startswith(prefix)
        body=part[len(prefix):]
        if body.startswith('[관련 구간 발췌]\n'):
            body=body[len('[관련 구간 발췌]\n'):]
        bodies.append((doc.metadata['doc_id'],body))
    return text,bodies

def coverage(q,bodies,aq,af,present):
    gold=set(q['answer_doc_ids'])
    correct=[body for doc_id,body in bodies if doc_id in gold]
    quote=covered(aq,correct)
    fact=covered(af,correct,True)
    hit_instances=sum(sum(covered(aq,[body])) for body in correct)
    return {'quotes':quote,'facts':fact,'quote_gold_hits':sum(quote),
        'present_quote_gold_hits':sum(p and h for p,h in zip(present,quote)),
        'quote_hit_instances':hit_instances,'duplicate_quote_hit_instances':hit_instances-sum(quote),
        'fact_gold_hits':sum(fact),'provided_doc_count':len({doc_id for doc_id,_ in bodies}),
        'provided_gold_doc_count':len(gold & {doc_id for doc_id,_ in bodies}),
        'provided_gold_doc_recall':len(gold & {doc_id for doc_id,_ in bodies})/len(gold)}

def test_helpers():
    q={'answer_doc_ids':['gold']}
    phrase='동일한 근거 인용문은 충분히 긴 문장입니다.'
    doc=Document(page_content=phrase*500,metadata={'doc_id':'gold','source':'synthetic','matched_start_index':0})
    for budget in [10,200,2000]:
        text,bodies=bounded([doc],budget,budget)
        assert count_tokens(text)<=budget
    assert coverage(q,[('wrong',phrase)],[phrase],[],[True])['quote_gold_hits']==0
    assert coverage(q,[('gold',phrase),('gold',phrase)],[phrase],[],[True])['duplicate_quote_hit_instances']==1
    sample=[{'chunk_id':'a'},{'chunk_id':'b'}]
    d={('main','a'):{'source_group':'g','start':0,'end':100},('main','b'):{'source_group':'g','start':80,'end':150}}
    assert intervals(sample,d,'main')['overlap_duplicate_characters']==20
    return {'budget_checks':3,'gold_doc_only_check':True,'duplicate_quote_check':True,'overlap_union_check':True}
