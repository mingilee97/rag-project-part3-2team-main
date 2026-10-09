export type QueryRoute = 'meta' | 'single' | 'compare' | 'search';
export type FlowKind = 'prepare' | 'query' | 'evaluate';
export type FlowPoint = { x: number; y: number };
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

export function edgePath(edge: ProcessEdge, points: Record<string, FlowPoint>, width: number): string {
  const a = points[edge.from], b = points[edge.to];
  if (!a || !b) return '';
  if (edge.kind === 'reference') {
    const lane = Math.max(a.x, b.x, width - 14);
    return `M${a.x},${a.y} C${lane},${a.y} ${lane},${b.y} ${b.x},${b.y}`;
  }
  if (edge.kind === 'retry') {
    const floor = Math.max(a.y, b.y) + 44;
    return `M${a.x},${a.y} C${a.x},${floor} ${b.x},${floor} ${b.x},${b.y}`;
  }
  if (edge.kind === 'bypass' && Math.abs(a.y - b.y) > 90) {
    const lane = 13;
    return `M${a.x},${a.y} C${lane},${a.y} ${lane},${b.y} ${b.x},${b.y}`;
  }
  if (Math.abs(a.y - b.y) < 55) return `M${a.x},${a.y} C${(a.x + b.x) / 2},${a.y} ${(a.x + b.x) / 2},${b.y} ${b.x},${b.y}`;
  return `M${a.x},${a.y} C${a.x},${(a.y + b.y) / 2} ${b.x},${(a.y + b.y) / 2} ${b.x},${b.y}`;
}

export function flowPath(sequence: string[], edges: ProcessEdge[], points: Record<string, FlowPoint>, width: number): string {
  return sequence.slice(1).map((id, index) => {
    const edge = edges.find(item => item.from === sequence[index] && item.to === id && item.kind !== 'inactive');
    return edge ? edgePath(edge, points, width) : '';
  }).join(' ');
}
