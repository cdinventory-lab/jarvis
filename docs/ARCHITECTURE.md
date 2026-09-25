# JARVIS Architecture

## Component map

```
                    ┌──────────────────────┐
                    │  UI (console now,    │  subscribes to EventBus
                    │  GUI later)          │  (status, activity, speech)
                    └──────────▲───────────┘
                               │ events
┌──────────────────────────────┴──────────────────────────────────────┐
│                            ORCHESTRATOR                             │
│   observe → understand → plan → act → verify → recover → report    │
│   (interrupt-aware, permission-gated, memory-backed)                │
└───┬───────────────┬────────────────┬───────────────┬───────────────┬─┘
    │               │                │               │               │
┌───▼───┐    ┌──────▼─────┐   ┌──────▼─────┐  ┌──────▼─────┐  ┌─────▼─────┐
│ BRAIN │    │   TOOLS    │   │ VERIFIER   │  │  SECURITY  │  │  MEMORY   │
│ rules │    │ registry   │   │ window/    │  │ risk +     │  │ task      │
│ (LLM  │    │ (§18)      │   │ process/   │  │ approvers  │  │ state +   │
│ later)│    └──────┬─────┘   │ file/text  │  └────────────┘  │ persist   │
└────────┘           │         └──────┬─────┘                  └───────────┘
                     │                │
              ┌──────▼────────────────▼──────┐
              │        CONTROLLERS           │
              │ mouse · keyboard · windows   │
              │ apps · filesystem · terminal │
              │ perception (OCR/vision)      │
              └──────────────┬───────────────┘
                             │ ComputerBackend (the platform seam)
              ┌──────────────┴───────────────┐
              │  PyAutoGuiBackend (real PC)  │
              │  SimulatedBackend (tests/CI) │
              └──────────────────────────────┘
```

## The platform seam: `ComputerBackend`

`jarvis/control/backend.py` defines every raw computer operation (mouse,
keyboard, screenshot, windows, processes, clipboard, launching). Two
implementations:

* **`PyAutoGuiBackend`** — PyAutoGUI for input/screenshot, pygetwindow on
  Windows for windows, psutil for processes, `os.startfile`/`webbrowser`
  for system handlers. All imports are lazy; the backend fails fast with a
  readable install hint when the machine can't support it.
* **`SimulatedBackend`** — a virtual desktop: windows with titles and text
  content, processes, focus-follows-click, startup latency (to exercise
  polling), clipboard, and a `SimScreenImage` screenshot stand-in whose
  text blocks stand in for OCR output.

Adding a backend (e.g. remote VM/VNC) = implement the interface; nothing
else changes.

## The planning contract

`core/planner/models.py` is the shared language:

* `Intent` — one understood unit of the request.
* `Step` — one action: `action` (tool name), `params`, `risk`,
  `expectation`, plus runtime `status/attempts/detail`.
* `Expectation` — what must be true afterwards (window appears, process
  running, file exists, screen contains text, ...).
* `Plan` — ordered steps (+ optional `direct_reply` for meta intents).

The **brain** produces plans; the **orchestrator** executes them; the
**verifier** checks expectations; **memory** records progress. None of them
know how the others are implemented.

## The loop (orchestrator)

```
for step in plan:
    interrupt check
    risk = tool.effective_risk(params)          # static or computed
    decision = security.check(request)          # auto / ask / deny
    if denied: step skipped → NEEDS_USER
    for attempt in 1..(1 + max_retries):
        emit EXECUTING, speak step
        result = tools.dispatch(action, params)
        if failed: retry (backoff, interruptible)
        if expectation == NONE: step done
        emit VERIFYING
        verification = verifier.verify(expectation)
        SUCCESS → done
        UNKNOWN → done with warning (e.g. no OCR installed)
        FAILED  → retry → recovery → NEEDS_USER
    memory.update_step
    interrupt check
summary → status COMPLETE / NEEDS_USER / FAILED / INTERRUPTED → speech
```

## Verification

`verification/verifier.py` polls the world until an expectation holds,
fails, or times out (all polling is interrupt-aware):

| Expectation | How it's checked |
|---|---|
| `WINDOW_APPEARS` / `WINDOW_CLOSED` | backend window list (title/app hints) |
| `ACTIVE_WINDOW` | focused window matches |
| `PROCESS_RUNNING` | process list (psutil / tasklist / simulated) |
| `FILE_EXISTS` / `DIR_EXISTS` | filesystem |
| `SCREEN_CONTAINS_TEXT` | OCR over a fresh screenshot |

Outcomes: `SUCCESS`, `FAILED`, `UNKNOWN` (cannot observe — e.g. no OCR
installed), `NEEDS_USER` (strict mode when unverifiable). JARVIS never
claims success for an action it could not verify — it says so.

## Safety

* `RiskLevel` LOW/MEDIUM/HIGH; `SecurityPolicy` decides auto-approve vs ask.
* `Approver` implementations: console prompt (interactive), deny-all
  (non-interactive default), auto (tests/`--assume-yes`).
* Terminal: executable allowlist, `shell=False`, hard timeout, HIGH risk.
* Filesystem: protected system paths refused outright; writes are MEDIUM.
* Unknown apps: registry → PATH → OS handler, and only after a MEDIUM-risk
  confirmation. Never a blind shell string.

## Events & UI

All observability flows through `EventBus`
(`status/user_input/plan/tool_call/verification/approval/error/speech/task`).
`ConsoleUI` renders the timestamped feed with status glyphs
(● Listening/Thinking/Executing/Verifying, ✓ Complete). A future desktop or
web UI subscribes to the same bus. The feed shows actions and outcomes —
never private chain-of-thought.

## Interrupts

One `InterruptFlag` shared by orchestrator, verifier and every polling loop.
Sources: Ctrl+C, the `stop` command, the emergency hotkey
(CTRL+ALT+J, `keyboard` extra). Poll granularity ~150–200 ms.

## Extension guide

| To add… | Do this |
|---|---|
| An LLM brain | implement `AIProvider` (core/brain/provider.py), wrap it in a `Brain` and pass it in `build_assistant` |
| A wake-word engine | implement `voice/wakeword/base.py` |
| STT/TTS engines | implement `voice/speech_to_text` / `voice/text_to_speech` |
| A new app | add an `AppSpec` to `APP_REGISTRY` in `control/apps.py` |
| A new tool | build a `Tool` and register it in `tools/builtin.py` |
| A new backend | implement `control/backend.py` and add it to `create_backend` |
| A new expectation | add an `ExpectationKind` + checker in the verifier |
| A GUI | subscribe a renderer to the `EventBus` |

## Threading model (Phase 1)

Single-threaded and synchronous by design: the REPL calls
`orchestrator.execute(text)` and renders events as they're emitted. The only
background thread is the optional emergency-hotkey listener. Phase 4 (voice)
introduces the audio threads, and the event bus is already thread-safe.
