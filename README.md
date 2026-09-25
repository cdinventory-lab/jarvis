# JARVIS — Autonomous PC Assistant

JARVIS is a Windows-first computer-use agent: it understands natural-language
commands, **plans**, **operates the real computer** (mouse, keyboard, apps,
browser, files), **verifies** the result by observing the screen, and
**recovers or asks** when something fails.

> "Hey JARVIS, open Chrome and search for Blender clothing mockups."
>
> — JARVIS plans the task, launches Chrome, opens the search, verifies the
> results page is on screen, and reports back.

It is **not** a chatbot that gives instructions — it is an agent that acts.

---

## Status

**Phase 1 — Computer Control: complete.**

| Phase | Scope | Status |
|---|---|---|
| 1 | Mouse, keyboard, screenshots, windows, app launching, text command interface, safety layer, verification | ✅ **done** |
| 2 | AI provider (LLM) + tool calling + task planning | ⏳ next (interfaces ready) |
| 3 | Vision: OCR, UI detection, visual element targeting | 🔶 basic OCR seam + `find_element` done |
| 4 | Voice: wake word, STT, TTS | ⏳ interfaces ready (`voice/`) |
| 5 | Memory: task memory, user preferences, persistence | 🔶 task memory done |
| 6 | Advanced autonomy: adapters, long tasks, scheduling | ⏳ |

See [docs/PLAN.md](docs/PLAN.md) for the full roadmap and acceptance criteria.

---

## The loop that makes it an agent (not a script)

```
OBSERVE → UNDERSTAND → PLAN → ACT → VERIFY → RECOVER → REPORT
```

Every step JARVIS takes carries an **expected outcome**. After acting, the
verifier re-observes the world — *window appeared? process running? file
exists? text visible on screen?* — and only then is a step considered done.
Failures are retried, re-planned, and finally escalated to the user.

```
18:21:04  User: Open Notepad and type Hello JARVIS.
18:21:04  ◇ Plan ready - 2 step(s): 1) Launch Notepad -> 2) Type 'Hello JARVIS'
18:21:04  ▸ Step 1/2: Launch Notepad
18:21:05  ✓ window detected: 'Notepad'
18:21:05  ▸ Step 2/2: Type 'Hello JARVIS'
18:21:06  ✓ text 'Hello JARVIS' found on screen
18:21:06  ✓ Task completed
18:21:06  JARVIS: Done. Completed 2 steps: ...
```

---

## Quickstart

### On your PC (Windows recommended)

```powershell
git clone https://github.com/cdinventory-lab/jarvis
cd jarvis
python -m venv .venv
.venv\Scripts\pip install -e ".[computer,ocr,hotkey,dev]"

# see what JARVIS can detect on this machine
.venv\Scripts\python -m jarvis --doctor

# start the assistant (typed commands; voice arrives in Phase 4)
.venv\Scripts\python -m jarvis
```

`--doctor` tells you exactly which capabilities are available (display,
pyautogui, OCR/tesseract, clipboard, hotkey library) and what to install.

