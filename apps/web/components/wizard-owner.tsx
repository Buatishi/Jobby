"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { resolveWizardOwner } from "@/lib/wizard/owner";

const WizardOwnerContext = createContext<string | null>(null);

/**
 * Espera a saber qué cuenta usa el wizard y se la da a los pasos: el avance que se guarda
 * en el navegador lleva su id. Si no se pudo saber (`null`), los pasos funcionan igual
 * pero sin guardar ni leer avance local.
 */
export function WizardOwnerProvider({ children }: { children: ReactNode }) {
  const [owner, setOwner] = useState<{ id: string | null } | null>(null);

  useEffect(() => {
    let active = true;
    void resolveWizardOwner().then((id) => {
      if (active) {
        setOwner({ id });
      }
    });
    return () => {
      active = false;
    };
  }, []);

  if (owner === null) {
    return <p className="text-sm text-muted-foreground">Cargando tu cuenta...</p>;
  }

  return (
    <WizardOwnerContext.Provider value={owner.id}>{children}</WizardOwnerContext.Provider>
  );
}

/** La cuenta dueña del avance del wizard (`null` si no se pudo saber). */
export function useWizardOwner(): string | null {
  return useContext(WizardOwnerContext);
}
