"use client";

import { ArrowBigUp, Eye, EyeOff } from "lucide-react";
import {
  type ComponentPropsWithoutRef,
  type KeyboardEvent,
  type MouseEvent,
  useState
} from "react";

import { isCapsLockOn } from "@/lib/auth/caps-lock";
import { useI18n } from "@/lib/i18n/provider";
import { cn } from "@/lib/utils";

type PasswordInputProps = Omit<ComponentPropsWithoutRef<"input">, "type">;

/** Campo de contraseña con el ojo para mostrarla y un aviso de Bloq Mayús activado. */
export function PasswordInput({
  className,
  disabled,
  id,
  onBlur,
  onKeyDown,
  onKeyUp,
  onMouseDown,
  ...props
}: PasswordInputProps) {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const hintId = id ? `${id}-caps-lock` : undefined;

  function trackCapsLock(
    event: KeyboardEvent<HTMLInputElement> | MouseEvent<HTMLInputElement>
  ) {
    setCapsLock(isCapsLockOn(event));
  }

  return (
    <div>
      <div className="relative">
        <input
          {...props}
          aria-describedby={capsLock ? hintId : undefined}
          className={cn(className, "pr-11")}
          disabled={disabled}
          id={id}
          onBlur={(event) => {
            setCapsLock(false);
            onBlur?.(event);
          }}
          onKeyDown={(event) => {
            trackCapsLock(event);
            onKeyDown?.(event);
          }}
          onKeyUp={(event) => {
            trackCapsLock(event);
            onKeyUp?.(event);
          }}
          onMouseDown={(event) => {
            trackCapsLock(event);
            onMouseDown?.(event);
          }}
          type={visible ? "text" : "password"}
        />
        <button
          aria-controls={id}
          aria-label={visible ? t("auth.hidePassword") : t("auth.showPassword")}
          aria-pressed={visible}
          className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-xl text-black/45 transition-colors hover:text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0F6E56]/25 disabled:pointer-events-none disabled:opacity-50"
          disabled={disabled}
          onClick={() => setVisible((current) => !current)}
          type="button"
        >
          {visible ? (
            <EyeOff aria-hidden className="h-4 w-4" />
          ) : (
            <Eye aria-hidden className="h-4 w-4" />
          )}
        </button>
      </div>
      {capsLock ? (
        <p
          className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-amber-700"
          id={hintId}
          role="status"
        >
          <ArrowBigUp aria-hidden className="h-3.5 w-3.5" />
          {t("auth.capsLockOn")}
        </p>
      ) : null}
    </div>
  );
}
