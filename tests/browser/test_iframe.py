import difflib
import json
from pathlib import Path
from typing import TypeAlias
from unittest import TestCase

import pytest
from loguru import logger
from notte_browser.dom.parsing import DomParsingConfig, DomTreeDict, ParseDomTreePipe
from notte_browser.dom.types import DOMBaseNode
from notte_browser.session import NotteSession, NotteSessionConfig
from notte_core.errors.processing import SnapshotProcessingError
from patchright.async_api import Page

from tests.mock.mock_service import MockLLMService

DomDict: TypeAlias = dict[str, str]


def node_to_dict(node: DOMBaseNode, max_depth: int = 4) -> DomDict:
    if max_depth <= 0:
        return {}

    if node.role.lower() == "iframe":
        print(node.name, node.children[:1])

    curr = {"name": node.name, "role": node.role}
    curr["children"] = [node_to_dict(child, max_depth - 1) for child in node.children]  # pyright: ignore[reportArgumentType]
    return curr


async def old_parse_dom_tree(page: Page, config: DomParsingConfig) -> DOMBaseNode:
    js_code = Path("tests/browser/oldBuildDom.js").read_text()

    if config.verbose:
        logger.info(f"Parsing DOM tree for {page.url} with config: {config.model_dump()}")
    node: DomTreeDict | None = await page.evaluate(js_code, config.model_dump())
    if node is None:
        raise SnapshotProcessingError(page.url, "Failed to parse HTML to dictionary")
    parsed = ParseDomTreePipe._parse_node(
        node,
        parent=None,
        in_iframe=False,
        in_shadow_root=False,
        iframe_parent_css_paths=[],
        notte_selector=page.url,
    )
    if parsed is None:
        raise SnapshotProcessingError(page.url, f"Failed to parse DOM tree. Dom Tree is empty. {node}")
    return parsed


async def get_parsed_nodes(website_url: str) -> tuple[DomDict, DomDict]:
    config = DomParsingConfig()
    # start browser with disabled web security, old parse dom tree
    old_session = NotteSession(
        config=NotteSessionConfig().disable_perception().headless().disable_web_security(),
        llmserve=MockLLMService(mock_response=""),
    )

    async with old_session as sesh:
        _ = await sesh.goto(website_url)
        await sesh.window.long_wait()
        old_res = node_to_dict(await old_parse_dom_tree(sesh.window.page, config))
        # dom_content = await sesh.window.page.locator("html").inner_html()  # Recommended!
        new_res = node_to_dict(await ParseDomTreePipe.parse_dom_tree(sesh.window.page, config))

    # start browser with enabled web security, new parse dom tree
    # new_session = NotteSession(
    #     config=NotteSessionConfig().disable_perception().headless().enable_web_security(),
    #     llmserve=MockLLMService(mock_response=""),
    # )
    #
    # async with new_session as sesh:
    #     _ = await sesh.goto(website_url)
    #     # await sesh.window.page.evaluate(f"""() => {{
    #     #     document.documentElement.innerHTML = `{dom_content}`;
    #     # }}""")
    #     new_res = node_to_dict(await ParseDomTreePipe.parse_dom_tree(sesh.window.page, config))
    #
    return old_res, new_res


@pytest.mark.asyncio
async def test_same_parsed_nodes():
    # old_res, new_res = await get_parsed_nodes("https://www.bbc.com/news")
    old_res, new_res = await get_parsed_nodes("https://www.allrecipes.com")
    d1 = json.dumps(old_res, indent=1)
    d2 = json.dumps(new_res, indent=1)
    # print("OLD")
    # print(d1)
    # print("\n\nNEW\n\n")
    # print(d2)
    # print("\n\nDIFF\n\n")
    # print(diff_checker(d1, d2))
    # compare results
    TestCase().assertDictEqual(old_res, new_res)


def diff_checker(text1, text2):
    """
    Compares two strings and returns a human-readable difference output similar to diffchecker.

    Args:
      text1: The first string.
      text2: The second string.

    Returns:
      A string representing the differences between the two input strings.
    """

    d = difflib.Differ()
    diff = d.compare(
        text1.splitlines(keepends=True), text2.splitlines(keepends=True)
    )  # Split into lines and keep the newline characters

    result = []
    for line in diff:
        if line.startswith("  "):  # Common line
            result.append("  " + line[2:])  # Keep only the actual content
        elif line.startswith("+ "):  # Added line
            result.append("+ " + line[2:])  # Prefix with '+' and remove ' '
        elif line.startswith("- "):  # Removed line
            result.append("- " + line[2:])  # Prefix with '-' and remove ' '
        elif line.startswith("? "):  # Inline change (ignored for simplicity)
            #  Optional: you could add some more sophisticated handling here if you wanted to highlight parts of lines that are different
            pass  # Skip for now
        else:  # Other codes (e.g., end of file)
            result.append(line)
