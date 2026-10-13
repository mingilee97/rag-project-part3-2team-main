// 모든 표시 데이터는 공개용 합성 입력이다. 원격 요청·저장 동작은 없다.
const titles = [['데이터 준비','원본 등록','본문 추출','청크 생성'], ['검색 준비','임베딩','질문 분류','근거 검색'], ['답변 생성','리랭킹 후보','답변 작성','근거 검증'], ['평가와 결정','평가 조건','지표 계산','버전 결정']];
const $ = selector => document.querySelector(selector);
async function render() {
  const version = $('#version').value, route = $('#route').value;
  const calendar = await import(`./modules/${version}/calendarDate.mjs`);
  const graph = await import(`./modules/${version}/processRoadmapLayout.mjs`);
  $('#parts').replaceChildren(...titles.map(([title,...stages], part) => {
    const card=document.createElement('div');card.className='part';
    const heading=document.createElement('h3');heading.textContent=`${part+1}. ${title}`;
    const list=document.createElement('ol');list.start=part*3+1;
    for(const stage of stages){const item=document.createElement('li');item.textContent=stage;list.append(item)}
    card.append(heading,list);return card;
  }));
  const sequence=graph.flowSequences('query',route)[0];
  $('#flow').textContent=`선택 경로: ${sequence.join(' → ')} · 연결 관계 ${graph.connectedEdges(route).length}개`;
  const edge=graph.connectedEdges(route).find(e=>e.id==='prepare-read');
  const points={s1:{x:110,y:65,left:30,right:190,top:35,bottom:95},s2:{x:470,y:65,left:390,right:550,top:35,bottom:95}};
  const svg=$('#geometry');svg.replaceChildren();
  for(const p of Object.values(points)){const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');for(const[k,v]of Object.entries({x:p.left,y:p.top,width:p.right-p.left,height:p.bottom-p.top,rx:8,fill:'#edf5ff',stroke:'#a6bedb'}))rect.setAttribute(k,v);svg.append(rect)}
  const line=document.createElementNS('http://www.w3.org/2000/svg','path');line.setAttribute('d',graph.edgePath(edge,points,940));line.setAttribute('fill','none');line.setAttribute('stroke','#2764a9');line.setAttribute('stroke-width','3');svg.append(line);
  $('#calendar').replaceChildren(...calendar.CALENDAR_WEEKDAYS.map(name=>{const day=document.createElement('strong');day.textContent=name;return day}),...calendar.sundayCalendarDays(2030,0).map(date=>{const day=document.createElement('div');day.className='day'+(date.slice(0,7)!=='2030-01'?' outside':'');day.textContent=date.slice(8);return day}));
  $('#role').textContent=version.startsWith('calendar')?'2026-10-08 인계에서 운영 기준으로 보고된 체크포인트입니다. 이번 작업에서 실제 배포 상태를 재확인하지 않았습니다.':'연결선 가독성을 검토한 로컬 후보입니다. 운영 배포나 모델 채택을 하지 않았습니다.';
}
$('#version').addEventListener('change',render);$('#route').addEventListener('change',render);render();
