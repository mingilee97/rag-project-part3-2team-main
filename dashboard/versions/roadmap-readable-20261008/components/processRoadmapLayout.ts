export type QueryRoute = 'meta' | 'single' | 'compare' | 'search';
export type FlowKind = 'prepare' | 'query' | 'evaluate';
export type FlowRect = { left: number; right: number; top: number; bottom: number };
export type FlowPoint = { x: number; y: number } & Partial<FlowRect>;
export type ProcessEdge = { id: string; from: string; to: string; kind: 'material' | 'reference' | 'bypass' | 'retry' | 'inactive'; selected?: boolean };

// Source configuration relationships; editing an experiment does not rewrite runtime topology.
export function connectedEdges(route: QueryRoute): ProcessEdge[] {
  const edges: ProcessEdge[] = [
    { id: 'prepare-read', from: 's1', to: 's2', kind: 'material' },
    { id: 'prepare-chunk', from: 's2', to: 's3', kind: 'material' },
    { id: 'prepare-embed', from: 's3', to: 's4', kind: 'material' },
    { id: 'prepare-index', from: 's4', to: 'chroma', kind: 'material' },
    { id: 'prepare-summary', from: 's4', to: 'summary', kind: 'material' },
    { id: 'stored-index', from: 'chroma', to: 's6', kind: 'reference' },
    { id: 'stored-summary', from: 'summary', to: 'route-search', kind: 'reference' },
    { id: 'query-input', from: 'question', to: 's5', kind: 'material' },
    ...(['meta', 'single', 'compare', 'search'] as const).map(name => ({ id: 'route-' + name, from: 's5', to: 'route-' + name, kind: 'material' as const, selected: route === name })),
    { id: 'query-grounding', from: 's6', to: 'weak-gate', kind: 'material', selected: route !== 'meta' },
    { id: 'conditional-gate', from: 'weak-gate', to: 's8', kind: 'material', selected: route !== 'meta' },
    { id: 'meta-gate-bypass', from: 'route-meta', to: 'direct-evidence', kind: 'bypass', selected: route === 'meta' },
    { id: 'direct-generation', from: 'direct-evidence', to: 's8', kind: 'material', selected: route === 'meta' },
    { id: 'answer-verification', from: 's8', to: 's9', kind: 'material' },
    { id: 'same-evidence-once', from: 's9', to: 's8', kind: 'retry' },
    { id: 'weak-reject', from: 'weak-gate', to: 'not-found', kind: 'bypass' },
    { id: 'reject-output', from: 'not-found', to: 'answer-output', kind: 'bypass' },
    { id: 'verified-output', from: 's9', to: route === 'compare' ? 'compare-output' : 'answer-output', kind: 'material' },
    { id: 'inactive-reranker', from: 's6', to: 's7', kind: 'inactive' },
    { id: 'evaluation-rules', from: 's10', to: 's11', kind: 'material' },
    { id: 'evaluation-judge', from: 's10', to: 'judge', kind: 'material' },
    { id: 'rules-record', from: 's11', to: 's12', kind: 'material' },
    { id: 'judge-record', from: 'judge', to: 's12', kind: 'material' },
  ];
  for (const name of ['single', 'compare', 'search'] as const) edges.push({ id: name + '-retrieve', from: 'route-' + name, to: 's6', kind: 'material', selected: route === name });
  return edges;
}

export function flowSequences(kind: FlowKind, route: QueryRoute): string[][] {
  if (kind === 'prepare') return [['s1', 's2', 's3', 's4', 'chroma']];
  if (kind === 'evaluate') return [['s10', 's11', 's12'], ['s10', 'judge', 's12']];
  const start = ['question', 's5', 'route-' + route];
  if (route === 'meta') return [[...start, 'direct-evidence', 's8', 's9', 'answer-output']];
  return [[...start, 's6', 'weak-gate', 's8', 's9', route === 'compare' ? 'compare-output' : 'answer-output']];
}

