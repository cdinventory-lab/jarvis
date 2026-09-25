"""Perception layer: screenshots, OCR, screen understanding."""

from jarvis.perception.ocr import (
    NullOcr,
    OcrEngine,
    OcrError,
    SimulatedOcr,
    TesseractOcr,
    TextBlock,
    create_ocr_engine,
)
from jarvis.perception.screenshot import ComputerVision, Element, ScreenAnalysis

__all__ = [
    "ComputerVision",
    "Element",
    "NullOcr",
    "OcrEngine",
    "OcrError",
    "ScreenAnalysis",
    "SimulatedOcr",
    "TesseractOcr",
    "TextBlock",
    "create_ocr_engine",
]
