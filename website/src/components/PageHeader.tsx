import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: ReactNode;
  subtitle?: string;
  className?: string;
};

export default function PageHeader({ eyebrow, title, subtitle, className }: PageHeaderProps) {
  return (
    <section className={["page-header", className].filter(Boolean).join(" ")}>
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h1>{title}</h1>
      {subtitle ? <p>{subtitle}</p> : null}
    </section>
  );
}