export type EdgeTone = 'process' | 'branch' | 'retrieval' | 'reference' | 'csv' | 'failure' | 'verify' | 'retry' | 'inactive';
export type PortSide = 'top' | 'bottom' | 'left' | 'right';
export type EdgeGeometry = { path: string; points: FlowPoint[]; ports: { from: PortSide; to: PortSide } | null };

// Presentation distinguishes the two source-defined bypasses without changing topology.
export function edgePresentation(edge: ProcessEdge): { tone: EdgeTone; label: string } {
  if (edge.kind === 'reference') return { tone: 'reference', label: '저장한 근거 참조' };
  if (edge.kind === 'retry') return { tone: 'retry', label: '같은 근거 · 최대 1회' };
  if (edge.kind === 'inactive') return { tone: 'inactive', label: '꺼짐 · 건너뜀' };
  if (edge.id === 'meta-gate-bypass' || edge.id === 'direct-generation') return { tone: 'csv', label: 'CSV 근거 · gate 우회' };
  if (edge.id === 'weak-reject' || edge.id === 'reject-output') return { tone: 'failure', label: edge.id === 'weak-reject' ? '근거 부족 · 생성 차단' : '근거 부족 안내 반환' };
  if (edge.id === 'answer-verification') return { tone: 'verify', label: '답안 검증' };
  if (edge.id.startsWith('route-')) return { tone: 'branch', label: '질문 종류 분기' };
  if (edge.id.endsWith('-retrieve') || edge.id === 'query-grounding') return { tone: 'retrieval', label: '검색 근거 전달' };
  return { tone: 'process', label: edge.id === 'conditional-gate' ? '근거 충족 · 생성' : '기본 처리 흐름' };
}

const CLEARANCE = 6;
const EPSILON = .01;
const finitePoint = (point: FlowPoint | undefined): point is FlowPoint => Boolean(point && Number.isFinite(point.x) && Number.isFinite(point.y));
const round = (value: number) => Math.round(value * 10) / 10;
const samePoint = (a: FlowPoint, b: FlowPoint) => Math.abs(a.x - b.x) < EPSILON && Math.abs(a.y - b.y) < EPSILON;
const clamp = (value: number, start: number, end: number) => Math.min(end, Math.max(start, value));

function rectangle(point: FlowPoint): FlowRect | null {
  const { left, right, top, bottom } = point;
  if (left === undefined || right === undefined || top === undefined || bottom === undefined || ![left, right, top, bottom].every(Number.isFinite) || right <= left || bottom <= top) return null;
  return { left, right, top, bottom };
}

function port(point: FlowPoint, side: PortSide): FlowPoint {
  const rect = rectangle(point);
  if (!rect) return { x: point.x, y: point.y };
  // Stage x/y is its art lane; labels and I/O occupy the rest of the full card.
  const x = clamp(point.x, rect.left, rect.right), y = clamp(point.y, rect.top, rect.bottom);
  if (side === 'top' || side === 'bottom') return { x, y: rect[side] };
  return { x: rect[side], y };
}

function outsidePort(point: FlowPoint, side: PortSide, distance: number): FlowPoint {
  if (side === 'top') return { x: point.x, y: point.y - distance };
  if (side === 'bottom') return { x: point.x, y: point.y + distance };
  if (side === 'left') return { x: point.x - distance, y: point.y };
  return { x: point.x + distance, y: point.y };
}

function clearSegment(a: FlowPoint, b: FlowPoint, obstacles: FlowRect[]): boolean {
  if (samePoint(a, b)) return true;
  if (Math.abs(a.x - b.x) < EPSILON) return !obstacles.some(rect => a.x > rect.left + EPSILON && a.x < rect.right - EPSILON && Math.max(a.y, b.y) > rect.top + EPSILON && Math.min(a.y, b.y) < rect.bottom - EPSILON);
  if (Math.abs(a.y - b.y) < EPSILON) return !obstacles.some(rect => a.y > rect.top + EPSILON && a.y < rect.bottom - EPSILON && Math.max(a.x, b.x) > rect.left + EPSILON && Math.min(a.x, b.x) < rect.right - EPSILON);
  return false;
}