> **OCR note:** screen-text verification needs the
> [Tesseract binary](https://github.com/UB-Mannheim/tesseract/wiki) on PATH.
> Without it, tasks still run — unverifiable checks report `UNKNOWN` instead
> of failing.

### Anywhere else (headless Linux/macOS, CI)

JARVIS runs on a built-in **simulated desktop** — same brain, same tools,
same verification loop, zero risk:

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m jarvis --backend simulated --demo notepad
.venv/bin/python -m pytest          # 149 tests, fully headless
```

### Built-in demos

```bash
python -m jarvis --demo notepad   # "Open Notepad and type Hello JARVIS."
python -m jarvis --demo search    # "Open Chrome and search for Blender clothing mockups."
python -m jarvis --demo folder    # "Create a folder named Jarvis Demo ... and open it."
```

---

## Usage

```
jarvis                          # interactive REPL
jarvis "open notepad and type hello world"
jarvis --backend simulated      # force the safe simulated desktop
jarvis --assume-yes             # auto-approve MEDIUM-risk for scripted runs
jarvis --doctor                 # environment / capability report
jarvis --list-apps --list-tools
```

In the REPL: type commands, `help`, `tools`, `apps`, `memory`, `status`,
`exit`. **Ctrl+C stops the running task**, `exit` quits. The emergency
hotkey **CTRL+ALT+J** (configurable) stops computer control instantly once
the `keyboard` extra is installed.

### What Phase 1 understands

```
open notepad · launch chrome · open blender · start vs code
open my downloads folder · open folder D:\projects
open blender.org · go to github.com
search for blender tutorials · search for mockups in chrome
open notepad and type Hello JARVIS
press enter · press ctrl+s · press ctrl+shift+esc
close notepad · close the window · minimize chrome · maximize notepad
create folder Demo in my documents
take a screenshot · scroll down
```

Chain steps with `and` / `then`. Unknown phrasings safely ask for help
instead of guessing.

---

## Safety model (spec §15)

| Risk | Examples | Behaviour |
|---|---|---|
| **LOW** | open app, search web, scroll, read, type text | runs automatically |
| **MEDIUM** | create/move/copy files, unknown-app launch | asks, or auto-approves if `JARVIS_AUTO_APPROVE_RISK=medium` |
| **HIGH** | terminal commands, protected system paths | always asks |

Backed by:

* an **allowlist** for terminal commands (`shell=False`, no string commands),
* **protected path** detection (never modifies `C:\Windows`, `/etc`, ...),
* unknown executables are never run blindly — they require confirmation,
* every approval/denial is shown in the activity log,
* JARVIS never attempts to bypass Windows security, antivirus or UAC.

All configuration is via environment variables / `.env` (see
`.env.example`). No secrets in code, ever.

---

## Architecture

```
jarvis/
├── core/
│   ├── brain/          # intent parsing + planning (RuleBasedBrain now, LLM in Phase 2)
│   ├── planner/        # Intent / Step / Plan / Expectation models
│   ├── memory/         # task memory (completed / current / remaining)
│   └── orchestrator/   # the observe → act → verify → recover loop
├── perception/         # screenshots, OCR seam, find_element
├── control/            # backend abstraction + mouse/keyboard/windows/apps/files/terminal
│   └── backends/       # PyAutoGuiBackend (real PC) · SimulatedBackend (tests/CI)
├── browser/            # URL / search now; structured automation in Phase 2+
├── voice/              # wake-word / STT / TTS interfaces (Phase 4)
├── tools/              # tool registry: name, params, risk, execute, verify
├── security/           # risk levels, permission policy, approvers
├── verification/       # SUCCESS / FAILED / UNKNOWN / NEEDS_USER
├── ui/                 # console UI (status ●, activity log, prompt)
├── config/             # env-driven settings
└── app.py              # composition root
```

Full component map and extension guides:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

**Design principles**

* **Backend seam** — everything above `control/backend.py` is
  platform-agnostic. Real PC control and the simulated desktop implement the
  same interface; so will a future remote/VM backend.
* **Provider-agnostic AI** — `AIProvider` (spec §19) is the Phase-2 seam for
  local or cloud LLMs. The rule-based brain keeps Phase 1 fully offline.
* **Events, not print statements** — components emit events on an `EventBus`;
  the console UI today, a desktop/web UI later, render the same feed. Private
  chain-of-thought is never exposed.
* **Independently testable** — every controller and tool runs against the
  simulated backend; `pytest` covers the whole loop headlessly.

---

## Development

```bash
make install   # venv + editable install with dev extras
make test      # pytest (149 tests)
make lint      # ruff
make demo      # phase-1 demo on the simulated desktop
make doctor    # environment report
```

Logs live in `~/.jarvis/logs/jarvis.log`; task memory in
`~/.jarvis/task_memory.json` (both configurable via `JARVIS_DATA_DIR`).

---

## Roadmap

* **Phase 2 — AI control:** wrap a cloud/local LLM behind `AIProvider` for
  free-form requests, dynamic tool selection, and LLM-assisted re-planning.
* **Phase 3 — vision:** robust OCR-based UI detection (buttons, inputs,
  menus) feeding `click_element`, plus icon/element models.
* **Phase 4 — voice:** local wake word ("Hey JARVIS"), local + cloud STT,
  natural TTS (SAPI/pyttsx3), full duplex with the interrupt system.
* **Phase 5 — memory:** user preferences, long-term memory, persistent
  configuration.
* **Phase 6 — advanced autonomy:** app adapters (Blender, VS Code, browser
  via CDP), background tasks, scheduling, multi-step project workflows.

Contributions welcome — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for the extension points first.
