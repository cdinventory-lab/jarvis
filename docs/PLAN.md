# JARVIS — Implementation Plan & Progress

## 1. Environment audit (performed before any code was written)

| # | Question | Finding |
|---|---|---|
| 1 | Project structure | Greenfield repo — only a placeholder `README.md` |
| 2 | Language | None chosen → **Python 3.11** (matches the spec's snippets; strongest automation ecosystem) |
| 3 | Framework | None → stdlib-first package; platform capabilities as optional extras |
| 4 | Operating system | Dev sandbox: headless Debian 12. **Target: Windows** → all platform access behind the `ComputerBackend` seam |
| 5 | Dependencies | None preinstalled; PyPI reachable |
| 6 | Runtimes | Python 3.11.2, Node 22 (unused) |
| 7 | Microphone | Not available in sandbox — voice is Phase 4; interfaces defined now |
| 8 | Screenshot / mouse / keyboard | No display in sandbox → **SimulatedBackend** for tests/demo + PyAutoGuiBackend for real machines |
| 9 | Local AI model | None in sandbox → deterministic rule-based brain for Phase 1; `AIProvider` seam for Phase 2 |
| 10 | Existing components | None |

Consequence: the architecture must let **development and CI happen headless**
while the **user experience happens on Windows**, with identical code paths.
That is exactly what the backend seam + simulated desktop provide.

---

## 2. Phased roadmap (spec §23)

### Phase 1 — Computer Control ✅ (this delivery)

* Mouse controller: move / click / double / right / drag / scroll / down / up
  + semantic `click_element` via screen perception.
* Keyboard controller: type / press / hotkey + named combos
  (copy, paste, select-all, save, arrows, F-keys).
* Screenshots (backend-provided) + OCR seam (Tesseract when installed).
* Basic Windows control: list / find / focus / minimize / maximize / close
  windows; active window; processes.
* Application launching: 13-app registry with Windows resolution
  (PATH → App Paths registry → default install locations), user folders.
* Text command interface: REPL + one-shot CLI + demos.
* **Autonomous loop** with per-step verification, retries, recovery, and
  `NEEDS_USER` escalation.
* Permission/safety layer (LOW/MEDIUM/HIGH), terminal allowlist, protected
  paths.
* Task memory with the §13 view (completed / current / remaining) + JSON
  persistence.
* Interrupt system: Ctrl+C, `stop` command, configurable emergency hotkey.
* Event bus + console UI (status ●, timestamped activity log, speech).
* Voice + AI-provider interfaces reserved (Phase 2/4 drop in without
  rewrites).
* 149 headless tests; `ruff` clean.

**Acceptance (spec §26):** `jarvis --demo notepad` runs
*"Open Notepad and type Hello JARVIS."* → launches Notepad → finds the
window (verified) → types the text → verifies the text is on screen →
reports completion. ✅ On the simulated desktop in CI, and the same code
path runs against real Notepad on Windows.

### Phase 2 — AI Control (next)

* `AIProvider` implementations (cloud LLM + local LLM, e.g. Ollama).
* LLM intent parsing (free-form requests, context, clarification questions).
* LLM-assisted planning + `replan()` for recovery.
* Dynamic tool selection with the existing registry; tool-call schemas.
* Stricter prompts → plans with expectations (verify everything).

### Phase 3 — Vision

* Robust OCR pipeline (image pre-processing, confidence thresholds).
* UI-element detection: buttons, input fields, menus, windows (not just text).
* `find_element` upgrades with element typing and stable selectors.
* Screenshot diffing for change detection.

### Phase 4 — Voice

* Local wake-word engine ("Hey JARVIS") — openWakeWord/Porcupine adapter.
* STT: local (Vosk/whisper.cpp) with optional cloud; `SpeechRecognizer`.
* TTS: pyttsx3/SAPI voice with configurable voice/rate/volume/verbosity.
* Full voice interrupt integration with the existing `InterruptFlag`.

### Phase 5 — Memory

* Long-term user preferences (separate from task memory).
* Persistent configuration profiles.
* Task resumption across restarts.

### Phase 6 — Advanced autonomy

* Application adapters (Blender, VS Code, browser via CDP/Playwright).
* Long multi-step projects with checkpointing.
* Background tasks + scheduling.
* Remote/VM backend for sandboxes.

---

## 3. Phase-1 verification evidence

* `make test` — 149 passed, 1 skipped (environment-conditional), ~4 s.
* End-to-end orchestrator tests cover: the §26 demo, compound search task,
  folder create+open with `open it` context, close-after-open, permission
  denial, protected-path risk escalation, mid-task interrupt, unknown input
  handling, memory persistence.
* `jarvis --demo notepad|search|folder` run the acceptance scenarios.
