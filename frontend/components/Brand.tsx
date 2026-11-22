import type { ProductId } from "@/lib/types";

/** Woven mark: warp and weft strands crossing, the textile behind all three products. */
export function Logo({ size = 34, animated = false }: { size?: number; animated?: boolean }) {
  const strands = [6, 14, 22];
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true" className={animated ? "weave-anim" : undefined}>
      <rect x="0.5" y="0.5" width="27" height="27" rx="7" fill="var(--panel-2)" stroke="var(--line-2)" />
      {strands.map((y, i) => (
        <rect key={`h${y}`} x="4" y={y - 1.5} width="20" height="3" rx="1.5" fill="var(--accent)"
              style={{ animationDelay: `${i * 0.2}s` }} />
      ))}
      {strands.map((x, i) => (
        // vertical strands pass over and under the horizontal ones
        <g key={`v${x}`}>
          {strands.map((y, j) => ((i + j) % 2 === 0 ? (
            <rect key={j} x={x - 1.5} y={y - 3.5} width="3" height="7" rx="1.5" fill="var(--text-2)" />
          ) : null))}
          <rect x={x - 0.75} y="4" width="1.5" height="20" rx="0.75" fill="var(--text-2)" opacity="0.35" />
        </g>
      ))}
    </svg>
  );
}

const SWATCH_TONE: Record<ProductId, string> = {
  raw_sheep_wool: "var(--accent)",
  duck_down: "var(--c-insufficient)",
  cashmere: "var(--c-strong)",
};

/** Small fibre drawings: crimped wool, a down cluster, fine cashmere strands. */
export function FibreIcon({ product, size = 22 }: { product: ProductId; size?: number }) {
  const stroke = SWATCH_TONE[product];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="1.6"
         strokeLinecap="round" aria-hidden="true">
      {product === "raw_sheep_wool" && (
        <>
          <path d="M3 7c2-2 3 2 5 0s3 2 5 0 3 2 5 0 2 1 3 0" />
          <path d="M3 12c2-2 3 2 5 0s3 2 5 0 3 2 5 0 2 1 3 0" />
          <path d="M3 17c2-2 3 2 5 0s3 2 5 0 3 2 5 0 2 1 3 0" />
        </>
      )}
      {product === "duck_down" && (
        <>
          <circle cx="12" cy="12" r="1.6" fill={stroke} />
          {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
            <path key={a} d="M12 12 Q14 8 12 4" transform={`rotate(${a} 12 12)`} />
          ))}
        </>
      )}
      {product === "cashmere" && (
        <>
          <path d="M4 20 C8 14 10 9 20 4" />
          <path d="M4 16 C8 11 11 7 18 3" opacity="0.7" />
          <path d="M7 21 C11 15 14 11 21 7" opacity="0.7" />
          <path d="M4 12 C7 9 9 6 13 3" opacity="0.45" />
        </>
      )}
    </svg>
  );
}

export function FibreSwatch({ product }: { product: ProductId }) {
  return <span className="fibre-swatch" style={{ background: "var(--bg-2)" }}><FibreIcon product={product} /></span>;
}
