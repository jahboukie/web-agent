import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
from app.core.logging import get_logger
from app.models.execution_plan import AtomicAction, ActionType

logger = get_logger(__name__)


class BaseActionExecutor(ABC):
    """Base class for all action executors."""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, page: Page, action: AtomicAction) -> bool:
        """Execute the action and return success status."""
        pass
    
    async def _find_element(self, page: Page, action: AtomicAction) -> Optional[Locator]:
        """Find element using multiple selector strategies."""
        selectors = []
        
        # Add selectors in order of preference
        if action.target_selector:
            selectors.append(action.target_selector)
        if action.element_css_selector:
            selectors.append(action.element_css_selector)
        if action.element_xpath:
            selectors.append(f"xpath={action.element_xpath}")
        
        # Try text-based selection if available
        if action.element_text_content:
            selectors.append(f"text={action.element_text_content}")
        
        for selector in selectors:
            try:
                element = page.locator(selector)
                # Check if element exists and is visible
                await element.wait_for(state="visible", timeout=5000)
                return element
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Selector failed: {selector}, error: {str(e)}")
                continue
        
        return None
    
    async def _wait_for_element(self, page: Page, action: AtomicAction) -> Optional[Locator]:
        """Wait for element to be available with timeout."""
        element = await self._find_element(page, action)
        if element:
            try:
                # Ensure timeout doesn't exceed 30 seconds for safety
                timeout_ms = min(action.timeout_seconds * 1000, 30000)
                await element.wait_for(state="visible", timeout=timeout_ms)
                return element
            except PlaywrightTimeoutError:
                logger.warning(f"Element not visible within timeout: {action.target_selector}")
                return None
        return None

    async def _validate_element_safety(self, element: Locator, action: AtomicAction) -> bool:
        """Validate element is safe to interact with."""
        try:
            # Check if element is enabled
            is_enabled = await element.is_enabled()
            if not is_enabled:
                logger.warning(f"Element is disabled: {action.target_selector}")
                return False

            # Check if element is visible
            is_visible = await element.is_visible()
            if not is_visible:
                logger.warning(f"Element is not visible: {action.target_selector}")
                return False

            # Check if element is attached to DOM
            try:
                await element.wait_for(state="attached", timeout=1000)
            except PlaywrightTimeoutError:
                logger.warning(f"Element is not attached to DOM: {action.target_selector}")
                return False

            # For input elements, check if they're editable
            if action.action_type in [ActionType.TYPE]:
                is_editable = await element.is_editable()
                if not is_editable:
                    logger.warning(f"Element is not editable: {action.target_selector}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Element safety validation failed: {str(e)}")
            return False

    async def _handle_element_not_found(self, action: AtomicAction) -> bool:
        """Handle graceful degradation when element is not found."""
        # Check if action has fallback selectors
        if hasattr(action, 'fallback_actions') and action.fallback_actions:
            logger.info(f"Element not found, checking fallback options for step {action.step_number}")
            return False  # Let the caller handle fallback logic

        # For non-critical actions, we can continue
        if not action.is_critical:
            logger.info(f"Non-critical element not found, continuing execution: {action.target_selector}")
            return True

        # Critical action failed
        logger.error(f"Critical element not found: {action.target_selector}")
        return False
    
    def _log_action(self, action: AtomicAction, success: bool, details: str = ""):
        """Log action execution."""
        logger.info(
            f"Action {action.action_type.value} executed",
            step_number=action.step_number,
            success=success,
            target=action.target_selector,
            details=details
        )


class ClickExecutor(BaseActionExecutor):
    """Execute click actions on elements."""
    
    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            element = await self._wait_for_element(page, action)
            if not element:
                return await self._handle_element_not_found(action)

            # Validate element safety before clicking
            if not await self._validate_element_safety(element, action):
                self._log_action(action, False, "Element failed safety validation")
                return False

            # Ensure element is clickable and scroll into view
            await element.wait_for(state="visible", timeout=5000)
            await element.scroll_into_view_if_needed()

            # Check if element is still clickable after scrolling
            try:
                # Use a shorter timeout for the actual click to prevent hanging
                await element.click(timeout=min(action.timeout_seconds * 1000, 10000))
            except PlaywrightTimeoutError:
                # Try alternative click methods
                logger.warning(f"Standard click failed, trying force click: {action.target_selector}")
                try:
                    await element.click(force=True, timeout=5000)
                except:
                    # Last resort: JavaScript click
                    await element.evaluate("element => element.click()")

            # Wait for any navigation or changes
            if action.wait_condition:
                await self._handle_wait_condition(page, action.wait_condition)
            else:
                # Default wait for potential page changes
                await asyncio.sleep(1)

            self._log_action(action, True, f"Clicked element: {action.target_selector}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Click failed: {str(e)}")
            return False
    
    async def _handle_wait_condition(self, page: Page, condition: str):
        """Handle post-click wait conditions."""
        try:
            if condition.startswith("url_contains:"):
                expected_url = condition.split(":", 1)[1]
                await page.wait_for_url(f"**/*{expected_url}*", timeout=10000)
            elif condition.startswith("element_visible:"):
                selector = condition.split(":", 1)[1]
                await page.wait_for_selector(selector, state="visible", timeout=10000)
            elif condition.startswith("text_visible:"):
                text = condition.split(":", 1)[1]
                await page.wait_for_selector(f"text={text}", timeout=10000)
            else:
                # Default wait
                await asyncio.sleep(2)
        except PlaywrightTimeoutError:
            logger.warning(f"Wait condition not met: {condition}")


