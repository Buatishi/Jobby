type ModifierEvent = {
  getModifierState?: (key: "CapsLock") => boolean;
};

/**
 * Si el Bloq Mayús está activo según el último evento de teclado o de mouse. El navegador no
 * expone el estado antes del primer evento, por eso se lee al tipear o al hacer clic.
 */
export function isCapsLockOn(event: ModifierEvent): boolean {
  return (
    typeof event.getModifierState === "function" &&
    event.getModifierState("CapsLock") === true
  );
}
