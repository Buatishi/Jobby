# Configuración de Claude Code del proyecto

Estado: vigente desde 2026-09-21. Costo: USD 0.

## 1. Para qué sirve

`AGENTS.md` le dice a Claude qué reglas seguir, pero es un consejo: Claude Code lo trata como
contexto, no como cumplimiento forzado. Este paquete hace dos cosas: asegura que esas reglas
lleguen siempre a Claude Code y convierte las tres más críticas en controles automáticos.
No cambia el código de la aplicación ni el despliegue.

| Pieza | Qué hace | Qué evita |
|---|---|---|
| `CLAUDE.md` en la raíz, `apps/web` y `services/api` | Cada uno solo importa el `AGENTS.md` de su carpeta (`@AGENTS.md`) | Que las reglas no se carguen: el 2026-09-21 el comando `/context` mostró que, en la app de escritorio, Claude Code **no** cargaba `AGENTS.md` solo |
| `permissions.deny` | Impide leer `.env`, `.env.local`, `.env.production` (raíz, API y web) y ejecutar el E2E vivo (`E2E_LIVE`). Las plantillas `.env.example` se siguen pudiendo leer | Exponer secretos o registrar y borrar usuarios reales por accidente |
| `permissions.allow` | Permite sin preguntar los controles habituales: typecheck, lint, tests, build, mypy, ruff y `git status`, `diff` y `log` | Decenas de confirmaciones por sesión |
| Hook `protect_paths.py` | **Bloquea** editar archivos `.env`, migraciones ya versionadas e interior de `.git/`. **Pide confirmación** antes de tocar `render.yaml`, `.github/workflows/`, el `Dockerfile` de la API o cualquier archivo de LemonSqueezy o webhooks | Modificar migraciones aplicadas, tocar el despliegue o el cobro sin avisar (`AGENTS.md`, secciones 1 y 2) |
| Skill `/pr-checklist` | Solo se ejecuta si la invocás: corre los controles según lo que cambió y arma el resumen Requisito, Impacto, Riesgo y Prueba | Abrir un PR sin haber verificado, o con un resumen inventado |

Tokens: `AGENTS.md` pesa unos 1.100 tokens y se carga una vez al iniciar la sesión (los de
`apps/web` y `services/api` se cargan solo al trabajar en esas carpetas). El hook corre fuera de
la conversación (0 tokens) y la skill no carga su descripción porque solo se invoca a mano.

## 2. Cómo se prueba

```bash
python -m unittest discover -s .claude/hooks -p "test_*.py" -v
```

8 casos: `.env` bloqueado en todas sus grafías (incluida `./.env` y rutas de Windows), plantillas
`.env.example` permitidas, migraciones versionadas bloqueadas y migraciones nuevas permitidas,
confirmación en archivos de despliegue y cobro, y que un error propio del hook no frene el
trabajo. Tres mutaciones deliberadas fueron detectadas.

Para comprobar que `AGENTS.md` se carga, abrir una sesión nueva y ejecutar `/context`: debe
aparecer `CLAUDE.md` (con `AGENTS.md` incluido) entre los archivos de memoria.

## 3. Reglas de uso

- Las reglas se escriben **solo** en `AGENTS.md`. Los `CLAUDE.md` únicamente lo importan; si se
  agrega texto ahí, las reglas quedan repartidas.
- No correr `/init`: está pensado para crear un `CLAUDE.md` nuevo y podría pisar estos.
- Es una protección para el flujo con Claude Code: no reemplaza la protección de `main`.
- Las reglas `allow` empiezan a valer después de que se confía en la carpeta; las `deny`, de
  inmediato ([configuración](https://code.claude.com/docs/en/settings)).
- Las importaciones de `AGENTS.md` se resuelven respecto del archivo que las escribe y se cargan
  al inicio ([memoria](https://code.claude.com/docs/en/memory)).

## 4. Configuración de usuario (fuera del repositorio)

La atribución de commits y pull requests se controla con `attribution` en el archivo de usuario
`~/.claude/settings.json`, no en el repositorio. Para que Claude Code no agregue líneas de
coautoría se dejan `commit` y `pr` vacíos:

```json
{ "attribution": { "commit": "", "pr": "" } }
```

Esto no reemplaza la declaración del uso de herramientas de IA que exige la consigna (sección 8):
esa declaración va en el documento de decisiones técnicas.

## 5. Cómo desactivarlo

Revertir el pull request, o borrar la carpeta `.claude/` y los tres `CLAUDE.md`.