class TypeExecutor(BaseActionExecutor):
    """Execute typing actions in input fields."""
    
    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            element = await self._wait_for_element(page, action)
            if not element:
                return await self._handle_element_not_found(action)

            if not action.input_value:
                self._log_action(action, False, "No input value provided")
                return False

            # Validate element safety
            if not await self._validate_element_safety(element, action):
                self._log_action(action, False, "Element failed safety validation")
                return False

            # Validate input value for safety (basic XSS prevention)
            if self._contains_unsafe_content(action.input_value):
                self._log_action(action, False, "Input value contains potentially unsafe content")
                return False

            # Scroll into view and focus
            await element.scroll_into_view_if_needed()
            await element.click(timeout=5000)  # Focus the element

            # Clear existing content safely
            await element.select_all()
            await element.press("Delete")

            # Type new value with delay for better reliability
            await element.type(action.input_value, delay=50)

            # Verify the value was entered correctly
            entered_value = await element.input_value()
            if entered_value != action.input_value:
                logger.warning(
                    f"Input value mismatch. Expected: '{action.input_value}', Got: '{entered_value}'"
                )
                # Try again with fill method
                await element.fill(action.input_value)

            # Trigger change events
            await element.press("Tab")
            await asyncio.sleep(0.5)  # Allow time for change events

            self._log_action(action, True, f"Typed '{action.input_value}' into {action.target_selector}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Type failed: {str(e)}")
            return False

    def _contains_unsafe_content(self, value: str) -> bool:
        """Check if input value contains potentially unsafe content."""
        unsafe_patterns = [
            '<script', '</script>', 'javascript:', 'data:text/html',
            'vbscript:', 'onload=', 'onerror=', 'onclick='
        ]
        value_lower = value.lower()
        return any(pattern in value_lower for pattern in unsafe_patterns)


class NavigateExecutor(BaseActionExecutor):
    """Execute navigation actions."""
    
    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            if not action.input_value:
                self._log_action(action, False, "No URL provided for navigation")
                return False
            
            # Navigate to URL
            response = await page.goto(
                action.input_value,
                wait_until="domcontentloaded",
                timeout=action.timeout_seconds * 1000
            )
            
            # Check if navigation was successful
            if response and response.status < 400:
                self._log_action(action, True, f"Navigated to {action.input_value}")
                return True
            else:
                self._log_action(action, False, f"Navigation failed with status: {response.status if response else 'unknown'}")
                return False
            
        except Exception as e:
            self._log_action(action, False, f"Navigation failed: {str(e)}")
            return False


class WaitExecutor(BaseActionExecutor):
    """Execute wait actions."""
    
    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            if action.wait_condition:
                # Handle specific wait conditions
                if action.wait_condition.startswith("element_visible:"):
                    selector = action.wait_condition.split(":", 1)[1]
                    await page.wait_for_selector(selector, state="visible", timeout=action.timeout_seconds * 1000)
                elif action.wait_condition.startswith("element_hidden:"):
                    selector = action.wait_condition.split(":", 1)[1]
                    await page.wait_for_selector(selector, state="hidden", timeout=action.timeout_seconds * 1000)
                elif action.wait_condition.startswith("url_contains:"):
                    url_part = action.wait_condition.split(":", 1)[1]
                    await page.wait_for_url(f"**/*{url_part}*", timeout=action.timeout_seconds * 1000)
                elif action.wait_condition.startswith("text_visible:"):
                    text = action.wait_condition.split(":", 1)[1]
                    await page.wait_for_selector(f"text={text}", timeout=action.timeout_seconds * 1000)
                elif action.wait_condition.startswith("seconds:"):
                    seconds = float(action.wait_condition.split(":", 1)[1])
                    await asyncio.sleep(seconds)
                else:
                    # Default wait for load state
                    await page.wait_for_load_state("domcontentloaded", timeout=action.timeout_seconds * 1000)
            else:
                # Default wait time from input_value or 2 seconds
                wait_time = float(action.input_value) if action.input_value else 2.0
                await asyncio.sleep(wait_time)
            
            self._log_action(action, True, f"Wait completed: {action.wait_condition or 'default'}")
            return True
            
        except PlaywrightTimeoutError:
            self._log_action(action, False, f"Wait timeout: {action.wait_condition}")
            return False
        except Exception as e:
            self._log_action(action, False, f"Wait failed: {str(e)}")
            return False


