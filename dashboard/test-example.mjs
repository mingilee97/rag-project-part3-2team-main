// 원본에서 생성한 두 UI 버전의 날짜 경계와 경로 계약을 합성 데이터로 확인한다.
import assert from 'node:assert/strict';
for (const version of ['calendar-unified-20261008','roadmap-readable-20261008']) {
  const calendar=await import(`./example/modules/${version}/calendarDate.mjs`);
  assert.equal(calendar.seoulToday(new Date('2030-01-01T15:00:00Z')),'2030-01-02');
  assert.equal(calendar.shiftCalendarMonth('2032-01-31',1),'2032-02-29');
  assert.equal(calendar.isCalendarDay('2030-02-29'),false);
  assert.equal(calendar.weekStartSunday('2030-01-01'),'2029-12-30');
  assert.equal(calendar.sundayCalendarDays(2030,0)[0],'2029-12-30');
  const graph=await import(`./example/modules/${version}/processRoadmapLayout.mjs`);
  for(const route of ['meta','single','compare','search']){
    const edges=graph.connectedEdges(route);assert.equal(edges.length,29);
    assert.equal(new Set(edges.map(e=>e.id)).size,29);
    const sequence=graph.flowSequences('query',route)[0];
    assert.equal(sequence.at(-1),route==='compare'?'compare-output':'answer-output');
    assert.equal(sequence.includes('weak-gate'),route!=='meta');
    assert.equal(edges.filter(e=>e.id.startsWith('route-')&&e.selected).length,1);
  }
  const edge=graph.connectedEdges('single')[0];
  const points={s1:{x:110,y:65,left:30,right:190,top:35,bottom:95},s2:{x:470,y:65,left:390,right:550,top:35,bottom:95}};
  assert.match(graph.edgePath(edge,points,940),/^M/);
}
console.log('두 버전의 날짜 경계·4개 질문 분기·29개 연결 계약이 통과했습니다.');
