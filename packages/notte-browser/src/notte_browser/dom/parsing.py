from pathlib import Path
from typing import Any

from loguru import logger
from notte_core.browser.dom_tree import DomErrorBuffer
from notte_core.browser.dom_tree import DomNode as NotteDomNode
from notte_core.common.config import config
from notte_core.errors.processing import SnapshotProcessingError
from notte_core.profiling import profiler
from typing_extensions import TypedDict

from notte_browser.dom.csspaths import build_csspath
from notte_browser.dom.id_generation import generate_sequential_ids
from notte_browser.dom.types import DOMBaseNode, DOMElementNode, DOMTextNode
from notte_browser.playwright_async_api import Page

DOM_TREE_JS_PATH = Path(__file__).parent / "buildDomNode.js"
HANDLE_LIST_JS_PATH = Path(__file__).parent / "buildHandleList.js"


class DomTreeDict(TypedDict):
    type: str
    text: str
    tagName: str | None
    xpath: str | None
    attributes: dict[str, str]
    isVisible: bool
    isInteractive: bool
    isTopElement: bool
    isEditable: bool
    highlightIndex: int | None
    shadowRoot: bool
    children: list["DomTreeDict"]
    bbox: dict[str, float] | None
    playwright_selector: str | None
    python_selector: str | None


