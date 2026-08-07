/**
 * Diagram hero for the Algolia relevance article.
 *
 * Carries the argument rather than decorating it: the top band is the layer
 * teams tune, the bottom band is the record it reasons over, and one field in
 * that record is greyed out — the missing brand attribute the article opens
 * with. Stock photography could not say any of that.
 *
 * All box positions are computed from one array with a running x-offset, so
 * boxes can never overlap regardless of label width — the previous version
 * hardcoded the brand box's x position against the other boxes' dynamically
 * computed widths, and it collided as soon as "description" pushed past it.
 *
 * Inline SVG with currentColor and theme tokens so it works in both themes and
 * stays crisp at any width.
 */

const RECORD_FIELDS = [
  { label: "title", width: 110 },
  { label: "price", width: 92 },
  { label: "description", width: 168 },
  { label: "brand", width: 120, missing: true },
];

const GAP = 16;
const RECORD_Y = 190;
const BOX_H = 46;

function layout(fields: typeof RECORD_FIELDS) {
  let x = 0;
  return fields.map((f) => {
    const box = { ...f, x };
    x += f.width + GAP;
    return box;
  });
}

export function ArticleHero() {
  const record = layout(RECORD_FIELDS);
  const totalWidth = record.at(-1)!.x + record.at(-1)!.width;
  const viewWidth = totalWidth + 80; // left/right padding inside the viewBox

  return (
    <figure className="mt-8 mb-2 overflow-hidden rounded-xl border border-border/60 bg-muted/30">
      <svg
        viewBox={`0 0 ${viewWidth} 320`}
        className="h-auto w-full"
        role="img"
        aria-label="Diagram: ranking configuration sits on top of the indexed record. A greyed-out brand field in the record is unreachable by the ranking layer above it."
      >
        {/* ── top band: the layer everyone tunes ───────────────────────── */}
        <text x="40" y="42" className="fill-muted-foreground" fontSize="11" fontWeight="600" letterSpacing="1.4">
          WHERE THE TUNING HAPPENS
        </text>

        <g>
          {[0, 1, 2, 3].map((i) => {
            const w = (totalWidth - GAP * 3) / 4;
            const x = 40 + i * (w + GAP);
            return (
              <g key={i} transform={`translate(${x}, 58)`}>
                <rect width={w} height={BOX_H} rx="8" className="fill-background stroke-border" strokeWidth="1" />
                <line
                  x1={w * 0.18} y1={BOX_H / 2} x2={w * 0.82} y2={BOX_H / 2}
                  className="stroke-border" strokeWidth="3" strokeLinecap="round"
                />
                <circle cx={w * (i === 1 ? 0.32 : i === 2 ? 0.66 : 0.5)} cy={BOX_H / 2} r="6" className="fill-primary" />
              </g>
            );
          })}
        </g>

        {/* ── the gap ──────────────────────────────────────────────────── */}
        <line
          x1="40" y1="140" x2={viewWidth - 40} y2="140"
          className="stroke-border" strokeWidth="1" strokeDasharray="4 5"
        />

        {/* ── bottom band: the record ──────────────────────────────────── */}
        <text x="40" y="176" className="fill-muted-foreground" fontSize="11" fontWeight="600" letterSpacing="1.4">
          WHERE THE ANSWER LIVES
        </text>

        <g transform={`translate(40, ${RECORD_Y})`}>
          {record.map((f) => (
            <g key={f.label} transform={`translate(${f.x}, 0)`}>
              <rect
                width={f.width} height={BOX_H} rx="8"
                className={
                  f.missing
                    ? "fill-muted/40 stroke-muted-foreground/40"
                    : "fill-background stroke-border"
                }
                strokeWidth="1"
                strokeDasharray={f.missing ? "5 4" : undefined}
              />
              <text
                x={f.width / 2}
                y={BOX_H / 2 + 5}
                textAnchor="middle"
                fontSize="14"
                className={f.missing ? "fill-muted-foreground/70" : "fill-foreground"}
              >
                {f.label}
              </text>
            </g>
          ))}
        </g>

        {/* ── the callout, anchored under the missing field ───────────── */}
        <g transform={`translate(${40 + record.at(-1)!.x}, ${RECORD_Y + BOX_H + 30})`}>
          <line x1="4" y1="-20" x2="4" y2="0" className="stroke-muted-foreground/50" strokeWidth="1.5" />
          <text x="0" y="18" fontSize="13" className="fill-muted-foreground">
            in the data.
          </text>
          <text x="0" y="36" fontSize="13" className="fill-muted-foreground">
            not in the index.
          </text>
        </g>
      </svg>
    </figure>
  );
}
