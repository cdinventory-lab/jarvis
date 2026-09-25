"""Browser subpackage (spec section 9).

Phase 1 provides URL opening / web search through the OS browser. Phase 2+
adds a structured automation backend (Playwright/CDP) for reliable clicking,
forms and downloads - with visual fallback for stubborn sites. The
`open_url` / `search_web` tools are the stable seam.
"""

from jarvis.control.apps import resolve_app_name


def browser_candidates(name: str = "") -> list[str]:
    """Known browser app names, optionally filtered by user preference."""
    from jarvis.control.apps import APP_REGISTRY

    browsers = [spec.name for spec in APP_REGISTRY.values() if spec.is_browser]
    if name:
        spec = resolve_app_name(name)
        if spec and spec.is_browser:
            return [spec.name] + [b for b in browsers if b != spec.name]
    return browsers
