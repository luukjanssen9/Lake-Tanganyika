import type { LucideIcon } from "lucide-react";

type StatCardProps = {
  label: string;
  value: string;
  detail?: string;
  icon?: LucideIcon;
};

export default function StatCard({ label, value, detail, icon: Icon }: StatCardProps) {
  return (
    <article className="stat-card">
      <div>
        <p className="stat-card__label">{label}</p>
        <strong>{value}</strong>
      </div>
      {Icon ? (
        <span className="stat-card__icon" aria-hidden="true">
          <Icon size={22} />
        </span>
      ) : null}
      {detail ? <p className="stat-card__detail">{detail}</p> : null}
    </article>
  );
}
