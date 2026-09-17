import { useEffect, useState } from "react";
import { Modal } from "./Modal";

export interface LightboxItem {
  title: string;
  original_url: string | null;
  overlay_url: string | null;
  facts: Array<{ label: string; value: string }>;
}

interface LightboxProps {
  items: LightboxItem[];
  index: number | null;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

export function Lightbox({ items, index, onClose, onNavigate }: LightboxProps) {
  const [layer, setLayer] = useState<"overlay" | "original">("overlay");
  const item = index === null ? null : items[index] ?? null;

  useEffect(() => {
    if (item && !item.overlay_url) setLayer("original");
  }, [item]);

  useEffect(() => {
    if (index === null) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "ArrowRight" && index !== null && index < items.length - 1) onNavigate(index + 1);
      if (event.key === "ArrowLeft" && index !== null && index > 0) onNavigate(index - 1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, items.length, onNavigate]);

  const source = item ? (layer === "overlay" ? item.overlay_url ?? item.original_url : item.original_url ?? item.overlay_url) : null;

  return (
    <Modal open={item !== null} title={item?.title ?? ""} onClose={onClose} wide>
      {item && (
        <div className="lightbox">
          <div className="lightbox-toolbar">
            {item.overlay_url && item.original_url && (
              <div className="segmented" role="group" aria-label="Couche affichée">
                <button type="button" className={layer === "original" ? "active" : ""} onClick={() => setLayer("original")}>Original</button>
                <button type="button" className={layer === "overlay" ? "active" : ""} onClick={() => setLayer("overlay")}>Segmentation</button>
              </div>
            )}
            <div className="lightbox-nav">
              <button type="button" className="secondary-button" disabled={index === 0} onClick={() => onNavigate((index ?? 0) - 1)}>← Précédente</button>
              <span className="muted">{(index ?? 0) + 1} / {items.length}</span>
              <button type="button" className="secondary-button" disabled={index === items.length - 1} onClick={() => onNavigate((index ?? 0) + 1)}>Suivante →</button>
            </div>
          </div>
          <div className="lightbox-stage">
            {source ? <img src={source} alt={`${item.title} · ${layer === "overlay" ? "segmentation" : "original"}`} /> : <p className="muted">Aucune image disponible.</p>}
          </div>
          {item.facts.length > 0 && (
            <dl className="kv lightbox-facts">
              {item.facts.map((fact) => (
                <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>
              ))}
            </dl>
          )}
        </div>
      )}
    </Modal>
  );
}
