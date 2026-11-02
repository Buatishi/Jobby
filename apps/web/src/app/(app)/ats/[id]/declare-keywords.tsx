import { KeywordName } from "./keyword-name";

export type MissingKeyword = {
  keyword: string;
  priority?: "required" | "nice";
};

/** El cuerpo del pedido de optimizar: solo viajan palabras que el reporte da por faltantes. */
export function optimizeRequestBody(
  jobId: string,
  selected: string[],
  missing: MissingKeyword[]
) {
  const allowed = new Set(missing.map((item) => item.keyword));
  return {
    job_id: jobId,
    confirmed_keywords: selected.filter((keyword) => allowed.has(keyword))
  };
}

/**
 * Qué falta para que el puntaje suba y por qué no se agregó: ni el CV ni el LinkedIn
 * muestran que la persona las sepa. Puede confirmar las que sí sabe; el optimizador
 * las escribe en las habilidades y el puntaje las cuenta.
 */
export function DeclareKeywords({
  missing,
  selected,
  onToggle,
  disabled = false
}: {
  missing: MissingKeyword[];
  selected: string[];
  onToggle: (keyword: string) => void;
  disabled?: boolean;
}) {
  if (missing.length === 0) {
    return null;
  }

  return (
    <div className="mb-5 rounded-2xl border border-border p-4">
      <h3 className="font-medium">Qué falta para que el puntaje suba</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        Estas palabras del puesto no figuran en tu CV ni en tu LinkedIn, así que
        no las escribimos: no hay con qué saber que las conocés. Si de verdad las
        sabés, marcalas y las sumamos a tus habilidades; el puntaje las cuenta.
      </p>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
        {missing.map((item) => (
          <li key={item.keyword}>
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                checked={selected.includes(item.keyword)}
                className="h-4 w-4 accent-brand-bright"
                disabled={disabled}
                onChange={() => onToggle(item.keyword)}
                type="checkbox"
              />
              <span>
                <KeywordName keyword={item.keyword} priority={item.priority} />
              </span>
            </label>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted-foreground">
        Marcá solo las que podés defender en una entrevista. Van a tu lista de
        habilidades, nunca como experiencia. Cada optimización cuenta en tu cupo
        del mes.
      </p>
    </div>
  );
}
