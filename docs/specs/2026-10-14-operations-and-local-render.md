# Operations Ledger & Local Render — Design

- **Date:** 2026-10-14
- **Status:** Foundation built (this branch). Workstreams A–E run in parallel against the contract below.
- **Roadmap:** [DEVELOPMENT_ROADMAP.md](../DEVELOPMENT_ROADMAP.md), Phase 2 ("provenance everywhere") plus the MOPS decision.

## Why

Two owner decisions on 2026-10-14 set the direction:

1. *"Any magical operation takes time."* MOPS (a per-second throughput
   counter driven by hard-coded constants) is retired. The honest unit is a
   real operation with a start, a measured duration and a completion record.
2. RNG draws stay as a divinatory method, but they are always **labeled as
   draws** and never shown as measurements.

The first real operation built for this is **local image rendering**. The
DataForge garden (`~/proj/dataforge/garden/projects/athena-generator`)
already runs Qwen-Image 2.1 Turbo locally through a headless ComfyUI at
`D:\ComfyUI` (156 successful renders; about 147 s per wallpaper-size image,
55 s for a cold 1024² render). Its `local-wallpapers.md` asks vajra-stream
for "a general request format, backend adapters, job progress, artifact
retrieval, and appropriate model capabilities". This spec delivers that,
with Athena-specific canon and taste staying in DataForge.

**ComfyUI stays.** It is the engine behind an adapter, not a dependency of
the domain. It already handles model loading, VRAM, AMD support and a
verified model manifest. Dropping it would mean rebuilding that for no real
gain, and the adapter keeps it replaceable.

## Foundation (done, this branch)

| Piece | Where |
|---|---|
| `operations` table (schema v7) | `core/schema.py` |
| Ledger API: create / start / complete / fail / cancel / update_result / list / summarize / reconcile_interrupted, listeners | `core/operations.py` |
| `GET /api/v1/operations`, `/operations/summary`, `/operations/{id}` | `backend/app/api/v1/endpoints/operations.py` |
| WS push `{"type": "operation_update", "data": Operation}` on every change; stale active ops marked `interrupted` at startup | `backend/app/main.py` lifespan |
| TypeScript types `Operation`, `OperationsSummary`, `Provenance` | `frontend/src/types/operations.ts` |
| Tests | `tests/unit/test_operations_ledger.py` |

Lifecycle: `queued -> running -> success | error | cancelled`, plus
`interrupted` (the process died mid-flight). `elapsed_seconds` is measured
from `started_at`. `provenance` maps field name to
`record | computed | draw | decorative`.

## Render contract (A implements, B consumes)

All paths are under `/api/v1`. A render job **is** an operation (`kind="render"`).

### `POST /render/jobs` → `202 {"operation": Operation}`

```jsonc
{
  "prompt": "string, required, non-empty",
  "preset": "square-1024 | desktop-19-10 | desktop-19-9 | s25",  // or width+height
  "width": 1024, "height": 1024,      // multiples of 32, 256..2560; ignored if preset given
  "seed": 123,                         // optional, 0..2^53-1 (JS-safe, so it round-trips exactly); omitted -> drawn, provenance.seed = "draw"
  "backend": "comfyui-qwen-image-2.1", // default; the only one in v1
  "working_id": "optional folio id to link",
  "purpose": "free | witness | sigil"  // default "free"
}
```

`operation.params` echoes the normalized request, including the actual seed.
On success, `operation.result` is:

```jsonc
{
  "backend_prompt_id": "comfyui prompt id",
  "image_url": "/api/v1/render/jobs/<id>/image",
  "width": 1024, "height": 1024,       // measured from the PNG, not assumed
  "seed": 123,
  "sha256": "hex of the PNG",
  "artifact_path": "generated/renders/2026-10-14/<id>.png"
}
```

While it runs, `result` may hold `{"backend_prompt_id": ..., "queue_position": n}`
via `update_operation_result`.

### Other routes

- `GET /render/jobs/{id}/image` returns the PNG (`404` until success).
- `POST /render/jobs/{id}/cancel`: queued → `cancelled`; running → ComfyUI
  `/interrupt`, then `cancelled`.
