// A self-contained, original decorative field — a diagonal grid of tiles that
// fades in from the left, with a handful of larger "lit" tiles scattered
// through it. Pure SVG, no external assets.
export default function CubeField() {
  const cols = 12;
  const rows = 9;
  const size = 64;
  const lit = new Set(["3-1", "6-4", "9-2", "4-6", "8-6", "10-4", "2-4", "7-1"]);

  const tiles = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const x = c * size + (r % 2 ? size / 2 : 0);
      const y = r * size * 0.86;
      const key = `${c}-${r}`;
      tiles.push(
        <rect
          key={key}
          x={x - 18}
          y={y - 18}
          width="36"
          height="36"
          rx="6"
          transform={`rotate(45 ${x} ${y})`}
          className={lit.has(key) ? "cube-tile lit" : "cube-tile"}
        />
      );
    }
  }

  return (
    <svg
      className="cube-field"
      viewBox={`0 0 ${cols * size} ${rows * size * 0.86}`}
      preserveAspectRatio="xMaxYMid slice"
      aria-hidden="true"
    >
      {tiles}
    </svg>
  );
}
