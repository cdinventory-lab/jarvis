"""Mouse controller (spec section 6).

Low-level operations plus semantic actions that use screen perception to
locate elements instead of fixed coordinates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from jarvis.control.backend import BackendError, ComputerBackend

if TYPE_CHECKING:
    from jarvis.perception.screenshot.service import ComputerVision, Element


class MouseController:
    """High-level mouse control over any backend."""

    def __init__(self, backend: ComputerBackend) -> None:
        self.backend = backend

    # -------------------------------------------------------------- primitives

    def position(self) -> tuple[int, int]:
        return self.backend.mouse_position()

    def move(self, x: int, y: int, duration: float = 0.2) -> None:
        """Move the cursor to absolute coordinates."""
        self.backend.move_to(int(x), int(y), duration=duration)

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.05,
    ) -> None:
        if button not in {"left", "middle", "right"}:
            raise ValueError(f"invalid mouse button {button!r}")
        self.backend.click(x=x, y=y, button=button, clicks=clicks, interval=interval)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        self.click(x=x, y=y, clicks=2)

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        self.click(x=x, y=y, button="right")

    def mouse_down(self, button: str = "left") -> None:
        self.backend.mouse_down(button=button)

    def mouse_up(self, button: str = "left") -> None:
        self.backend.mouse_up(button=button)

    def drag(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float = 0.4,
        button: str = "left",
    ) -> None:
        self.backend.drag(
            int(start[0]), int(start[1]), int(end[0]), int(end[1]),
            duration=duration, button=button,
        )

    def scroll(self, amount: int) -> None:
        """Scroll by `amount` 'clicks' (positive = up, negative = down)."""
        self.backend.scroll(int(amount))

    def scroll_down(self, amount: int = 3) -> None:
        self.scroll(-abs(amount))

    def scroll_up(self, amount: int = 3) -> None:
        self.scroll(abs(amount))

    # ---------------------------------------------------------------- semantic

    def click_element(
        self,
        description: str,
        vision: ComputerVision,
        button: str = "left",
    ) -> Element:
        """Visually locate an element by description and click its centre.

        Raises BackendError if the element cannot be found on screen, so the
        orchestrator can re-plan instead of clicking blind.
        """
        element = vision.find_element(description)
        if element is None:
            raise BackendError(f"could not find {description!r} on screen")
        centre_x = element.box[0] + element.box[2] // 2
        centre_y = element.box[1] + element.box[3] // 2
        self.click(x=centre_x, y=centre_y, button=button)
        return element
