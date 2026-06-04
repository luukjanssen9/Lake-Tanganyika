import type { ReactNode } from "react";
import { X } from "lucide-react";

type ChartModalProps = {
  title: string;
  children: ReactNode;
  controls?: ReactNode;
  onClose: () => void;
};

export default function ChartModal({ title, children, controls, onClose }: ChartModalProps) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="modal-panel" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-panel__top">
          <h2>{title}</h2>
          <button className="icon-button" type="button" onClick={onClose} title="Close" aria-label="Close">
            <X size={20} />
          </button>
        </div>
        {controls ? <div className="control-row modal-controls">{controls}</div> : null}
        <div className="modal-panel__body">{children}</div>
      </section>
    </div>
  );
}
