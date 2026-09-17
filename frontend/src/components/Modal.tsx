import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { useI18n } from "../i18n";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}

export function Modal({ open, title, onClose, children, wide = false }: ModalProps) {
  const { locale } = useI18n();
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      className={`modal ${wide ? "modal-wide" : ""}`}
      ref={dialogRef}
      aria-labelledby="modal-title"
      onClose={onClose}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose();
      }}
    >
      <div className="modal-body">
        <div className="modal-heading">
          <h2 id="modal-title">{title}</h2>
          <button className="icon-button" type="button" onClick={onClose} aria-label={locale === "fr" ? "Fermer" : "Close"}>×</button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
