"""Screen perception (spec section 5).

:class:`ComputerVision` exposes the interface the spec asks for:

    screenshot()          - capture the screen
    analyze_screen(image) - what text/elements are visible
    find_element(desc)    - locate "Chrome address bar"-style targets

Element finding is text/OCR based in Phase 1; Phase 3 upgrades this with
proper UI detection (icons, input boxes, buttons) without changing callers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jarvis.control.backend import ComputerBackend
from jarvis.perception.ocr.engine import OcrEngine, TextBlock

logger = logging.getLogger("jarvis.perception")


@dataclass(frozen=True)
class Element:
    """A located UI target."""

    text: str
    box: tuple[int, int, int, int]
    confidence: float
    source: str = "ocr"

    @property
    def center(self) -> tuple[int, int]:
        x, y, w, h = self.box
        return (x + w // 2, y + h // 2)


@dataclass(frozen=True)
class ScreenAnalysis:
    size: tuple[int, int]
    text_blocks: tuple[TextBlock, ...]

    @property
    def text(self) -> str:
        return "\n".join(block.text for block in self.text_blocks)

    def contains_text(self, text: str) -> bool:
        needle = text.strip().lower()
        return any(needle in block.text.lower() for block in self.text_blocks)


def _match_score(block_text: str, description: str) -> float:
    """0..1 relevance of a text block for a description."""
    block = block_text.strip().lower()
    target = description.strip().lower()
    if not target:
        return 0.0
    if block == target:
        return 1.0
    if block.startswith(target) or block.endswith(target):
        return 0.9
    if target in block:
        return 0.75
    # word-level overlap for menu bars like "File  Edit  Format  View  Help"
    target_words = set(target.split())
    block_words = set(block.split())
    if target_words and target_words <= block_words:
        return 0.7
    return 0.0


class ComputerVision:
    """Screenshot + OCR based perception over any backend."""

    def __init__(self, backend: ComputerBackend, ocr: OcrEngine) -> None:
        self.backend = backend
        self.ocr = ocr

    # ------------------------------------------------------------------ capture

    def screenshot(self) -> object:
        return self.backend.screenshot()

    # ------------------------------------------------------------------ analyze

    def analyze_screen(self, image: object | None = None) -> ScreenAnalysis:
        if image is None:
            image = self.screenshot()
        try:
            blocks = self.ocr.extract_text(image)
        except Exception as exc:  # noqa: BLE001 - perception must not crash the agent
            logger.warning("OCR failed: %s", exc)
            blocks = []
        return ScreenAnalysis(size=self.backend.screen_size(), text_blocks=tuple(blocks))

    # ------------------------------------------------------------------- search

    def find_element(self, description: str) -> Element | None:
        """Locate the best on-screen match for a description.

        Returns None when nothing scores well enough - callers re-plan or
        ask the user instead of clicking a guess.
        """
        if not getattr(self.ocr, "available", True):
            return None
        analysis = self.analyze_screen()
        best: tuple[float, TextBlock] | None = None
        for block in analysis.text_blocks:
            score = _match_score(block.text, description)
            if score > 0 and (best is None or score > best[0]):
                best = (score, block)
        if best is None or best[0] < 0.6:
            return None
        score, block = best
        return Element(text=block.text, box=block.box, confidence=score)
