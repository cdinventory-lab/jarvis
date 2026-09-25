"""Phase-1 deterministic brain: intent parsing + plan construction.

No LLM yet - by design (spec section 23: Phase 2 adds the AI provider).
This brain handles the core computer-control vocabulary with regex rules and
produces plans whose steps each carry a risk level and a *verifiable
expectation*, which is what makes the observe->act->verify loop possible.

Known limitations (Phase 2 fixes them): simple quote-aware splitting of
compound commands, no context-dependent disambiguation, English only.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jarvis.control.apps import APP_REGISTRY, USER_FOLDERS, resolve_app_name
from jarvis.core.brain.base import Brain
from jarvis.core.planner.models import (
    Expectation,
    ExpectationKind,
    Intent,
    Plan,
    Step,
)
from jarvis.security.permissions import RiskLevel

# --------------------------------------------------------------------------- #
# Text normalisation
# --------------------------------------------------------------------------- #

_WAKE_PREFIXES = ("hey jarvis", "jarvis", "ok jarvis")
_POLITENESS = ("please", "for me", "thanks")

_URL_RE = re.compile(r"^(https?://\S+|[\w-]+(?:\.[\w-]+)+(?:/\S*)?)$", re.IGNORECASE)
_SPECIAL_FOLDERS = "|".join(USER_FOLDERS.keys())


def _strip_quotes(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _normalize(text: str) -> str:
    """Drop wake words / politeness / trailing sentence dot.

    Case is PRESERVED so typed text, search queries and file names keep
    their original form ("Hello JARVIS" stays "Hello JARVIS").
    """
    cleaned = text.strip()
    lowered = cleaned.lower()
    for prefix in _WAKE_PREFIXES + ("please", "could you", "can you"):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].lstrip(" ,:;")  # noqa: B005 - char set
            lowered = cleaned.lower()
    for suffix in _POLITENESS:
        if lowered.endswith(f" {suffix}"):
            cleaned = cleaned[: -(len(suffix) + 1)]
            lowered = cleaned.lower()
    cleaned = cleaned.strip()
    if cleaned.endswith(".") and not _URL_RE.match(cleaned):
        cleaned = cleaned.rstrip(".").rstrip()
    return cleaned


def _split_compound(text: str) -> list[str]:
    """Split 'open notepad and type hello' into segments (quote-aware)."""
    segments: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    i = 0
    lowered = text.lower()
    connectors = (" and then ", " then ", " after that ", " and ")
    while i < len(text):
        char = text[i]
        if quote:
            buffer.append(char)
            if char == quote:
                quote = None
            i += 1
            continue
        if char in "'\"":
            quote = char
            buffer.append(char)
            i += 1
            continue
        matched = next(
            (c for c in connectors if lowered.startswith(c, i) and buffer), None
        )
        if matched:
            segments.append("".join(buffer).strip())
            buffer = []
            i += len(matched)
            continue
        buffer.append(char)
        i += 1
    tail = "".join(buffer).strip()
    if tail:
        segments.append(tail)
    return [s for s in (seg.strip(" ,;") for seg in segments) if s]  # noqa: B005 - char set


# --------------------------------------------------------------------------- #
# Intent parsing (ordered rules)
# --------------------------------------------------------------------------- #

_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("meta.stop", re.compile(r"^(stop|cancel|pause|wait|halt|abort)$")),
    ("meta.help", re.compile(r"^(help|what can you do|list commands|commands)$")),
    ("meta.status", re.compile(r"^(status|what are you doing|current task|show status)$")),
    ("meta.greeting", re.compile(r"^(hello|hi|hey|good (morning|afternoon|evening))$")),
    ("meta.thanks", re.compile(r"^(thanks|thank you|cheers)$")),
    ("screenshot", re.compile(r"^(?:take|capture|grab)(?: a| the)? screenshot$")),
    (
        "create_folder",
        re.compile(
            r"^create (?:a |a new |new )?(?:folder|directory)"
            r"(?: called | named | name )?(?P<name>.+?)"
            r"(?: (?:in|under|inside) (?P<base>.+))?$"
        ),
    ),
    (
        "open_folder",
        re.compile(r"^open (?:my |the )?(?P<folder>" + _SPECIAL_FOLDERS + r")(?: folder)?$"),
    ),
    (
        "open_folder.path",
        re.compile(r"^open (?:the )?(?:folder|directory) (?P<path>.+)$"),
    ),
    ("open_file", re.compile(r"^open (?:the )?(?:file|document) (?P<path>.+)$")),
    (
        "search_web",
        re.compile(
            r"^(?:search(?: the web| the internet)?|google|look up)"
            r"(?: for)? (?P<query>.+?)"
            r"(?: (?:in|with|using|on) (?P<browser>chrome|google chrome|edge|firefox|browser|google))?$"
        ),
    ),
    (
        "open_url",
        re.compile(r"^(?:open|go to|navigate to|browse to|visit) (?P<url>https?://\S+)$"),
    ),
    (
        "open_url.bare",
        re.compile(
            r"^(?:open|go to|navigate to|browse to|visit) (?P<url>[\w-]+(?:\.[\w-]+)+(?:/\S*)?)$"
        ),
    ),
    ("press_key", re.compile(r"^(?:press|hit) (?:the )?(?P<key>.+)$")),
    ("type_text", re.compile(r"^(?:type|write|input)(?: out)? (?P<text>.+)$")),
    (
        "close",
        re.compile(
            r"^(?:close|quit|exit|kill|terminate) (?:the )?(?:current |active )?"
            r"(?P<target>window|windows|app|application|program|.*)$"
        ),
    ),
    (
        "minimize",
        re.compile(r"^(?:minimize|minimise)(?: the)?(?: window)?(?: (?P<target>.+))?$"),
    ),
    (
        "maximize",
        re.compile(r"^maximize(?: the)?(?: window)?(?: (?P<target>.+))?$"),
    ),
    (
        "scroll",
        re.compile(r"^scroll (?P<direction>up|down)(?: by (?P<amount>\d+).*)?$"),
    ),
    (
        "open_app",
        re.compile(
            r"^(?:open|launch|start|run|fire up)(?: up)? (?:my |the )?"
            r"(?P<app>.+?)(?: (?:app|application|program))?$"
        ),
    ),
]

def _compile_case_insensitive(rules):
    return [(name, re.compile(pattern.pattern, pattern.flags | re.IGNORECASE))
            for name, pattern in rules]


_RULES = _compile_case_insensitive(_RULES)


_META_REPLIES = {
    "meta.greeting": "Hello. I'm listening - what would you like me to do?",
    "meta.thanks": "You're welcome.",
    "meta.help": (
        "I can: open apps ('open notepad'), type text ('type hello world'), "
        "press keys ('press enter', 'press ctrl+s'), search the web ('search for "
        "blender tutorials', 'search for X in chrome'), open URLs ('open "
        "blender.org'), open folders ('open my downloads folder'), create folders "
        "('create folder demo in my documents'), close/minimize/maximize apps, "
        "take screenshots, and run approved terminal commands. Chain steps with "
        "'and' or 'then'."
    ),
}

_MODIFIERS = {"ctrl", "control", "alt", "shift", "win", "windows", "cmd", "meta", "super"}


class RuleBasedBrain(Brain):
    """Deterministic intent parser + planner for Phase 1 commands."""

    name = "rule-based"

    # ------------------------------------------------------------------ parsing

    def understand(self, text: str) -> list[Intent]:
        intents: list[Intent] = []
        for segment in _split_compound(_normalize(text)):
            intent = self._parse_segment(segment)
            if intent is not None:
                intents.append(intent)
        return intents

    def meta_reply(self, intent_name: str) -> str | None:
        """Static conversational replies for meta intents (help/greeting...)."""
        return _META_REPLIES.get(intent_name)

    def _parse_segment(self, segment: str) -> Intent | None:
        for name, pattern in _RULES:
            match = pattern.match(segment)
            if not match:
                continue
            groups = match.groupdict()
            groups = {k: v for k, v in groups.items() if v is not None}
            intent = self._build_intent(name, groups, segment)
            if intent is not None:
                return intent
        return None

    def _build_intent(self, name: str, groups: dict[str, str], segment: str) -> Intent | None:
        if name.startswith("meta."):
            return Intent(name=name, slots={}, raw=segment, confidence=1.0)
        if name == "screenshot":
            return Intent(name, {}, segment)
        if name == "create_folder":
            return Intent(
                name,
                {"name": _strip_quotes(groups["name"]), "base": groups.get("base", "")},
                segment,
            )
        if name == "open_folder":
            return Intent(name, {"folder": groups["folder"].lower()}, segment)
        if name == "open_folder.path":
            return Intent(name, {"path": _strip_quotes(groups["path"])}, segment)
        if name == "open_file":
            return Intent(name, {"path": _strip_quotes(groups["path"])}, segment)
        if name == "search_web":
            browser = (groups.get("browser", "") or "").lower()
            if browser in ("google", "google chrome"):
                browser = "chrome"
            if browser == "browser":
                browser = ""
            return Intent(
                name, {"query": _strip_quotes(groups["query"]), "browser": browser}, segment
            )
        if name in ("open_url", "open_url.bare"):
            url = groups["url"]
            if url.lower().endswith((".exe", ".msi", ".bat", ".cmd")):
                return None  # an executable, not a website - let open_app handle it
            return Intent("open_url", {"url": url}, segment)
        if name == "press_key":
            return self._parse_press(groups["key"], segment)
        if name == "type_text":
            return Intent(name, {"text": _strip_quotes(groups["text"])}, segment)
        if name == "close":
            return Intent(name, {"target": groups.get("target", "").strip()}, segment)
        if name in ("minimize", "maximize"):
            return Intent(name, {"target": groups.get("target", "").strip()}, segment)
        if name == "scroll":
            amount = int(groups.get("amount") or 3)
            return Intent(
                name,
                {"direction": groups["direction"], "amount": amount},
                segment,
            )
        if name == "open_app":
            app = groups["app"].strip()
            if app in ("it", "that"):
                # e.g. "create folder X ... and open it" - resolved in plan()
                return Intent("open_recent", {}, segment)
            spec = resolve_app_name(app)
            return Intent(
                name,
                {"app": spec.name if spec else app, "known": spec is not None},
                segment,
            )
        return None

    def _parse_press(self, keys: str, segment: str) -> Intent:
        from jarvis.control.keyboard import normalize_key

        raw_parts = [p for p in re.split(r"\+| ", keys.strip()) if p]
        try:
            parts = [normalize_key(p) for p in raw_parts]
        except ValueError:
            return Intent("press_key", {"key": raw_parts[0] if raw_parts else ""}, segment)
        if len(parts) > 1 and any(p in _MODIFIERS for p in parts):
            return Intent("hotkey", {"keys": parts}, segment)
        return Intent("press_key", {"key": parts[0] if parts else ""}, segment)

    # ------------------------------------------------------------------ planning

    def plan(self, intents: list[Intent], context: dict[str, Any]) -> Plan:
        task = str(context.get("task", "")).strip()
        plan = Plan(task=task)
        home = Path(context.get("home", str(Path.home())))
        last_browser: str | None = None

        seq = itertools.count(1)
        last_created_folder: str | None = None

        for intent in intents:
            if intent.name.startswith("meta."):
                continue  # meta intents are handled by the orchestrator
            if intent.name == "open_recent":
                if last_created_folder:
                    plan.steps.append(
                        Step(
                            step_id=f"s{next(seq)}",
                            action="open_folder",
                            params={"path": last_created_folder},
                            description=f"Open folder {last_created_folder}",
                            risk=RiskLevel.LOW,
                            expectation=Expectation(
                                ExpectationKind.WINDOW_APPEARS,
                                {
                                    "title_contains": Path(last_created_folder).name,
                                },
                            ),
                        )
                    )
                continue
            steps = self._steps_for_intent(intent, home, last_browser, seq)
            for step in steps:
                plan.steps.append(step)
                if step.action == "create_folder":
                    last_created_folder = str(step.params.get("path", "")) or None
            if intent.name == "open_app":
                spec = APP_REGISTRY.get(intent.slots.get("app", ""))
                if spec and spec.is_browser:
                    last_browser = spec.name
        return plan

    # ------------------------------------------------------------ step builders

    def _steps_for_intent(
        self, intent: Intent, home: Path, last_browser: str | None, seq: itertools.count[int]
    ) -> list[Step]:
        name = intent.name
        slots = intent.slots

        def next_id() -> str:
            return f"s{next(seq)}"

        if name == "open_app":
            spec = APP_REGISTRY.get(slots["app"])
            expectation = Expectation(ExpectationKind.NONE)
            if spec:
                params: dict[str, Any] = {
                    "app": spec.name,
                    "titles": list(spec.window_titles),
                }
                expectation = Expectation(
                    ExpectationKind.WINDOW_APPEARS,
                    {"any_title_contains": list(spec.window_titles), "app": spec.name},
                )
                description = f"Launch {spec.display}"
                risk = RiskLevel.LOW
            else:
                params = {"app": slots["app"], "generic": True}
                description = f"Launch {slots['app']} (unknown app - trying PATH)"
                risk = RiskLevel.MEDIUM
            return [
                Step(
                    step_id=next_id(),
                    action="open_app",
                    params=params,
                    description=description,
                    risk=risk,
                    expectation=expectation,
                )
            ]

        if name == "type_text":
            return [
                Step(
                    step_id=next_id(),
                    action="type_text",
                    params={"text": slots["text"]},
                    description=f"Type {slots['text']!r}",
                    risk=RiskLevel.LOW,
                    expectation=Expectation(
                        ExpectationKind.SCREEN_CONTAINS_TEXT, {"text": slots["text"]}
                    ),
                )
            ]

        if name == "press_key":
            return [
                Step(
                    step_id=next_id(),
                    action="press_key",
                    params={"key": slots["key"]},
                    description=f"Press {slots['key']}",
                    risk=RiskLevel.LOW,
                )
            ]

        if name == "hotkey":
            keys = slots["keys"]
            return [
                Step(
                    step_id=next_id(),
                    action="hotkey",
                    params={"keys": keys},
                    description=f"Press {'+'.join(keys)}",
                    risk=RiskLevel.LOW,
                )
            ]

        if name == "search_web":
            browser = slots.get("browser") or last_browser or ""
            query = slots["query"]
            return [
                Step(
                    step_id=next_id(),
                    action="search_web",
                    params={"query": query, "browser": browser},
                    description=f"Search the web for {query!r}"
                    + (f" in {browser}" if browser else ""),
                    risk=RiskLevel.LOW,
                    expectation=Expectation(
                        ExpectationKind.WINDOW_APPEARS, {"title_contains": query}
                    ),
                )
            ]

        if name == "open_url":
            url = slots["url"]
            domain = urlparse(url if "://" in url else "https://" + url).hostname or url
            return [
                Step(
                    step_id=next_id(),
                    action="open_url",
                    params={"url": url, "browser": last_browser or ""},
                    description=f"Open {url}",
                    risk=RiskLevel.LOW,
                    expectation=Expectation(
                        ExpectationKind.WINDOW_APPEARS, {"title_contains": domain.split(".")[0]}
                    ),
                )
            ]

        if name == "open_folder":
            folder = slots["folder"]
            key = folder.strip().lower()
            target = home / (USER_FOLDERS.get(key, "") if key in USER_FOLDERS else key)
            return [
                Step(
                    step_id=next_id(),
                    action="open_folder",
                    params={"folder": folder},
                    description=f"Open the {folder} folder",
                    risk=RiskLevel.LOW,
                    expectation=Expectation(
                        ExpectationKind.WINDOW_APPEARS,
                        {"title_contains": target.name or "Home"},
                    ),
                )
            ]

        if name == "open_folder.path":
            return [
                Step(
                    step_id=next_id(),
                    action="open_folder",
                    params={"path": slots["path"]},
                    description=f"Open folder {slots['path']}",
                    risk=RiskLevel.LOW,
                )
            ]

        if name == "open_file":
            return [
                Step(
                    step_id=next_id(),
                    action="open_file",
                    params={"path": slots["path"]},
                    description=f"Open file {slots['path']}",
                    risk=RiskLevel.LOW,
                )
            ]

        if name == "create_folder":
            base = slots.get("base", "")
            if base:
                base_dir = self._resolve_base(base, home)
                path = base_dir / slots["name"]
            else:
                path = home / slots["name"]
            return [
                Step(
                    step_id=next_id(),
                    action="create_folder",
                    params={"path": str(path)},
                    description=f"Create folder {path}",
                    risk=RiskLevel.MEDIUM,
                    expectation=Expectation(ExpectationKind.DIR_EXISTS, {"path": str(path)}),
                )
            ]

        if name == "close":
            target = slots.get("target", "")
            if target in ("", "window", "windows", "app", "application", "program"):
                params: dict[str, Any] = {"active": True}
                description = "Close the active window"
                expectation = Expectation(ExpectationKind.NONE)
            else:
                spec = resolve_app_name(target)
                hint = spec.window_titles[0] if spec and spec.window_titles else target
                params = {"title_contains": hint}
                description = f"Close {spec.display if spec else target}"
                expectation = Expectation(
                    ExpectationKind.WINDOW_CLOSED, {"title_contains": hint}
                )
            return [
                Step(
                    step_id=next_id(),
                    action="close_app",
                    params=params,
                    description=description,
                    risk=RiskLevel.LOW,
                    expectation=expectation,
                )
            ]

        if name in ("minimize", "maximize"):
            target = slots.get("target", "")
            params: dict[str, Any] = {"active": True}
            description = f"{'Minimize' if name == 'minimize' else 'Maximize'} the active window"
            if target and target not in ("window", "the window"):
                spec = resolve_app_name(target)
                params = {"title_contains": spec.window_titles[0] if spec else target}
                description = (
                    f"{'Minimize' if name == 'minimize' else 'Maximize'} "
                    f"{spec.display if spec else target}"
                )
            return [
                Step(
                    step_id=next_id(),
                    action=f"{name}_window",
                    params=params,
                    description=description,
                    risk=RiskLevel.LOW,
                )
            ]

        if name == "scroll":
            amount = -slots["amount"] if slots["direction"] == "down" else slots["amount"]
            return [
                Step(
                    step_id=next_id(),
                    action="scroll",
                    params={"amount": amount},
                    description=f"Scroll {slots['direction']}",
                    risk=RiskLevel.LOW,
                )
            ]

        if name == "screenshot":
            return [
                Step(
                    step_id=next_id(),
                    action="screenshot",
                    params={},
                    description="Take a screenshot",
                    risk=RiskLevel.LOW,
                )
            ]

        return []

    @staticmethod
    def _resolve_base(base: str, home: Path) -> Path:
        key = base.strip().lower().removesuffix(" folder").replace("my ", "").strip()
        if key in USER_FOLDERS:
            return home / USER_FOLDERS[key]
        candidate = Path(base).expanduser()
        return candidate if candidate.is_absolute() else home / candidate
