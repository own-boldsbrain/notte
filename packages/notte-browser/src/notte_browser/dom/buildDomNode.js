// file taken from: https://github.com/browser-use/browser-use/blob/main/browser_use/dom/buildDomTree.js
(
	{ highlight_elements, focus_element, viewport_expansion }
) => {

	function hashString(str) {
		let hash = 0;
		for (let i = 0; i < str.length; i++) {
			hash = (hash << 5) - hash + str.charCodeAt(i);
		}
		return hash;
	}

	class IdGenerator {
		constructor() {
			this.link_counter = 0;
			this.button_counter = 0;
			this.input_counter = 0;
			this.image_counter = 0;
			this.other_counter = 0;
			this.total_counter = 0;
		}

		isInteractive(node) {
			return node.isInteractive && node.isVisible && node.isTopElement;
		}

		generateNextId(node) {
			if (!this.isInteractive(node)) {
				throw new Error("Node is not interactive");
			}
			this.total_counter += 1;
			switch (node.tagName.toLowerCase(), node.role) {
				case 'a':
					this.link_counter += 1;
					return `L${this.link_counter}`;
				case 'button':
				case 'menuitem':
				case 'menuitemcheckbox':
				case 'menuitemradio':
				case 'menu':
				case 'menubar':
				case 'radiogroup':
				case 'tablist':
					this.button_counter += 1;
					return `B${this.button_counter}`;
				case 'input':
				case 'textarea':
				case 'select':
				case 'option':
				case 'optgroup':
				case 'fieldset':
				case 'legend':
				case 'datalist':
					this.input_counter += 1;
					return `I${this.input_counter}`;
				case 'img':
				case 'figure':
				case 'image':
					this.image_counter += 1;
					return `F${this.image_counter}`;
				default:
					this.other_counter += 1;
					return `O${this.other_counter}`;
			}
		}
	}

	function highlightElement(element, index, parentIframe = null) {
		// Create or get highlight container
		let container = document.getElementById('playwright-highlight-container');
		if (!container) {
			container = document.createElement('div');
			container.id = 'playwright-highlight-container';
			container.style.position = 'absolute';
			container.style.pointerEvents = 'none';
			container.style.top = '0';
			container.style.left = '0';
			container.style.width = '100%';
			container.style.height = '100%';
			container.style.zIndex = '2147483647'; // Maximum z-index value
			document.body.appendChild(container);
		}

		// Generate a color based on the index
		const colors = [
			'#FF0000', '#00FF00', '#0000FF', '#FFA500',
			'#800080', '#008080', '#FF69B4', '#4B0082',
			'#FF4500', '#2E8B57', '#DC143C', '#4682B4'
		];
		const colorIndex = hashString(index) % colors.length;
		const baseColor = colors[colorIndex];
		const backgroundColor = `${baseColor}1A`; // 10% opacity version of the color

		// Create highlight overlay
		const overlay = document.createElement('div');
		overlay.style.position = 'absolute';
		overlay.style.border = `2px solid ${baseColor}`;
		overlay.style.backgroundColor = backgroundColor;
		overlay.style.pointerEvents = 'none';
		overlay.style.boxSizing = 'border-box';

		// Position overlay based on element, including scroll position
		const rect = element.getBoundingClientRect();
		let top = rect.top + window.scrollY;
		let left = rect.left + window.scrollX;

		// Adjust position if element is inside an iframe
		if (parentIframe) {
			const iframeRect = parentIframe.getBoundingClientRect();
			top += iframeRect.top;
			left += iframeRect.left;
		}

		overlay.style.top = `${top}px`;
		overlay.style.left = `${left}px`;
		overlay.style.width = `${rect.width}px`;
		overlay.style.height = `${rect.height}px`;

		// Create label
		const label = document.createElement('div');
		label.className = 'playwright-highlight-label';
		label.style.position = 'absolute';
		label.style.background = baseColor;
		label.style.color = 'white';
		label.style.padding = '1px 4px';
		label.style.borderRadius = '4px';
		label.style.fontSize = `${Math.min(12, Math.max(8, rect.height / 2))}px`; // Responsive font size
		label.textContent = index;

		// Calculate label position
		const labelWidth = 20; // Approximate width
		const labelHeight = 16; // Approximate height

		// Default position (top-right corner inside the box)
		let labelTop = top + 2;
		let labelLeft = left + rect.width - labelWidth - 2;

		// Adjust if box is too small
		if (rect.width < labelWidth + 4 || rect.height < labelHeight + 4) {
			// Position outside the box if it's too small
			labelTop = top - labelHeight - 2;
			labelLeft = left + rect.width - labelWidth;
		}


		label.style.top = `${labelTop}px`;
		label.style.left = `${labelLeft}px`;

		// Add to container
		container.appendChild(overlay);
		container.appendChild(label);

		// Store reference for cleanup
		element.setAttribute('browser-user-highlight-id', `playwright-highlight-${index}`);

		return index + 1;
	}


	// Helper function to generate XPath as a tree
	function getXPathTree(element, stopAtBoundary = true) {
		const segments = [];
		let currentElement = element;

		while (currentElement && currentElement.nodeType === Node.ELEMENT_NODE) {
			// Stop if we hit a shadow root or iframe
			if (stopAtBoundary && (currentElement.parentNode instanceof ShadowRoot || currentElement.parentNode instanceof HTMLIFrameElement)) {
				break;
			}

			let index = 0;
			let sibling = currentElement.previousSibling;
			while (sibling) {
				if (sibling.nodeType === Node.ELEMENT_NODE &&
					sibling.nodeName === currentElement.nodeName) {
					index++;
				}
				sibling = sibling.previousSibling;
			}
			// should also iteratate over the next siblings look if there is a next sibling with the same tag name
			let moreSiblings = false;
			let nextSibling = currentElement.nextSibling;
			while (nextSibling) {
				if (nextSibling.nodeType === Node.ELEMENT_NODE &&
					nextSibling.nodeName === currentElement.nodeName) {
					moreSiblings = true;
				}
				nextSibling = nextSibling.nextSibling;
			}

			const tagName = currentElement.nodeName.toLowerCase();
			const xpathIndex = (index > 0 || moreSiblings) ? `[${index + 1}]` : '';
			segments.unshift(`${tagName}${xpathIndex}`);

			currentElement = currentElement.parentNode;
		}

		return segments.join('/');
	}

	// Helper function to check if element is accepted
	function isElementAccepted(element) {
		const leafElementDenyList = new Set(['svg', 'script', 'style', 'link', 'meta']);
		return !leafElementDenyList.has(element.tagName.toLowerCase());
	}


	// Add isEditable check
	function isEditableElement(element) {
		// Check if element is disabled
		if (element.disabled || element.getAttribute('aria-disabled') === 'true') {
			return false;
		}

		// Check for readonly attribute
		const isReadonly = element.hasAttribute('readonly') ||
			element.getAttribute('aria-readonly') === 'true';

		// For select, input, and textarea, check readonly attribute
		if (element.tagName.toLowerCase() in { 'select': 1, 'input': 1, 'textarea': 1 }) {
			return !isReadonly;
		}

		// Check contenteditable
		if (element.hasAttribute('contenteditable') &&
			element.getAttribute('contenteditable') !== 'false') {
			return !isReadonly;
		}

		return false;
	}

	// Helper function to check if element is interactive
	function isInteractiveElement(element) {
		// Base interactive elements and roles

		const interactiveElements = new Set([
			"a",          // Links
			"button",     // Buttons
			"input",      // All input types (text, checkbox, radio, etc.)
			"select",     // Dropdown menus
			"textarea",   // Text areas
			"details",    // Expandable details
			"summary",    // Summary element (clickable part of details)
			"label",      // Form labels (often clickable)
			"option",     // Select options
			"optgroup",   // Option groups
			"fieldset",   // Form fieldsets (can be interactive with legend)
			"legend",     // Fieldset legends
			"embed",
			"menu",
			"menuitem",
			"object"
		]);

		const interactiveRoles = new Set([
			'button', 'menu', 'menuitem', 'link', 'checkbox', 'radio',
			'slider', 'tab', 'tabpanel', 'textbox', 'combobox', 'grid',
			'listbox', 'option', 'progressbar', 'scrollbar', 'searchbox',
			'switch', 'tree', 'treeitem', 'spinbutton', 'tooltip', 'a-button-inner', 'a-dropdown-button', 'click',
			'menuitemcheckbox', 'menuitemradio', 'a-button-text', 'button-text', 'button-icon', 'button-icon-only', 'button-text-icon-only', 'dropdown', 'combobox'
		]);

		// Define explicit disable attributes and properties
		const explicitDisableTags = new Set([
			'disabled',           // Standard disabled attribute
			// 'aria-disabled',      // ARIA disabled state
			'readonly',          // Read-only state
			// 'aria-readonly',     // ARIA read-only state
			// 'aria-hidden',       // Hidden from accessibility
			// 'hidden',            // Hidden attribute
			// 'inert',             // Inert attribute
			// 'aria-inert',        // ARIA inert state
			// 'tabindex="-1"',     // Removed from tab order
			// 'aria-hidden="true"' // Hidden from screen readers
		]);

		// Define interactive cursors
		const interactiveCursors = new Set([
			'pointer',    // Link/clickable elements
			'move',       // Movable elements
			'text',       // Text selection
			'grab',       // Grabbable elements
			'grabbing',   // Currently grabbing
			'cell',       // Table cell selection
			'copy',       // Copy operation
			'alias',      // Alias creation
			'all-scroll', // Scrollable content
			'col-resize', // Column resize
			'context-menu', // Context menu available
			'crosshair',  // Precise selection
			'e-resize',   // East resize
			'ew-resize',  // East-west resize
			'help',       // Help available
			'n-resize',   // North resize
			'ne-resize',  // Northeast resize
			'nesw-resize', // Northeast-southwest resize
			'ns-resize',  // North-south resize
			'nw-resize',  // Northwest resize
			'nwse-resize', // Northwest-southeast resize
			'row-resize', // Row resize
			's-resize',   // South resize
			'se-resize',  // Southeast resize
			'sw-resize',  // Southwest resize
			'vertical-text', // Vertical text selection
			'w-resize',   // West resize
			'zoom-in',    // Zoom in
			'zoom-out'    // Zoom out
		]);

		// Define non-interactive cursors
		const nonInteractiveCursors = new Set([
			'not-allowed', // Action not allowed
			'no-drop',     // Drop not allowed
			'wait',        // Processing
			'progress',    // In progress
			'initial',     // Initial value
			'inherit'      // Inherited value
			//? Let's just include all potentially clickable elements that are not specifically blocked
			// 'none',        // No cursor
			// 'default',     // Default cursor
			// 'auto',        // Browser default
		]);

		const tagName = element.tagName.toLowerCase();
		const role = element.getAttribute('role');
		const ariaRole = element.getAttribute('aria-role');
		const tabIndex = element.getAttribute('tabindex');
		const cursor = element.style.cursor;


		const hasInteractiveCursor = tagName !== "html" && interactiveCursors.has(cursor);

		// Add check for specific class
		const hasAddressInputClass = element.classList.contains('address-input__container__input');

		// Basic role/attribute checks
		const hasInteractiveRole = hasInteractiveCursor ||
			hasAddressInputClass ||
			interactiveElements.has(tagName) ||
			interactiveRoles.has(role) ||
			interactiveRoles.has(ariaRole) ||
			(tabIndex !== null && tabIndex !== '-1') ||
			element.getAttribute('data-action') === 'a-dropdown-select' ||
			element.getAttribute('data-action') === 'a-dropdown-button';

		if (hasInteractiveRole) return true;

		// Get computed style
		const style = window.getComputedStyle(element);

		// Check if element has click-like styling
		// const hasClickStyling = style.cursor === 'pointer' ||
		//     element.style.cursor === 'pointer' ||
		//     style.pointerEvents !== 'none';

		// Check for event listeners
		const hasClickHandler = element.onclick !== null ||
			element.getAttribute('onclick') !== null ||
			element.hasAttribute('ng-click') ||
			element.hasAttribute('@click') ||
			element.hasAttribute('v-on:click');

		// Helper function to safely get event listeners
		function getEventListeners(el) {
			try {
				// Try to get listeners using Chrome DevTools API
				return window.getEventListeners?.(el) || {};
			} catch (e) {
				// Fallback: check for common event properties
				const listeners = {};

				// List of common event types to check
				const eventTypes = [
					'click', 'mousedown', 'mouseup',
					'touchstart', 'touchend',
					'keydown', 'keyup', 'focus', 'blur'
				];

				for (const type of eventTypes) {
					const handler = el[`on${type}`];
					if (handler) {
						listeners[type] = [{
							listener: handler,
							useCapture: false
						}];
					}
				}

				return listeners;
			}
		}

		// Check for click-related events on the element itself
		const listeners = getEventListeners(element);
		const hasClickListeners = listeners && (
			listeners.click?.length > 0 ||
			listeners.mousedown?.length > 0 ||
			listeners.mouseup?.length > 0 ||
			listeners.touchstart?.length > 0 ||
			listeners.touchend?.length > 0
		);

		// Check for ARIA properties that suggest interactivity
		const hasAriaProps = element.hasAttribute('aria-expanded') ||
			element.hasAttribute('aria-pressed') ||
			element.hasAttribute('aria-selected') ||
			element.hasAttribute('aria-checked');

		// Check for form-related functionality
		const isFormRelated = element.form !== undefined ||
			element.hasAttribute('contenteditable') ||
			style.userSelect !== 'none';

		// Check if element is draggable
		const isDraggable = element.draggable ||
			element.getAttribute('draggable') === 'true';

		return hasAriaProps ||
			// hasClickStyling ||
			hasClickHandler ||
			hasClickListeners ||
			// isFormRelated ||
			isDraggable;

	}

	// Helper function to check if element is visible
	function isElementVisible(element) {
		const style = window.getComputedStyle(element);
		return element.offsetWidth > 0 &&
			element.offsetHeight > 0 &&
			style.visibility !== 'hidden' &&
			style.display !== 'none';
	}

	// Helper function to check if element is the top element at its position
	function isTopElement(element) {
		// Find the correct document context and root element
		let doc = element.ownerDocument;

		// If we're in an iframe, elements are considered top by default
		if (doc !== window.document) {
			return true;
		}

		// For shadow DOM, we need to check within its own root context
		const shadowRoot = element.getRootNode();
		if (shadowRoot instanceof ShadowRoot) {
			const rect = element.getBoundingClientRect();
			const point = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };

			try {
				// Use shadow root's elementFromPoint to check within shadow DOM context
				const topEl = shadowRoot.elementFromPoint(point.x, point.y);
				if (!topEl) return false;

				// Check if the element or any of its parents match our target element
				let current = topEl;
				while (current && current !== shadowRoot) {
					if (current === element) return true;
					current = current.parentElement;
				}
				return false;
			} catch (e) {
				return true; // If we can't determine, consider it visible
			}
		}

		// Regular DOM elements
		const rect = element.getBoundingClientRect();

		// If viewportExpansion is -1, check if element is the top one at its position
		if (viewport_expansion === -1) {
			return true; // Consider all elements as top elements when expansion is -1
		}

		// Calculate expanded viewport boundaries including scroll position
		const scrollX = window.scrollX;
		const scrollY = window.scrollY;
		const viewportTop = -viewport_expansion + scrollY;
		const viewportLeft = -viewport_expansion + scrollX;
		const viewportBottom = window.innerHeight + viewport_expansion + scrollY;
		const viewportRight = window.innerWidth + viewport_expansion + scrollX;

		// Get absolute element position
		const absTop = rect.top + scrollY;
		const absLeft = rect.left + scrollX;
		const absBottom = rect.bottom + scrollY;
		const absRight = rect.right + scrollX;

		// Skip if element is completely outside expanded viewport
		if (absBottom < viewportTop ||
			absTop > viewportBottom ||
			absRight < viewportLeft ||
			absLeft > viewportRight) {
			return false;
		}

		// For elements within expanded viewport, check if they're the top element
		try {
			const centerX = rect.left + rect.width / 2;
			const centerY = rect.top + rect.height / 2;

			// Only clamp the point if it's outside the actual document
			const point = {
				x: centerX,
				y: centerY
			};

			if (point.x < 0 || point.x >= window.innerWidth ||
				point.y < 0 || point.y >= window.innerHeight) {
				return false; // Consider elements with center outside viewport as visible
			}

			const topEl = document.elementFromPoint(point.x, point.y);
			if (!topEl) return false;

			let current = topEl;
			while (current && current !== document.documentElement) {
				if (current === element) return true;
				current = current.parentElement;
			}
			return false;
		} catch (e) {
			return true;
		}
	}

	// Helper function to check if text node is visible
	function isTextNodeVisible(textNode) {
		const range = document.createRange();
		range.selectNodeContents(textNode);
		const rect = range.getBoundingClientRect();

		return rect.width !== 0 &&
			rect.height !== 0 &&
			rect.top >= 0 &&
			rect.top <= window.innerHeight &&
			textNode.parentElement?.checkVisibility({
				checkOpacity: true,
				checkVisibilityCSS: true
			});
	}


	// Function to traverse the DOM and create nested JSON
	function buildDomTree(node, parentIframe = null) {
		if (!node) return null;

		// Special case for text nodes
		if (node.nodeType === Node.TEXT_NODE) {
			const textContent = node.textContent.trim();
			if (textContent && isTextNodeVisible(node)) {
				return {
					type: "TEXT_NODE",
					text: textContent,
					isVisible: true,
				};
			}
			return null;
		}

		// Check if element is accepted
		if (node.nodeType === Node.ELEMENT_NODE && !isElementAccepted(node)) {
			return null;
		}

		const nodeData = {
			tagName: node.tagName ? node.tagName.toLowerCase() : null,
			attributes: {},
			xpath: node.nodeType === Node.ELEMENT_NODE ? getXPathTree(node, true) : null,
			children: [],
		};

		// Copy all attributes if the node is an element
		if (node.nodeType === Node.ELEMENT_NODE && node.attributes) {
			// Use getAttributeNames() instead of directly iterating attributes
			const attributeNames = node.getAttributeNames?.() || [];
			for (const name of attributeNames) {
				nodeData.attributes[name] = node.getAttribute(name);
			}
		}

		if (node.nodeType === Node.ELEMENT_NODE) {
			const isInteractive = isInteractiveElement(node);
			const isVisible = isElementVisible(node);
			const isTop = isTopElement(node);
			const isEditable = isEditableElement(node);

			nodeData.isInteractive = isInteractive;
			nodeData.isVisible = isVisible;
			nodeData.isTopElement = isTop;
			nodeData.isEditable = isEditable;

			// Highlight if element meets all criteria and highlighting is enabled
			if (idGenerator.isInteractive(nodeData)) {
				nodeData.interactiveId = idGenerator.generateNextId(nodeData);
				if (highlight_elements) {
					if (focus_element >= 0) {
						if (focus_element === nodeData.interactiveId) {
							highlightElement(node, nodeData.interactiveId, parentIframe);
						}
					} else {
						highlightElement(node, nodeData.interactiveId, parentIframe);
					}
				}
			}
		}

		// Only add iframeContext if we're inside an iframe
		// if (parentIframe) {
		//     nodeData.iframeContext = `iframe[src="${parentIframe.src || ''}"]`;
		// }

		// Only add shadowRoot field if it exists
		if (node.shadowRoot) {
			nodeData.shadowRoot = true;
		}

		// Handle shadow DOM
		if (node.shadowRoot) {
			const shadowChildren = Array.from(node.shadowRoot.childNodes).map(child =>
				buildDomTree(child, parentIframe)
			);
			nodeData.children.push(...shadowChildren);
		}

		// Handle iframes
		if (node.tagName === 'IFRAME') {
			try {
				const iframeDoc = node.contentDocument || node.contentWindow.document;
				if (iframeDoc) {
					const iframeChildren = Array.from(iframeDoc.body.childNodes).map(child =>
						buildDomTree(child, node)
					);
					nodeData.children.push(...iframeChildren);
				}
			} catch (e) {
				console.warn('Unable to access iframe:', node);
			}
		} else {
			const children = Array.from(node.childNodes).map(child =>
				buildDomTree(child, parentIframe)
			);
			nodeData.children.push(...children);
		}

		return nodeData;
	}
	const idGenerator = new IdGenerator();
	return buildDomTree(document.body);
}
