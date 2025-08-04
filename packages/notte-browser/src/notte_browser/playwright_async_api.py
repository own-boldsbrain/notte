from loguru import logger

try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        CDPSession,
        ConsoleMessage,
        Error,
        FrameLocator,
        Locator,
        Page,
        Playwright,
        TimeoutError,
        async_playwright,
    )

    logger.info("⚙️ Prioritized 'playwright' over 'patchright'. Uninstall 'playwright' to default to 'patchright'.")
except ImportError:
    from patchright.async_api import (
        Browser,
        BrowserContext,
        CDPSession,
        ConsoleMessage,
        Error,
        FrameLocator,
        Locator,
        Page,
        Playwright,
        TimeoutError,
        async_playwright,
    )


def getPlaywrightOrPatchrightTimeoutError() -> tuple[type[Exception], type[Exception]] | type[Exception]:
    errors: list[type[Exception]] = []
    try:
        from patchright.async_api import TimeoutError as _PatchrightTimeoutError

        errors.append(_PatchrightTimeoutError)
    except ImportError:
        pass
    try:
        from playwright.async_api import TimeoutError as _PlaywrightTimeoutError

        errors.append(_PlaywrightTimeoutError)
    except ImportError:
        pass
    if len(errors) == 1:
        return errors[0]
    elif len(errors) == 2:
        return errors[0], errors[1]
    else:
        raise RuntimeError("Unexpected number of errors")


def getPlaywrightOrPatchrightError() -> tuple[type[Exception], type[Exception]] | type[Exception]:
    errors: list[type[Exception]] = []
    try:
        from patchright.async_api import Error as _PatchrightError

        errors.append(_PatchrightError)
    except ImportError:
        pass
    try:
        from playwright.async_api import Error as _PlaywrightError

        errors.append(_PlaywrightError)
    except ImportError:
        pass
    if len(errors) == 1:
        return errors[0]
    elif len(errors) == 2:
        return errors[0], errors[1]
    else:
        raise RuntimeError("Unexpected number of errors")


__all__ = [
    "Browser",
    "BrowserContext",
    "Playwright",
    "async_playwright",
    "TimeoutError",
    "Error",
    "Locator",
    "Page",
    "CDPSession",
    "FrameLocator",
    "ConsoleMessage",
]
