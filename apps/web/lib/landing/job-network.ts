export type NetworkNode = {
  id: string;
  label: string;
  score: number;
  x: number;
  y: number;
};

export const NETWORK_VIEWBOX = { width: 960, height: 380 } as const;
export const NETWORK_CENTER = { x: 480, y: 318 } as const;
export const NODE_RING_RADIUS = 30;

// Puestos y puntajes de ejemplo: la landing los rotula como datos de muestra.
export const networkNodes: NetworkNode[] = [
  { id: "backend", label: "Backend Developer", score: 86, x: 110, y: 236 },
  { id: "fullstack", label: "Full Stack Developer", score: 78, x: 285, y: 112 },
  { id: "product", label: "Product Analyst", score: 71, x: 480, y: 72 },
  { id: "data", label: "Data Engineer", score: 54, x: 675, y: 112 },
  { id: "devops", label: "DevOps Engineer", score: 38, x: 850, y: 236 }
];

// Arco curvo que sale del CV y llega a cada puesto.
export function arcPath(node: NetworkNode): string {
  const midX = (NETWORK_CENTER.x + node.x) / 2;
  const midY = Math.min(NETWORK_CENTER.y, node.y) - 70;

  return `M${NETWORK_CENTER.x} ${NETWORK_CENTER.y - 38} Q${midX} ${midY} ${node.x} ${node.y + 38}`;
}

export function ringDash(score: number, radius: number = NODE_RING_RADIUS): string {
  const circumference = 2 * Math.PI * radius;
  const length = (circumference * Math.max(0, Math.min(100, score))) / 100;

  return `${length.toFixed(1)} ${circumference.toFixed(1)}`;
}