- `GET /render/health` returns `{"backend", "reachable": bool, "base_url", "detail", "queue_remaining"}`.
  It never raises when ComfyUI is down.
- `GET /render/presets` returns `[{"id", "width", "height", "export_width", "export_height", "label"}]`.
- Listing renders uses `GET /operations?kind=render`. There is no separate list route.

### Behaviour

- **One job at a time.** The GPU is serial. A single asyncio worker drains
  queued render operations in `created_at` order.
- **Survives restarts.** Render is excluded from `reconcile_interrupted`. At
  startup the worker re-queues `queued` jobs and re-attaches `running` jobs
  through their stored `backend_prompt_id` (`/history/<id>`). A job that can't
  be re-attached is failed with an explicit error.
- **Artifacts:** `generated/renders/YYYY-MM-DD/<op_id>.png` plus a `<op_id>.json`
  sidecar with the exact graph, prompt, seed, sizes and ComfyUI history
  (mirrors the garden sidecar). `generated/` is gitignored.
- **Config:** a single setting, `COMFYUI_BASE_URL` (default
  `http://127.0.0.1:8188`), read through the settings shim per ADR 002.
  Timeout `RENDER_TIMEOUT_SECONDS` (default 1800; cold loads are slow).
- **Graph:** port `build_graph` from the garden's `src/local_render.py`
  (UNETLoader `qwen_image_2.1_turbo_bf16`, CLIPLoader `qwen3vl_8b_bf16`
  type `qwen_image`, VAELoader `qwen_image_2.1_vae_bf16`,
  `TextEncodeQwenImage21`, `QwenImage21Cache`, euler, `ManualSigmas` with the
  8 official sigmas, CFG 1, Lanczos export scaling). Validate the PNG magic
  number and dimensions.
- **No silent failure:** ComfyUI `node_errors`, non-200 responses, timeouts and
  invalid PNGs all end as `error` with the backend's message.

## Workstreams

Each runs in its own git worktree from this branch. Don't edit another
workstream's files. Shared files (`useWebSocketStable.ts`, `App.tsx`,
`api.py`, `.tsc-baseline`) get small, additive hunks only.

| | Workstream | Owns |
|---|---|---|
| **A** | Render engine (backend) | `backend/core/services/render/`, `backend/app/api/v1/endpoints/render.py`, settings additions, render tests |
| **B** | Ledger & Render Studio UI | `frontend/src/stores/operationsStore.ts`, `operation_update` case in `useWebSocketStable.ts`, `routes/Operations` tabs **Ledger** and **Render**, new components + tests |
| **C** | Retire MOPS | `mops_engine.py`, `endpoints/mops.py` and every MOPS consumer (backend and frontend); replace displays with ledger facts |
| **D** | Label the draws | `core/radionics_engine.py`, `modules/radionics_operator.py` GV/potency outputs, `vajra_service.py` rate jitter, `RitualVisualization.tsx` potency display, attunement e-meter labeling |
| **E** | TypeScript debt | `AstrologyPanel.tsx`, `AstrologyExtractionPanel.tsx`; lower `.tsc-baseline` |

### Phase B (after A merges)

- `SigilService.generate_ai_image` and `core/working.py:attach_witness_image`
  submit render jobs linked by `working_id`, instead of base64 blobs.
- `scripts/start_comfyui.bat` currently passes `--api-only`, a flag that
  doesn't exist, so it fails. Replace it with a launcher configured through
  `COMFYUI_LAUNCHER`.
- Delete the stale SD 1.5 `comfy_workflow.json`.
- Reference-image conditioning (`/upload/image`), as the garden harness does.

---

## Wave 2 (2026-10-15)