function simplify(points: FlowPoint[]): FlowPoint[] {
  const result: FlowPoint[] = [];
  for (const point of points) {
    if (result.length && samePoint(result[result.length - 1], point)) continue;
    const a = result[result.length - 2], b = result[result.length - 1];
    if (a && b && ((Math.abs(a.x - b.x) < EPSILON && Math.abs(b.x - point.x) < EPSILON) || (Math.abs(a.y - b.y) < EPSILON && Math.abs(b.y - point.y) < EPSILON))) result.pop();
    result.push({ x: round(point.x), y: round(point.y) });
  }
  return result;
}

function pathScore(points: FlowPoint[]): number {
  return points.slice(1).reduce((score, point, index) => score + Math.abs(point.x - points[index].x) + Math.abs(point.y - points[index].y), 0) + Math.max(0, points.length - 2) * 18;
}

function clearPath(points: FlowPoint[], obstacles: FlowRect[]): boolean {
  return points.slice(1).every((point, index) => clearSegment(points[index], point, obstacles));
}

// Most rails are straight or have one elbow in a reserved inter-row gap.
function simpleRoute(start: FlowPoint, end: FlowPoint, obstacles: FlowRect[], width: number, lane?: number): FlowPoint[] | null {
  const routes: FlowPoint[][] = [
    [start, end],
    [start, { x: start.x, y: end.y }, end],
    [start, { x: end.x, y: start.y }, end],
  ];
  const xs = [start.x, end.x, 12, width - 12, ...(lane === undefined ? [] : [lane]), ...obstacles.flatMap(rect => [rect.left - CLEARANCE, rect.right + CLEARANCE])];
  const ys = [(start.y + end.y) / 2, start.y, end.y, ...obstacles.flatMap(rect => [rect.top - CLEARANCE, rect.bottom + CLEARANCE])];
  for (const x of xs) if (x >= 0 && x <= width) routes.push([start, { x, y: start.y }, { x, y: end.y }, end]);
  for (const y of ys) if (y >= Math.min(start.y, end.y) - CLEARANCE && y <= Math.max(start.y, end.y) + CLEARANCE) routes.push([start, { x: start.x, y }, { x: end.x, y }, end]);
  const valid = routes.map(simplify).filter(route => clearPath(route, obstacles));
  valid.sort((a, b) => pathScore(a) - pathScore(b));
  return valid[0] ?? null;
}

type HeapItem = { state: number; cost: number; estimate: number };
class RouteHeap {
  private items: HeapItem[] = [];
  push(item: HeapItem) {
    let index = this.items.length;
    this.items.push(item);
    while (index > 0) {
      const parent = (index - 1) >> 1;
      if (this.items[parent].estimate <= item.estimate) break;
      this.items[index] = this.items[parent]; index = parent;
    }
    this.items[index] = item;
  }
  pop(): HeapItem | undefined {
    const first = this.items[0], last = this.items.pop();
    if (!first || !last || !this.items.length) return first;
    let index = 0;
    while (index * 2 + 1 < this.items.length) {
      let next = index * 2 + 1;
      if (next + 1 < this.items.length && this.items[next + 1].estimate < this.items[next].estimate) next++;
      if (this.items[next].estimate >= last.estimate) break;
      this.items[index] = this.items[next]; index = next;
    }
    this.items[index] = last;
    return first;
  }
}

