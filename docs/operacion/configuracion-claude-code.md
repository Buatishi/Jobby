# Configuración de Claude Code del proyecto

Estado: **propuesta** (pull request borrador; se activa recién al integrarlo).

## 1. Para qué sirve

`AGENTS.md` le dice a Claude qué reglas seguir, pero es un consejo: Claude Code lo trata como
contexto, no como cumplimiento forzado. Este paquete convierte tres reglas críticas del
proyecto en controles automáticos y reduce las confirmaciones repetitivas. No cambia el
código de la aplicación ni el despliegue.

| Pieza | Qué hace | Qué evita |
|---|---|---|
| `permissions.deny` | Impide leer `.env`, `.env.local`, `.env.production` (raíz, API y web) y ejecutar el E2E vivo (`E2E_LIVE`). Las plantillas `.env.example` se siguen pudiendo leer | Exponer secretos o registrar y borrar usuarios reales por accidente |
| `permissions.allow` | Permite sin preguntar los controles habituales: typecheck, lint, tests, build, mypy, ruff y `git status`, `diff` y `log` | Decenas de confirmaciones por sesión |
| Hook `protect_paths.py` | **Bloquea** editar archivos `.env`, migraciones ya versionadas e interior de `.git/`. **Pide confirmación** antes de tocar `render.yaml`, `.github/workflows/`, el `Dockerfile` de la API o cualquier archivo de LemonSqueezy o webhooks | Modificar migraciones aplicadas, tocar el despliegue o el cobro sin avisar (`AGENTS.md`, secciones 1 y 2) |
| Skill `/pr-checklist` | Solo se ejecuta si la invocás: corre los controles según lo que cambió y arma el resumen Requisito, Impacto, Riesgo y Prueba | Abrir un PR sin haber verificado, o con un resumen inventado |

Costo: USD 0. Los tokens: el hook corre fuera de la conversación (0 tokens) y la skill no
carga su descripción porque solo se invoca a mano.

## 2. Cómo se prueba

```bash
python -m unittest discover -s .claude/hooks -p "test_*.py" -v
```

8 casos: `.env` bloqueado en todas sus grafías (incluida `./.env` y rutas de Windows), plantillas
`.env.example` permitidas, migraciones versionadas bloqueadas y migraciones nuevas permitidas,
confirmación en archivos de despliegue y cobro, y que un error propio del hook no frene el
trabajo. Tres mutaciones deliberadas fueron detectadas.

## 3. Límites y advertencias

- Es una protección para el flujo con Claude Code: no reemplaza la protección de `main`.
- Las reglas `allow` empiezan a valer después de que se confía en la carpeta; las `deny`, de
  inmediato ([configuración](https://code.claude.com/docs/en/settings)).
- **No crear un `CLAUDE.md` ni correr `/init`**: mientras no exista ningún `CLAUDE.md`,
  Claude Code lee `AGENTS.md` por sí solo; con uno presente lo ignora salvo que lo importe con
  `@AGENTS.md` ([memoria](https://code.claude.com/docs/en/memory)).
- La atribución de commits (`attribution`) no está en este paquete: se configura en el
  archivo de usuario `~/.claude/settings.json`.

## 4. Cómo desactivarlo

Revertir el pull request, o borrar la carpeta `.claude/`.