Workstreams A–E are merged (PR #19). Wave 2 builds on that, with the same rules
as before: own your files, keep edits to shared files small and additive.

### Contract W2-1: reference images (F implements, G consumes)

- `POST /api/v1/render/references` (multipart, field `image`; png/jpeg/webp,
  ≤ 20 MB) returns `201 {"reference_id", "sha256", "filename", "width", "height"}`.
  Stored under `generated/renders/references/<sha256>.<ext>`, so the same
  file is never stored twice. The original upload is never modified.
- `GET /api/v1/render/references/{reference_id}` returns the stored image.
- `RenderJobRequest` gains optional `reference_id`. When it is set, the
  adapter uploads the file to ComfyUI `/upload/image` and wires `LoadImage`
  into `TextEncodeQwenImage21` (`vae` + `images.image_1`), as in the garden
  harness. `params.reference_id` and `result.reference_sha256` are recorded.

### Contract W2-2: witness renders linked to folios (F implements, G consumes)

- `POST /api/v1/operator/workings/{id}/witness` (and its `/manifest` alias)
  takes optional JSON `{"backend": "local" | "hosted"}`. `local` (the default
  when `/render/health` is reachable) submits a render job with
  `working_id=<id>`, `purpose="witness"` and the folio's image prompt. It
  returns `202 {"working_id", "operation": Operation}` straight away, with
  no blocking. `hosted` keeps today's synchronous OpenRouter path unchanged.
- When that render job succeeds, the folio's `witness` becomes
  `{"status": "ok", "source": "local-render", "operation_id", "image_url", "seed", "seed_provenance", "width", "height", "prompt"}`.
  When it fails: `{"status": "error", "operation_id", "error"}`. This is
  written by an operations listener (`core.operations.add_listener`), so the
  folio is updated even if no browser is open.
- To show progress, the UI reads `GET /operations?working_id=<id>&kind=render`.

### Contract W2-3: cancellable background operations (H implements, G consumes)

- `POST /api/v1/operations/{id}/cancel` returns `200 {"operation"}` once the
  operation has ended (normally `cancelled`, with its measured elapsed time).
  It returns `404` for an unknown id, and `409 {"detail"}` when the operation
  is already finished or nothing in this process can stop it. Which handler
  stops it is described under [Cancel registries](#cancel-registries-as-built).
- `POST /api/v1/radionics/broadcast` no longer blocks. It validates the
  request, creates the `broadcast` operation, runs the scalar loop in a
  worker thread, and returns straight away with the same fields as before.
  `operation_id` is set; fields that only exist after the run are null.
  Cancelling stops the loop at its next tick and records `cancelled` with
  the measured elapsed time.
- `vajra_service` sessions and sigil broadcasts that run for a duration are
  recorded as `broadcast`/`audio` operations (start → measured end).

### Cancel registries (as built)

`core.operations.request_cancel(op_id)` (behind `POST /operations/{id}/cancel`)
looks up a handler in two registries, the more specific one first:

| Registry | API | Who registers | Lifetime |
|---|---|---|---|
| **Per operation** | `register_op_cancel(op_id, fn)` / `unregister_op_cancel(op_id)` | Scalar-radionics broadcasts (`core/integrated_scalar_radionics.py`: `_track` registers `stop.request("cancelled")` on the run's `BroadcastStop`), and `vajra_service` audio sessions, including sigil broadcasts (`_cancel_session`). | Registered when the work is queued or started; removed when it ends (`_untrack`, `_end_session_operation`). |
| **Per kind** | `register_cancel_handler(kind, fn)` / `unregister_cancel_handler(kind)` | Only `render`: `backend/app/main.py:register_cancel_handlers` wires it to the render queue's `jobs.cancel_job` at warmup. | For the life of the process. |

A handler may be sync or async. It (or the worker it signals) records the
terminal state. `request_cancel` waits up to `CANCEL_SETTLE_SECONDS` (5 s)
for that. If the worker has not settled by then, it records `cancelled`
itself, and a worker that loses that race gets an `OperationError` from its
own late transition. No handler in either registry means `409`. That
includes a broadcast or session whose process restarted: it was already
reconciled to `interrupted`, so it is no longer active.

The broadcast path also keeps a third, private table that is not a ledger
registry: `_active` (operation id to `BroadcastStop`) in
`core/integrated_scalar_radionics.py`. Server shutdown uses it
(`stop_all_broadcasts` / `shutdown_broadcasts`, reason `"shutdown"`, so
those runs end `interrupted` rather than `cancelled`). `POST
/radionics/stop` stops crystal-grid playback only and does not cancel a
broadcast operation. `/render/jobs/{id}/cancel` remains an alias that
calls the render queue directly.
