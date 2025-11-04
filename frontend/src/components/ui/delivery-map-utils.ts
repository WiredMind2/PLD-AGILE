import L from "leaflet";

export const createCircularIcon = (
  backgroundColor: string,
  icon: string,
  textColor: string = "white",
  size: number = 40,
  isHighlighted: boolean = false
): L.DivIcon => {
  // Add highlight effects when highlighted
  const highlightStyles = isHighlighted
    ? `
    border: 4px solid #fbbf24 !important;
    box-shadow: 0 0 20px rgba(251, 191, 36, 0.8), 0 4px 8px rgba(0,0,0,0.3) !important;
    animation: pulse-highlight 2s infinite;
  `
    : "";

  return L.divIcon({
    html: `
      <div style="
        background-color: ${backgroundColor};
        width: ${size}px;
        height: ${size}px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: ${Math.floor(size * 0.45)}px;
        color: ${textColor};
        font-weight: bold;
        ${highlightStyles}
      ">
        ${icon}
      </div>
      ${
        isHighlighted
          ? `
        <style>
          @keyframes pulse-highlight {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
          }
        </style>
      `
          : ""
      }
    `,
    className: "custom-circular-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
};

export const getIcon = (
  type: "pickup" | "delivery" | "courier" | "default" | "unreachable",
  isHighlighted: boolean = false
): L.DivIcon => {
  const iconConfigs = {
    pickup: { color: "#ef4444", icon: "📦", size: 40 },
    delivery: { color: "#3b82f6", icon: "🏢", size: 40 },
    courier: { color: "#22c55e", icon: "🚴", size: 40 },
    default: { color: "#ff7b00ff", icon: "●", size: 15 },
    unreachable: { color: "#dc2626", icon: "❌", size: 35 },
  };

  const config = iconConfigs[type];
  return createCircularIcon(
    config.color,
    config.icon,
    "white",
    config.size,
    isHighlighted
  );
};

// Helper: midpoint between two lat/lngs
export const midpoint = (
  a: [number, number],
  b: [number, number]
): [number, number] => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

// create a circular number icon for segments
export const createNumberIcon = (text: string, size = 26): L.DivIcon => {
  return L.divIcon({
    html:
      `
        <div style="
          background: rgba(16,185,129,0.95);
          color: white;
          width: ${size}px;
          height: ${size}px;
          border-radius: 50%;
          display:flex;
          align-items:center;
          justify-content:center;
          font-size: ${Math.floor(size * 0.5)}px;
          font-weight: 700;
          border: 2px solid white;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        ">` +
      text +
      `</div>
      `,
    className: "segment-number-marker",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
};

// Calculate labeled positions for route segments
export const calculateLabeledPositions = (
  routes: { id: string; positions: [number, number][] }[]
): { pos: [number, number]; index: number; key: string }[] => {
  const labeledPositions: {
    pos: [number, number];
    index: number;
    key: string;
  }[] = [];

  if (!routes || routes.length === 0) return labeledPositions;

  type Seg = {
    mid: [number, number];
    dir: [number, number];
    index: number;
    key: string;
  };
  const allSegments: Seg[] = [];

  for (const r of routes) {
    for (let idx = 0; idx < Math.max(0, r.positions.length - 1); idx++) {
      const start = r.positions[idx];
      const end = r.positions[idx + 1];
      const mid = midpoint(start, end);
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      // canonicalize direction so same physical segment has the same canonical direction
      // compare tuples to pick a canonical ordering independent of traversal direction
      const forward =
        start[0] < end[0] || (start[0] === end[0] && start[1] <= end[1]);
      const cdx = forward ? dx : -dx;
      const cdy = forward ? dy : -dy;
      const clen = Math.sqrt(cdx * cdx + cdy * cdy) || 1e-9;
      const canonDir: [number, number] = [cdx / clen, cdy / clen];
      allSegments.push({
        mid,
        dir: canonDir,
        index: idx + 1,
        key: `${r.id}-seg-${idx}`,
      });
    }
  }

  // cluster midpoints by proximity (meters)
  const groups: Seg[][] = [];
  const tolMeters = 4; // midpoints closer than this are considered overlapping
  const metersBetween = (a: [number, number], b: [number, number]) => {
    const latAvg = (a[0] + b[0]) / 2;
    const mx = (a[0] - b[0]) * 111320;
    const my = (a[1] - b[1]) * 111320 * Math.cos((latAvg * Math.PI) / 180);
    return Math.sqrt(mx * mx + my * my);
  };

  for (const s of allSegments) {
    let placed = false;
    for (const g of groups) {
      if (metersBetween(g[0].mid, s.mid) <= tolMeters) {
        g.push(s);
        placed = true;
        break;
      }
    }
    if (!placed) groups.push([s]);
  }

  const spacingMeters = 10;
  for (const g of groups) {
    if (g.length === 1) {
      labeledPositions.push({
        pos: g[0].mid,
        index: g[0].index,
        key: g[0].key,
      });
      continue;
    }
    const m = g.length;
    for (let i = 0; i < m; i++) {
      const s = g[i];
      const offsetMeters = (i - (m - 1) / 2) * spacingMeters;
      const lat = s.mid[0];
      const mperdegLat = 111320;
      const mperdegLng = 111320 * Math.cos((lat * Math.PI) / 180);
      const dLatPerMeter = 1 / mperdegLat;
      const dLngPerMeter = 1 / (mperdegLng || mperdegLat);
      // offset along the perpendicular to the canonical direction so opposite traversals don't cancel
      const normal: [number, number] = [-s.dir[1], s.dir[0]];
      const deltaLat = normal[0] * offsetMeters * dLatPerMeter;
      const deltaLng = normal[1] * offsetMeters * dLngPerMeter;
      labeledPositions.push({
        pos: [s.mid[0] + deltaLat, s.mid[1] + deltaLng],
        index: s.index,
        key: s.key + `-o${i}`,
      });
    }
  }

  return labeledPositions;
};