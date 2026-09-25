"""OCR engine abstraction (spec section 5, Phase 3 seam).

`TesseractOcr` reads real screenshots when pytesseract + the Tesseract
binary are installed. `SimulatedOcr` reads the text carried by
:class:`jarvis.control.backends.simulated.SimScreenImage`. `NullOcr`
degrades gracefully (verification then reports UNKNOWN instead of failing).
"""

from __future__ import annotations

import logging
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger("jarvis.ocr")


@dataclass(frozen=True)
class TextBlock:
    """One piece of text located on screen."""

    text: str
    box: tuple[int, int, int, int]  # x, y, w, h
    confidence: float = 1.0


class OcrError(RuntimeError):
    """OCR failed."""


class OcrEngine(ABC):
    @abstractmethod
    def extract_text(self, image: object) -> list[TextBlock]:
        """Extract located text blocks from a screenshot image."""


class NullOcr(OcrEngine):
    """No OCR available: returns nothing (verifier reports UNKNOWN)."""

    available = False

    def extract_text(self, image: object) -> list[TextBlock]:
        return []


class SimulatedOcr(OcrEngine):
    """Reads the text blocks embedded in a SimScreenImage."""

    available = True

    def extract_text(self, image: object) -> list[TextBlock]:
        blocks = getattr(image, "blocks", None)
        if blocks is None:
            return []
        return [
            TextBlock(text=text, box=box, confidence=1.0) for text, box in blocks
        ]


class TesseractOcr(OcrEngine):
    """Real OCR through pytesseract (requires the Tesseract binary)."""

    available = True

    def __init__(self, language: str | None = None) -> None:
        try:
            import pytesseract  # noqa: PLC0415 - optional dependency
        except ImportError as exc:
            raise OcrError(
                "pytesseract is not installed; run pip install 'jarvis[ocr]' "
                "and install the Tesseract binary."
            ) from exc
        if shutil.which("tesseract") is None and not pytesseract.get_tesseract_version():
            raise OcrError("Tesseract binary not found on PATH.")
        self._pytesseract = pytesseract
        self.language = language

    def extract_text(self, image: object) -> list[TextBlock]:
        try:
            data = self._pytesseract.image_to_data(
                image, output_type=self._pytesseract.Output.DICT, lang=self.language
            )
        except Exception as exc:  # pragma: no cover - depends on host
            raise OcrError(f"tesseract failed: {exc}") from exc
        blocks: list[TextBlock] = []
        for i, text in enumerate(data.get("text", [])):
            text = text.strip()
            if not text:
                continue
            try:
                confidence = float(data["conf"][i])
            except (KeyError, TypeError, ValueError):
                confidence = -1.0
            if confidence < 30:
                continue
            blocks.append(
                TextBlock(
                    text=text,
                    box=(data["left"][i], data["top"][i], data["width"][i], data["height"][i]),
                    confidence=confidence / 100.0,
                )
            )
        return blocks


def create_ocr_engine() -> OcrEngine:
    """Best available OCR engine: tesseract when installed, else Null."""
    try:
        engine = TesseractOcr()
        logger.info("OCR engine: tesseract")
        return engine
    except (OcrError, Exception) as exc:  # noqa: BLE001 - degrade gracefully
        logger.info("OCR engine: none (%s) - screen-text checks report UNKNOWN", exc)
        return NullOcr()
