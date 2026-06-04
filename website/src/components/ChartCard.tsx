import type { ReactNode } from "react";
import { Maximize2 } from "lucide-react";

type ChartCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  controls?: ReactNode;
  onOpen?: () => void;
};

export default function ChartCard({ title, subtitle, children, controls, onOpen }: ChartCardProps) {
  return (
    <article className="chart-card">
      <div className="chart-card__top">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {onOpen ? (
          <button className="icon-button" type="button" onClick={onOpen} title="Open large chart" aria-label="Open large chart">
            <Maximize2 size={18} />
          </button>
        ) : null}
      </div>
      {controls ? <div className="control-row">{controls}</div> : null}
      <button className="chart-card__body" type="button" onClick={onOpen} aria-label={`Open ${title}`}>
        {children}
      </button>
    </article>
  );
}