class ScrollExecutor(BaseActionExecutor):
    """Execute scroll actions."""
    
    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            if action.target_selector:
                # Scroll to specific element
                element = await self._wait_for_element(page, action)
                if element:
                    await element.scroll_into_view_if_needed()
                    self._log_action(action, True, f"Scrolled to element: {action.target_selector}")
                    return True
                else:
                    self._log_action(action, False, "Element not found for scrolling")
                    return False
            else:
                # Scroll by amount specified in input_value
                if action.input_value:
                    try:
                        scroll_amount = int(action.input_value)
                        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                        self._log_action(action, True, f"Scrolled by {scroll_amount} pixels")
                        return True
                    except ValueError:
                        self._log_action(action, False, f"Invalid scroll amount: {action.input_value}")
                        return False
                else:
                    # Default scroll to bottom
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    self._log_action(action, True, "Scrolled to bottom of page")
                    return True
            
        except Exception as e:
            self._log_action(action, False, f"Scroll failed: {str(e)}")
            return False


class SelectExecutor(BaseActionExecutor):
    """Execute select actions on dropdown elements."""

    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            element = await self._wait_for_element(page, action)
            if not element:
                self._log_action(action, False, "Select element not found")
                return False

            if not action.input_value:
                self._log_action(action, False, "No option value provided for select")
                return False

            # Try different selection methods
            try:
                # Try by value
                await element.select_option(value=action.input_value)
            except:
                try:
                    # Try by text
                    await element.select_option(label=action.input_value)
                except:
                    # Try by index if it's a number
                    try:
                        index = int(action.input_value)
                        await element.select_option(index=index)
                    except:
                        self._log_action(action, False, f"Could not select option: {action.input_value}")
                        return False

            self._log_action(action, True, f"Selected option '{action.input_value}' in {action.target_selector}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Select failed: {str(e)}")
            return False


class SubmitExecutor(BaseActionExecutor):
    """Execute form submission actions."""

    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            if action.target_selector:
                # Submit specific form or click submit button
                element = await self._wait_for_element(page, action)
                if not element:
                    self._log_action(action, False, "Submit element not found")
                    return False

                # Check if it's a form or button
                tag_name = await element.evaluate("el => el.tagName.toLowerCase()")

                if tag_name == "form":
                    # Submit the form
                    await element.evaluate("form => form.submit()")
                else:
                    # Click the submit button
                    await element.click()
            else:
                # Submit the first form on the page
                await page.evaluate("document.forms[0].submit()")

            # Wait for navigation or response
            await asyncio.sleep(2)

            self._log_action(action, True, f"Form submitted: {action.target_selector or 'first form'}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Submit failed: {str(e)}")
            return False


class ScreenshotExecutor(BaseActionExecutor):
    """Execute screenshot actions."""

    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            from pathlib import Path
            from app.core.config import settings

            # Create screenshot filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"action_screenshot_{action.step_number}_{timestamp}.png"

            screenshot_dir = Path(settings.SCREENSHOT_DIR)
            screenshot_dir.mkdir(exist_ok=True)
            filepath = screenshot_dir / filename

            # Take screenshot
            if action.target_selector:
                # Screenshot of specific element
                element = await self._wait_for_element(page, action)
                if element:
                    await element.screenshot(path=str(filepath))
                else:
                    # Fallback to full page
                    await page.screenshot(path=str(filepath), full_page=True)
            else:
                # Full page screenshot
                await page.screenshot(path=str(filepath), full_page=True)

            self._log_action(action, True, f"Screenshot saved: {filename}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Screenshot failed: {str(e)}")
            return False


class HoverExecutor(BaseActionExecutor):
    """Execute hover actions on elements."""

    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            element = await self._wait_for_element(page, action)
            if not element:
                self._log_action(action, False, "Element not found for hover")
                return False

            # Scroll element into view and hover
            await element.scroll_into_view_if_needed()
            await element.hover()

            # Wait for any hover effects
            await asyncio.sleep(1)

            self._log_action(action, True, f"Hovered over element: {action.target_selector}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Hover failed: {str(e)}")
            return False


class KeyPressExecutor(BaseActionExecutor):
    """Execute key press actions."""

    async def execute(self, page: Page, action: AtomicAction) -> bool:
        try:
            if not action.input_value:
                self._log_action(action, False, "No key specified for key press")
                return False

            if action.target_selector:
                # Press key on specific element
                element = await self._wait_for_element(page, action)
                if not element:
                    self._log_action(action, False, "Element not found for key press")
                    return False

                await element.focus()
                await element.press(action.input_value)
            else:
                # Press key on page
                await page.keyboard.press(action.input_value)

            self._log_action(action, True, f"Pressed key '{action.input_value}' on {action.target_selector or 'page'}")
            return True

        except Exception as e:
            self._log_action(action, False, f"Key press failed: {str(e)}")
            return False