// A small visibility grid handles wrapped route choices and text blockers on phones.
// It only adds a detour when the shorter rail would actually intersect a rectangle.
function gridRoute(start: FlowPoint, end: FlowPoint, obstacles: FlowRect[], width: number): FlowPoint[] | null {
  const unique = (values: number[]) => [...new Set(values.map(round))].sort((a, b) => a - b);
  const xs = unique([start.x, end.x, 0, 1, width - 1, width, ...obstacles.flatMap(rect => [rect.left - CLEARANCE, rect.right + CLEARANCE])].filter(x => x >= 0 && x <= width));
  const firstY = Math.min(start.y, end.y), lastY = Math.max(start.y, end.y);
  const crossingRows = obstacles.filter(rect => rect.bottom >= firstY && rect.top <= lastY);
  const searchTop = Math.max(0, Math.min(firstY, ...crossingRows.map(rect => rect.top)) - CLEARANCE);
  const searchBottom = Math.max(lastY, ...crossingRows.map(rect => rect.bottom)) + CLEARANCE;
  const ys = unique([start.y, end.y, ...obstacles.flatMap(rect => [rect.top - CLEARANCE, rect.bottom + CLEARANCE])].filter(y => y >= searchTop && y <= searchBottom));
  const startX = xs.indexOf(round(start.x)), startY = ys.indexOf(round(start.y)), endX = xs.indexOf(round(end.x)), endY = ys.indexOf(round(end.y));
  if ([startX, startY, endX, endY].some(index => index < 0)) return null;
  const columns = xs.length, total = columns * ys.length * 3, costs = new Float64Array(total).fill(Infinity), previous = new Int32Array(total).fill(-1), heap = new RouteHeap();
  const initial = (startY * columns + startX) * 3;
  costs[initial] = 0; heap.push({ state: initial, cost: 0, estimate: 0 });
  let finish = -1;
  for (let item = heap.pop(); item; item = heap.pop()) {
    if (item.cost > costs[item.state] + EPSILON) continue;
    const direction = item.state % 3, cell = Math.floor(item.state / 3), xIndex = cell % columns, yIndex = Math.floor(cell / columns);
    if (xIndex === endX && yIndex === endY) { finish = item.state; break; }
    const here = { x: xs[xIndex], y: ys[yIndex] };
    for (const [dx, dy, nextDirection] of [[-1, 0, 1], [1, 0, 1], [0, -1, 2], [0, 1, 2]]) {
      const nextX = xIndex + dx, nextY = yIndex + dy;
      if (nextX < 0 || nextX >= columns || nextY < 0 || nextY >= ys.length) continue;
      const there = { x: xs[nextX], y: ys[nextY] };
      if (!clearSegment(here, there, obstacles)) continue;
      const state = (nextY * columns + nextX) * 3 + nextDirection;
      const cost = item.cost + Math.abs(here.x - there.x) + Math.abs(here.y - there.y) + (direction && direction !== nextDirection ? 18 : 0);
      if (cost + EPSILON >= costs[state]) continue;
      costs[state] = cost; previous[state] = item.state;
      heap.push({ state, cost, estimate: cost + Math.abs(there.x - end.x) + Math.abs(there.y - end.y) });
    }
  }
  if (finish < 0) return null;
  const route: FlowPoint[] = [];
  for (let state = finish; state >= 0; state = previous[state]) { const cell = Math.floor(state / 3); route.push({ x: xs[cell % columns], y: ys[Math.floor(cell / columns)] }); }
  return simplify(route.reverse());
}

function routeBetween(start: FlowPoint, end: FlowPoint, obstacles: FlowRect[], width: number): FlowPoint[] | null {
  return simpleRoute(start, end, obstacles, width) ?? gridRoute(start, end, obstacles, width);
}

function laneRoute(start: FlowPoint, end: FlowPoint, obstacles: FlowRect[], width: number, lane: number): FlowPoint[] | null {
  const first = { x: lane, y: start.y }, last = { x: lane, y: end.y };
  const enter = routeBetween(start, first, obstacles, width), rail = routeBetween(first, last, obstacles, width), leave = routeBetween(last, end, obstacles, width);
  return enter && rail && leave ? simplify([...enter, ...rail, ...leave]) : null;
}

