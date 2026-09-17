import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, WheelEvent } from "react";
import { useI18n } from "../i18n";
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
  const { locale } = useI18n();
  const [layer, setLayer] = useState<"overlay" | "original" | "compare">("overlay");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ pointerId: number; x: number; y: number; panX: number; panY: number } | null>(null);
  const item = index === null ? null : items[index] ?? null;

  useEffect(() => {
    if (item) {
      setLayer(item.overlay_url ? "overlay" : "original");
      setZoom(1);
      setPan({ x: 0, y: 0 });
    }
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
  const transform = `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`;

  function changeZoom(next: number) {
    const bounded = Math.min(5, Math.max(1, next));
    setZoom(bounded);
    if (bounded === 1) setPan({ x: 0, y: 0 });
  }

  function resetView() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function onWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    changeZoom(zoom + (event.deltaY < 0 ? 0.25 : -0.25));
  }

  function onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (zoom === 1) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      panX: pan.x,
      panY: pan.y,
    };
  }

  function onPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    setPan({
      x: drag.current.panX + event.clientX - drag.current.x,
      y: drag.current.panY + event.clientY - drag.current.y,
    });
  }

  function onPointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    if (drag.current?.pointerId === event.pointerId) drag.current = null;
  }

  return (
    <Modal open={item !== null} title={item?.title ?? ""} onClose={onClose} wide>
      {item && (
        <div className="lightbox">
          <div className="lightbox-toolbar">
            {item.overlay_url && item.original_url && (
              <div className="segmented" role="group" aria-label={locale === "fr" ? "Couche affichée" : "Displayed layer"}>
                <button type="button" className={layer === "original" ? "active" : ""} onClick={() => setLayer("original")}>{locale === "fr" ? "Source (aperçu)" : "Source (preview)"}</button>
                <button type="button" className={layer === "overlay" ? "active" : ""} onClick={() => setLayer("overlay")}>Segmentation</button>
                <button type="button" className={layer === "compare" ? "active" : ""} onClick={() => setLayer("compare")}>{locale === "fr" ? "Côte à côte" : "Side by side"}</button>
              </div>
            )}
            <div className="zoom-controls" role="group" aria-label={locale === "fr" ? "Zoom de l’image" : "Image zoom"}>
              <button type="button" className="icon-button" onClick={() => changeZoom(zoom - 0.25)} disabled={zoom <= 1} aria-label={locale === "fr" ? "Réduire le zoom" : "Zoom out"}>−</button>
              <output aria-live="polite">{Math.round(zoom * 100)} %</output>
              <button type="button" className="icon-button" onClick={() => changeZoom(zoom + 0.25)} disabled={zoom >= 5} aria-label={locale === "fr" ? "Augmenter le zoom" : "Zoom in"}>+</button>
              <button type="button" className="text-button" onClick={resetView} disabled={zoom === 1 && pan.x === 0 && pan.y === 0}>{locale === "fr" ? "Réinitialiser" : "Reset"}</button>
            </div>
            <div className="lightbox-nav">
              <button type="button" className="secondary-button" disabled={index === 0} onClick={() => onNavigate((index ?? 0) - 1)}>← {locale === "fr" ? "Précédente" : "Previous"}</button>
              <span className="muted">{(index ?? 0) + 1} / {items.length}</span>
              <button type="button" className="secondary-button" disabled={index === items.length - 1} onClick={() => onNavigate((index ?? 0) + 1)}>{locale === "fr" ? "Suivante" : "Next"} →</button>
            </div>
          </div>
          <div
            className={`lightbox-stage ${zoom > 1 ? "zoomed" : ""} ${layer === "compare" ? "comparing" : ""}`}
            onWheel={onWheel}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
          >
            {layer === "compare" && item.original_url && item.overlay_url ? (
              <div className="lightbox-compare">
                <figure>
                  <div className="lightbox-image-frame"><img draggable={false} style={{ transform }} src={item.original_url} alt={`${item.title} · ${locale === "fr" ? "aperçu source" : "source preview"}`} /></div>
                  <figcaption>{locale === "fr" ? "Source (aperçu)" : "Source (preview)"}</figcaption>
                </figure>
                <figure>
                  <div className="lightbox-image-frame"><img draggable={false} style={{ transform }} src={item.overlay_url} alt={`${item.title} · segmentation`} /></div>
                  <figcaption>Segmentation</figcaption>
                </figure>
              </div>
            ) : source ? (
              <div className="lightbox-image-frame single"><img draggable={false} style={{ transform }} src={source} alt={`${item.title} · ${layer === "overlay" ? "segmentation" : locale === "fr" ? "aperçu source" : "source preview"}`} /></div>
            ) : (
              <p className="muted">{locale === "fr" ? "Aucune image disponible." : "No image available."}</p>
            )}
          </div>
          <p className="muted lightbox-zoom-note">
            {locale === "fr"
              ? "Molette ou boutons pour zoomer ; faites glisser l’image agrandie. En mode côte à côte, la vue reste synchronisée."
              : "Use the wheel or buttons to zoom; drag the enlarged image. Side-by-side views stay synchronized."}
          </p>
          {item.original_url && (
            <p className="muted lightbox-preview-note">
              {locale === "fr"
                ? "L’aperçu est un PNG 8 bits destiné uniquement à l’affichage. L’analyse utilise le fichier source conservé dans son format d’origine."
                : "The preview is an 8-bit PNG for display only. Analysis uses the source file in its original format."}
            </p>
          )}
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