class ParseDomTreePipe:
    @profiler.profiled("domforward")
    @staticmethod
    async def forward(page: Page) -> NotteDomNode:
        dom_tree = await ParseDomTreePipe.parse_dom_tree(page)
        dom_tree = generate_sequential_ids(dom_tree)
        notte_dom_tree = dom_tree.to_notte_domnode()
        DomErrorBuffer.flush()
        return notte_dom_tree

    @profiler.profiled()
    @staticmethod
    async def parse_dom_tree(page: Page) -> DOMBaseNode:
        js_code = DOM_TREE_JS_PATH.read_text()
        handle_js_code = HANDLE_LIST_JS_PATH.read_text()
        dom_config: dict[str, bool | int] = {
            "highlight_elements": config.highlight_elements,
            "focus_element": config.focus_element,
            "viewport_expansion": config.viewport_expansion,
            "enable_pointer_elements": config.enable_pointer_elements,
        }
        if config.verbose:
            logger.trace(f"Parsing DOM tree for {page.url} with config: {dom_config}")
        page_eval: dict[str, Any] | None = await profiler.profiled()(page.evaluate)(js_code, dom_config)
        handle_page_eval = await page.evaluate_handle(handle_js_code, dom_config)
        locators: list[tuple[str, str]] | None = await handle_page_eval.generate_locators()  # type: ignore
        if locators is None:
            raise SnapshotProcessingError(page.url, "Failed to generate locators")
        if page_eval is None:
            raise SnapshotProcessingError(page.url, "Failed to parse HTML to dictionary")
        # update page_eval with locators
        for node_data in page_eval["map"].values():
            if "highlightIndex" in node_data:
                internal_selector, python_selector = locators[node_data["highlightIndex"]]  # type: ignore
                node_data["playwright_selector"] = internal_selector
                node_data["python_selector"] = python_selector
        # interactive element
        node = await ParseDomTreePipe._reconstruct_dom_tree(page_eval)
        parsed = ParseDomTreePipe._parse_node(
            node,
            parent=None,
            in_iframe=False,
            in_shadow_root=False,
            iframe_parent_css_paths=[],
            notte_selector=page.url,
            parent_playwright_selector=None,
        )
        if parsed is None:
            raise SnapshotProcessingError(page.url, f"Failed to parse DOM tree. Dom Tree is empty. {node}")
        return parsed

    @staticmethod
    def _parse_node(
        node: DomTreeDict,
        parent: "DOMElementNode | None",
        in_iframe: bool,
        in_shadow_root: bool,
        iframe_parent_css_paths: list[str],
        notte_selector: str,
        parent_playwright_selector: str | None,
    ) -> DOMBaseNode | None:
        if node.get("type") == "TEXT_NODE":
            text_node = DOMTextNode(
                text=node["text"],
                is_visible=node["isVisible"],
                parent=parent,
            )

            return text_node

        tag_name = node["tagName"]
        attrs = node.get("attributes", {})
        xpath = node["xpath"]
        playwright_selector = node.get("playwright_selector")
        python_selector = node.get("python_selector")
        highlight_index = node.get("highlightIndex")

        if tag_name is None:
            if xpath is None and len(attrs) == 0 and len(node.get("children", [])) == 0:
                return None
            raise ValueError(f"Tag name is None for node: {node}")

        highlight_index = node.get("highlightIndex")
        shadow_root = node.get("shadowRoot", False)
        if xpath is None:
            raise ValueError(f"XPath is None for node: {node}")
        if highlight_index is not None and playwright_selector is None:
            raise ValueError(f"Playwright selector is None for node: {node} (highlight_index: {highlight_index})")
        if highlight_index is not None and python_selector is None:
            raise ValueError(f"Python selector is None for node: {node} (highlight_index: {highlight_index})")
        # extra check for interactive elements => disable interactive elements if paranet playwright selector is the same as the current one
        if highlight_index is not None and parent_playwright_selector is not None:
            if parent_playwright_selector == playwright_selector:
                highlight_index = None
                python_selector = None
                playwright_selector = None

        css_path = build_csspath(
            tag_name=tag_name,
            xpath=xpath,
            attributes=attrs,
            highlight_index=highlight_index,
        )
        _iframe_parent_css_paths = iframe_parent_css_paths
        notte_selector = ":".join([notte_selector, str(hash(xpath)), str(hash(css_path))])

        if shadow_root:
            in_shadow_root = True

        if tag_name.lower() == "iframe":
            in_iframe = True
            _iframe_parent_css_paths = _iframe_parent_css_paths + [css_path]

        element_node = DOMElementNode(
            tag_name=tag_name,
            in_iframe=in_iframe,
            xpath=xpath,
            css_path=css_path,
            notte_selector=notte_selector,
            iframe_parent_css_selectors=iframe_parent_css_paths,
            attributes=attrs,
            is_visible=node.get("isVisible", False),
            is_interactive=node.get("isInteractive", False),
            is_top_element=node.get("isTopElement", False),
            is_editable=node.get("isEditable", False),
            highlight_index=highlight_index,
            bbox=node.get("bbox"),
            shadow_root=shadow_root,
            in_shadow_root=in_shadow_root,
            parent=parent,
            playwright_selector=playwright_selector,
            python_selector=python_selector,
        )

        children: list[DOMBaseNode] = []
        for child in node.get("children", []):
            if child is not None:
                child_node = ParseDomTreePipe._parse_node(
                    node=child,
                    parent=element_node,
                    in_iframe=in_iframe,
                    iframe_parent_css_paths=_iframe_parent_css_paths,
                    notte_selector=notte_selector,
                    in_shadow_root=in_shadow_root,
                    parent_playwright_selector=parent_playwright_selector or playwright_selector,
                )
                if child_node is not None:
                    children.append(child_node)

        element_node.children = children

        return element_node

    @staticmethod
    async def _reconstruct_dom_tree(
        eval_page: dict[str, Any],
    ) -> DomTreeDict:
        js_node_map = eval_page["map"]
        js_root_id = eval_page["rootId"]

        def rebuild_dom_tree(node_data: dict[str, Any]):
            children_ids = node_data.get("children", [])
            children = [js_node_map[child_id] for child_id in children_ids if child_id in js_node_map]
            node_data["children"] = children

            for child in children:
                _ = rebuild_dom_tree(child)

        root = js_node_map[js_root_id]
        rebuild_dom_tree(root)

        return root


dom_tree_parsers = dict(
    default=ParseDomTreePipe,
)