export function edgeGeometry(edge: ProcessEdge, points: Record<string, FlowPoint>, width: number): EdgeGeometry {
  const a = points[edge.from], b = points[edge.to];
  if (!finitePoint(a) || !finitePoint(b)) return { path: '', points: [], ports: null };
  const allPoints = Object.values(points).filter(finitePoint);
  const bounds = allPoints.map(rectangle).filter((rect): rect is FlowRect => Boolean(rect));
  const safeWidth = Number.isFinite(width) && width > 0 ? width : Math.max(a.x, b.x, ...bounds.map(rect => rect.right), 1) + CLEARANCE;
  const rightLane = (inset: number) => Math.max(1, safeWidth - inset);
  let lane: number | undefined;
  let portPairs: [PortSide, PortSide][];
  if (edge.kind === 'reference') { lane = rightLane(12); portPairs = [['right', 'right'], ['bottom', 'right'], ['bottom', 'top'], ['top', 'right']]; }
  else if (edge.kind === 'retry') { lane = rightLane(26); portPairs = [['right', 'right']]; }
  else if (edge.id === 'meta-gate-bypass') { lane = Math.min(12, safeWidth / 2); portPairs = [['left', 'top'], ['left', 'left'], ['bottom', 'top']]; }
  else if (edge.id === 'weak-reject' || edge.id === 'reject-output') { lane = rightLane(42); portPairs = [['right', 'right'], ['bottom', 'right'], ['bottom', 'top']]; }
  else {
    const ar = rectangle(a), br = rectangle(b);
    if (ar && br && ar.bottom <= br.top + EPSILON) portPairs = [['bottom', 'top']];
    else if (ar && br && ar.right <= br.left + EPSILON) portPairs = [['right', 'left'], ['bottom', 'top']];
    else if (ar && br && br.right <= ar.left + EPSILON) portPairs = [['left', 'right'], ['bottom', 'top']];
    else if (a.y <= b.y) portPairs = [['bottom', 'top'], ['right', 'left'], ['left', 'right']];
    else portPairs = [['top', 'bottom'], ['left', 'left'], ['right', 'right']];
  }
  let best: { route: FlowPoint[]; pair: [PortSide, PortSide]; score: number } | null = null;
  portPairs.forEach((pair, index) => {
    const start = port(a, pair[0]), end = port(b, pair[1]);
    const gap = pair[0] === 'bottom' && pair[1] === 'top' ? end.y - start.y : pair[0] === 'right' && pair[1] === 'left' ? end.x - start.x : CLEARANCE * 3;
    const distance = gap > 0 ? Math.min(CLEARANCE, gap / 3) : CLEARANCE;
    const first = rectangle(a) ? outsidePort(start, pair[0], distance) : start;
    const last = rectangle(b) ? outsidePort(end, pair[1], distance) : end;
    const middle = lane === undefined ? routeBetween(first, last, bounds, safeWidth) : laneRoute(first, last, bounds, safeWidth, lane);
    const route = middle ? simplify([start, ...middle, end]) : null;
    if (!route || !clearPath(route, bounds)) return;
    const score = pathScore(route) + index * 24;
    if (!best || score < best.score) best = { route, pair, score };
  });
  if (!best) return { path: '', points: [], ports: null };
  const chosen = best as { route: FlowPoint[]; pair: [PortSide, PortSide]; score: number };
  const path = chosen.route.map((point, index) => `${index ? 'L' : 'M'}${point.x},${point.y}`).join(' ');
  return { path, points: chosen.route, ports: { from: chosen.pair[0], to: chosen.pair[1] } };
}

export function edgePath(edge: ProcessEdge, points: Record<string, FlowPoint>, width: number): string {
  return edgeGeometry(edge, points, width).path;
}

export function flowPath(sequence: string[], edges: ProcessEdge[], points: Record<string, FlowPoint>, width: number): string {
  return sequence.slice(1).map((id, index) => {
    const edge = edges.find(item => item.from === sequence[index] && item.to === id && item.kind !== 'inactive');
    return edge ? edgePath(edge, points, width) : '';
  }).join(' ');
}
