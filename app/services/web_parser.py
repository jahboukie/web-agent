"""
WebParser Service for semantic webpage analysis and element extraction.

This service provides:
- Async webpage parsing with Playwright
- Semantic element extraction and classification
- Interactive element identification
- Content block analysis
- Screenshot capture
- Progress reporting during parsing
- Error handling and retry logic
"""

import asyncio
import hashlib
import json
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import structlog
from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.browser_pool import browser_pool
from app.services.task_status_service import TaskStatusService
from app.services.webpage_cache_service import webpage_cache_service
from app.schemas.web_page import WebPageParseRequest, WebPageParseResponse
from app.models.task import Task, TaskStatus
from app.core.config import settings

logger = structlog.get_logger(__name__)


class WebParserService:
    """Service for parsing webpages and extracting semantic information."""
    
    def __init__(self):
        self.max_wait_time = getattr(settings, 'PARSER_MAX_WAIT_TIME', 30)
        self.screenshot_quality = getattr(settings, 'SCREENSHOT_QUALITY', 80)
        self.max_elements_per_page = getattr(settings, 'MAX_ELEMENTS_PER_PAGE', 1000)
    
    async def parse_webpage_async(
        self,
        db: AsyncSession,
        task_id: int,
        url: str,
        options: WebPageParseRequest
    ) -> WebPageParseResponse:
        """Main async parsing method for background execution."""

        start_time = datetime.utcnow()
        context = None

        try:
            # Update task status - starting
            await TaskStatusService.mark_task_processing(
                db, task_id, f"webparser-{task_id}"
            )

            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=5,
                current_step="checking_cache"
            )

            # Initialize cache service if needed
            if not webpage_cache_service._initialized:
                await webpage_cache_service.initialize()

            # Check cache first
            cached_result = await webpage_cache_service.get_cached_result(
                url, options.dict()
            )

            if cached_result:
                # Update task with cached result
                cached_result.cache_hit = True

                performance_metrics = {
                    'parsing_duration_seconds': (datetime.utcnow() - start_time).total_seconds(),
                    'cache_hit': True,
                    'elements_extracted': cached_result.web_page.interactive_elements_count,
                    'content_blocks': len(cached_result.web_page.content_blocks)
                }

                # Convert cached result to JSON-serializable dict (HttpUrl -> str)
                cached_result_dict = json.loads(cached_result.json())
                await TaskStatusService.complete_task(db, task_id, cached_result_dict, performance_metrics)

                logger.info(
                    "Webpage parsing completed from cache",
                    task_id=task_id,
                    url=url,
                    cache_key=getattr(cached_result, 'cache_key', 'unknown')
                )

                return cached_result

            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=10,
                current_step="acquiring_browser_context"
            )

            # Acquire browser context with timeout and fallback
            context = None
            use_fallback = False

            try:
                logger.info("🔍 Attempting to acquire browser context from pool", task_id=task_id)
                context = await asyncio.wait_for(
                    browser_pool.acquire_context(task_id),
                    timeout=30.0  # 30 second timeout
                )
                logger.info("✅ Browser context acquired from pool", task_id=task_id)
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("⚠️ Pool acquisition failed, trying direct browser creation", task_id=task_id, error=str(e))
                use_fallback = True

                # Fallback: Create browser context directly
                try:
                    from playwright.async_api import async_playwright

                    logger.info("🔄 Creating direct browser context", task_id=task_id)
                    playwright = await async_playwright().start()
                    browser = await playwright.chromium.launch(headless=True)
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080}
                    )
                    logger.info("✅ Direct browser context created", task_id=task_id)

                    # Store references for cleanup
                    context._playwright = playwright
                    context._browser = browser

                except Exception as fallback_error:
                    logger.error("❌ Direct browser creation also failed", task_id=task_id, error=str(fallback_error))
                    raise Exception(f"Both pool and direct browser creation failed: {str(fallback_error)}")
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=20,
                current_step="navigating_to_page"
            )
            
            # Perform the actual parsing
            result = await self._perform_parsing(context, url, options, task_id, db)

            # Cache the result for future use
            await webpage_cache_service.cache_result(url, result, options.dict())

            # Complete the task
            performance_metrics = {
                'parsing_duration_seconds': (datetime.utcnow() - start_time).total_seconds(),
                'cache_hit': False,
                'elements_extracted': result.web_page.interactive_elements_count,
                'content_blocks': len(result.web_page.content_blocks),
                'screenshot_captured': len(result.screenshots) > 0
            }

            logger.info("🔧 FINALIZATION: Starting finalization step", task_id=task_id)

            # Monitor memory usage
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                logger.info("📊 FINALIZATION: Memory usage", task_id=task_id, memory_mb=round(memory_mb, 2))
            except Exception as mem_error:
                logger.warning("Failed to get memory info", task_id=task_id, error=str(mem_error))

            # Debug: Log the result structure before passing to complete_task
            # Convert to JSON-serializable dict (HttpUrl -> str)
            result_dict = json.loads(result.json())

            logger.info(
                "🔍 FINALIZATION: Result structure before complete_task",
                task_id=task_id,
                result_keys=list(result_dict.keys()),
                has_web_page=('web_page' in result_dict),
                has_processing_time_ms=('processing_time_ms' in result_dict),
                result_type=type(result).__name__,
                result_dict_size=len(str(result_dict)),
                performance_metrics=performance_metrics
            )

            logger.info("🔧 FINALIZATION: About to call complete_task", task_id=task_id)

            try:
                await TaskStatusService.complete_task(db, task_id, result_dict, performance_metrics)
                logger.info("✅ FINALIZATION: complete_task succeeded", task_id=task_id)
            except Exception as e:
                logger.error("❌ FINALIZATION: complete_task failed", task_id=task_id, error=str(e), error_type=type(e).__name__)
                raise

            logger.info(
                "Webpage parsing completed successfully",
                task_id=task_id,
                url=url,
                duration_seconds=performance_metrics['parsing_duration_seconds']
            )

            return result
            
        except Exception as e:
            await TaskStatusService.fail_task(db, task_id, e)
            logger.error("Webpage parsing failed", task_id=task_id, url=url, error=str(e))
            raise
        finally:
            if context:
                if use_fallback:
                    # Cleanup direct browser context
                    try:
                        await context.close()
                        if hasattr(context, '_browser'):
                            await context._browser.close()
                        if hasattr(context, '_playwright'):
                            await context._playwright.stop()
                        logger.info("🧹 Direct browser context cleaned up", task_id=task_id)
                    except Exception as cleanup_error:
                        logger.error("❌ Error cleaning up direct browser context", task_id=task_id, error=str(cleanup_error))
                else:
                    # Release context back to pool
                    await browser_pool.release_context(task_id, context)
    
    async def _perform_parsing(
        self,
        context: BrowserContext,
        url: str,
        options: WebPageParseRequest,
        task_id: int,
        db: AsyncSession
    ) -> WebPageParseResponse:
        """Perform the actual webpage parsing with progress updates."""
        
        parsing_start_time = datetime.utcnow()
        page = await context.new_page()

        try:
            # Navigate to the page
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=30,
                current_step="waiting_for_page_load"
            )
            
            # Wait for additional loading if specified
            if options.wait_for_load and options.wait_for_load > 0:
                await asyncio.sleep(min(options.wait_for_load, 10))  # Cap at 10 seconds
            
            # Wait for network idle if specified
            if options.wait_for_network_idle:
                try:
                    await page.wait_for_load_state('networkidle', timeout=15000)
                except PlaywrightTimeoutError:
                    logger.warning("Network idle timeout", task_id=task_id, url=url)
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=40,
                current_step="extracting_page_metadata"
            )
            
            # Extract page metadata
            metadata = await self._extract_page_metadata(page)
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=50,
                current_step="extracting_interactive_elements"
            )
            
            # Extract interactive elements
            interactive_elements = await self._extract_interactive_elements(page)
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=70,
                current_step="extracting_content_blocks"
            )
            
            # Extract content blocks
            content_blocks = await self._extract_content_blocks(page)
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=80,
                current_step="analyzing_action_capabilities"
            )
            
            # Analyze action capabilities
            action_capabilities = await self._analyze_action_capabilities(
                interactive_elements, metadata
            )
            
            screenshot_path = None
            if options.include_screenshot:
                await TaskStatusService.update_task_progress(
                    db, task_id,
                    progress_percentage=90,
                    current_step="capturing_screenshot"
                )
                screenshot_path = await self._capture_screenshot(page, task_id)
            
            await TaskStatusService.update_task_progress(
                db, task_id,
                progress_percentage=95,
                current_step="finalizing_results"
            )
            
            # Create content hash
            content_hash = self._generate_content_hash(metadata, interactive_elements, content_blocks)

            # Calculate parsing duration
            parsing_duration_ms = int((datetime.utcnow() - parsing_start_time).total_seconds() * 1000)

            # Build the WebPage object
            from app.schemas.web_page import WebPage
            web_page = WebPage(
                id=0,  # Temporary ID for response
                url=url,
                canonical_url=metadata.get('canonical_url', url),
                title=metadata.get('title', ''),
                domain=urlparse(url).netloc,
                content_hash=content_hash,
                interactive_elements_count=len(interactive_elements),
                form_count=metadata.get('form_count', 0),
                link_count=metadata.get('link_count', 0),
                image_count=metadata.get('image_count', 0),
                semantic_data=metadata,
                parsed_at=datetime.utcnow(),
                parsing_duration_ms=parsing_duration_ms,
                success=True,
                interactive_elements=[],  # Will be populated separately if needed
                content_blocks=[],       # Will be populated separately if needed
                action_capabilities=[]   # Will be populated separately if needed
            )

            # Build the response
            response = WebPageParseResponse(
                web_page=web_page,
                processing_time_ms=parsing_duration_ms,
                cache_hit=False,
                screenshots=[screenshot_path] if screenshot_path else [],
                warnings=[],
                errors=[]
            )

            return response
            
        finally:
            await page.close()
    
    async def _extract_page_metadata(self, page: Page) -> Dict[str, Any]:
        """Extract comprehensive page metadata."""
        
        try:
            # Basic page information
            title = await page.title()
            url = page.url
            
            # Extract meta tags
            meta_tags = await page.evaluate("""
                () => {
                    const metas = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        if (name && content) {
                            metas[name] = content;
                        }
                    });
                    return metas;
                }
            """)
            
            # Extract links
            links = await page.evaluate("""
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(link => {
                        links.push({
                            text: link.textContent.trim(),
                            href: link.href,
                            title: link.title || null
                        });
                    });
                    return links.slice(0, 100); // Limit to first 100 links
                }
            """)
            
            # Count various elements
            element_counts = await page.evaluate("""
                () => {
                    return {
                        forms: document.querySelectorAll('form').length,
                        inputs: document.querySelectorAll('input, textarea, select').length,
                        buttons: document.querySelectorAll('button, input[type="submit"], input[type="button"]').length,
                        images: document.querySelectorAll('img').length,
                        links: document.querySelectorAll('a[href]').length,
                        scripts: document.querySelectorAll('script').length
                    };
                }
            """)
            
            # Check for JavaScript frameworks
            frameworks = await page.evaluate("""
                () => {
                    const frameworks = [];
                    if (window.React) frameworks.push('React');
                    if (window.Vue) frameworks.push('Vue');
                    if (window.angular) frameworks.push('Angular');
                    if (window.jQuery || window.$) frameworks.push('jQuery');
                    return frameworks;
                }
            """)
            
            return {
                'title': title,
                'current_url': url,
                'canonical_url': meta_tags.get('canonical', url),
                'description': meta_tags.get('description', ''),
                'keywords': meta_tags.get('keywords', ''),
                'language': meta_tags.get('language', 'en'),
                'viewport': meta_tags.get('viewport', ''),
                'meta_tags': meta_tags,
                'links': links,
                'form_count': element_counts['forms'],
                'input_count': element_counts['inputs'],
                'button_count': element_counts['buttons'],
                'image_count': element_counts['images'],
                'link_count': element_counts['links'],
                'has_javascript': element_counts['scripts'] > 0,
                'javascript_frameworks': frameworks,
                'extracted_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to extract page metadata", error=str(e))
            return {
                'title': '',
                'current_url': page.url,
                'error': str(e),
                'extracted_at': datetime.utcnow().isoformat()
            }

    async def _extract_interactive_elements(self, page: Page) -> List[Dict[str, Any]]:
        """Extract interactive elements from the page."""

        try:
            elements = await page.evaluate("""
                () => {
                    const elements = [];
                    const selectors = [
                        'button',
                        'input',
                        'select',
                        'textarea',
                        'a[href]',
                        '[onclick]',
                        '[role="button"]',
                        '[tabindex]'
                    ];

                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach((el, index) => {
                            const rect = el.getBoundingClientRect();
                            const isVisible = rect.width > 0 && rect.height > 0 &&
                                            window.getComputedStyle(el).visibility !== 'hidden' &&
                                            window.getComputedStyle(el).display !== 'none';

                            if (isVisible) {
                                elements.push({
                                    tag_name: el.tagName.toLowerCase(),
                                    element_type: el.type || 'unknown',
                                    text_content: el.textContent?.trim().substring(0, 200) || '',
                                    placeholder: el.placeholder || null,
                                    value: el.value || null,
                                    aria_label: el.getAttribute('aria-label') || null,
                                    title: el.title || null,
                                    element_id: el.id || null,
                                    element_class: el.className || null,
                                    x_coordinate: Math.round(rect.left),
                                    y_coordinate: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    is_visible: isVisible,
                                    is_enabled: !el.disabled,
                                    href: el.href || null,
                                    form_id: el.form?.id || null,
                                    required: el.required || false,
                                    element_index: index
                                });
                            }
                        });
                    });

                    return elements.slice(0, 1000); // Limit to prevent memory issues
                }
            """)

            # Enhance elements with additional analysis
            enhanced_elements = []
            for element in elements:
                enhanced_element = await self._enhance_element_data(element)
                enhanced_elements.append(enhanced_element)

            return enhanced_elements

        except Exception as e:
            logger.error("Failed to extract interactive elements", error=str(e))
            return []

    async def _enhance_element_data(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance element data with semantic analysis."""

        # Determine semantic role
        semantic_role = self._determine_semantic_role(element)

        # Calculate interaction confidence
        interaction_confidence = self._calculate_interaction_confidence(element)

        # Determine supported interactions
        supported_interactions = self._determine_supported_interactions(element)

        element.update({
            'semantic_role': semantic_role,
            'interaction_confidence': interaction_confidence,
            'supported_interactions': supported_interactions,
            'automation_complexity': self._calculate_automation_complexity(element),
            'discovered_at': datetime.utcnow().isoformat()
        })

        return element

    def _determine_semantic_role(self, element: Dict[str, Any]) -> str:
        """Determine the semantic role of an element."""

        tag = element.get('tag_name', '').lower()
        element_type = element.get('element_type', '').lower()
        text = element.get('text_content', '').lower()
        aria_label = element.get('aria_label', '').lower()

        # Button-like elements
        if tag == 'button' or element_type in ['button', 'submit']:
            if any(word in text or word in aria_label for word in ['submit', 'send', 'save']):
                return 'submit_button'
            elif any(word in text or word in aria_label for word in ['cancel', 'close', 'back']):
                return 'cancel_button'
            elif any(word in text or word in aria_label for word in ['search', 'find']):
                return 'search_button'
            return 'action_button'

        # Input elements
        if tag == 'input':
            if element_type in ['email', 'text'] and any(word in text or word in aria_label for word in ['email', 'mail']):
                return 'email_input'
            elif element_type == 'password':
                return 'password_input'
            elif element_type in ['text', 'search'] and any(word in text or word in aria_label for word in ['search', 'query']):
                return 'search_input'
            elif element_type == 'checkbox':
                return 'checkbox'
            elif element_type == 'radio':
                return 'radio_button'
            return 'text_input'

        # Links
        if tag == 'a':
            return 'navigation_link'

        # Select elements
        if tag == 'select':
            return 'dropdown'

        # Textarea
        if tag == 'textarea':
            return 'text_area'

        return 'interactive_element'

    def _calculate_interaction_confidence(self, element: Dict[str, Any]) -> float:
        """Calculate confidence score for successful interaction."""

        confidence = 0.5  # Base confidence

        # Boost confidence for visible elements
        if element.get('is_visible', False):
            confidence += 0.2

        # Boost confidence for enabled elements
        if element.get('is_enabled', True):
            confidence += 0.1

        # Boost confidence for elements with clear labels
        if element.get('aria_label') or element.get('title') or element.get('text_content'):
            confidence += 0.1

        # Boost confidence for standard form elements
        if element.get('tag_name') in ['button', 'input', 'select', 'textarea']:
            confidence += 0.1

        return min(1.0, confidence)

    def _determine_supported_interactions(self, element: Dict[str, Any]) -> List[str]:
        """Determine what interactions are supported by this element."""

        interactions = []
        tag = element.get('tag_name', '').lower()
        element_type = element.get('element_type', '').lower()

        if tag == 'button' or element_type in ['button', 'submit']:
            interactions.extend(['click', 'focus'])
        elif tag == 'input':
            if element_type in ['text', 'email', 'password', 'search', 'url', 'tel']:
                interactions.extend(['type', 'clear', 'focus', 'blur'])
            elif element_type in ['checkbox', 'radio']:
                interactions.extend(['check', 'uncheck', 'click'])
            elif element_type == 'file':
                interactions.extend(['upload', 'click'])
        elif tag == 'select':
            interactions.extend(['select_option', 'focus'])
        elif tag == 'textarea':
            interactions.extend(['type', 'clear', 'focus', 'blur'])
        elif tag == 'a':
            interactions.extend(['click', 'navigate'])

        return interactions

    def _calculate_automation_complexity(self, element: Dict[str, Any]) -> float:
        """Calculate automation complexity score (0.0 = easy, 1.0 = complex)."""

        complexity = 0.1  # Base complexity

        # Increase complexity for elements without clear identifiers
        if not any([element.get('element_id'), element.get('aria_label'), element.get('title')]):
            complexity += 0.2

        # Increase complexity for elements with dynamic classes
        class_name = element.get('element_class', '')
        if any(indicator in class_name for indicator in ['random', 'hash', 'generated']):
            complexity += 0.3

        # Increase complexity for small or overlapping elements
        width = element.get('width', 0)
        height = element.get('height', 0)
        if width < 20 or height < 20:
            complexity += 0.2

        return min(1.0, complexity)

    async def _extract_content_blocks(self, page: Page) -> List[Dict[str, Any]]:
        """Extract content blocks from the page."""

        try:
            content_blocks = await page.evaluate("""
                () => {
                    const blocks = [];
                    const selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'article', 'section', 'main'];

                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach((el, index) => {
                            const text = el.textContent?.trim();
                            if (text && text.length > 10) { // Only meaningful content
                                const rect = el.getBoundingClientRect();
                                blocks.push({
                                    block_type: selector,
                                    text_content: text.substring(0, 500), // Limit text length
                                    x_coordinate: Math.round(rect.left),
                                    y_coordinate: Math.round(rect.top),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height),
                                    is_visible: rect.width > 0 && rect.height > 0,
                                    element_index: index
                                });
                            }
                        });
                    });

                    return blocks.slice(0, 200); // Limit to prevent memory issues
                }
            """)

            # Enhance content blocks with semantic analysis
            enhanced_blocks = []
            for block in content_blocks:
                block['semantic_importance'] = self._calculate_semantic_importance(block)
                block['semantic_category'] = self._categorize_content(block)
                block['discovered_at'] = datetime.utcnow().isoformat()
                enhanced_blocks.append(block)

            return enhanced_blocks

        except Exception as e:
            logger.error("Failed to extract content blocks", error=str(e))
            return []

    def _calculate_semantic_importance(self, block: Dict[str, Any]) -> float:
        """Calculate semantic importance of a content block."""

        importance = 0.1  # Base importance
        block_type = block.get('block_type', '').lower()
        text = block.get('text_content', '').lower()

        # Headers are more important
        if block_type in ['h1', 'h2', 'h3']:
            importance += 0.4
        elif block_type in ['h4', 'h5', 'h6']:
            importance += 0.2

        # Main content areas
        if block_type in ['main', 'article']:
            importance += 0.3

        # Length-based importance
        text_length = len(text)
        if text_length > 100:
            importance += 0.1
        if text_length > 500:
            importance += 0.1

        return min(1.0, importance)

    def _categorize_content(self, block: Dict[str, Any]) -> str:
        """Categorize content block by type."""

        block_type = block.get('block_type', '').lower()
        text = block.get('text_content', '').lower()

        if block_type.startswith('h'):
            return 'heading'
        elif any(word in text for word in ['error', 'warning', 'alert']):
            return 'alert'
        elif any(word in text for word in ['menu', 'navigation', 'nav']):
            return 'navigation'
        elif any(word in text for word in ['footer', 'copyright', '©']):
            return 'footer'
        elif len(text) > 200:
            return 'main_content'
        else:
            return 'general_content'

    async def _analyze_action_capabilities(
        self,
        interactive_elements: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze what actions can be performed on this page."""

        capabilities = []

        # Analyze form submission capabilities
        forms = [el for el in interactive_elements if el.get('tag_name') == 'form' or el.get('form_id')]
        if forms:
            capabilities.append({
                'action_name': 'form_submission',
                'description': 'Submit forms on this page',
                'feasibility_score': 0.8,
                'required_elements': [el['element_id'] or el['element_class'] for el in forms[:3]],
                'complexity_score': 0.3
            })

        # Analyze search capabilities
        search_elements = [
            el for el in interactive_elements
            if 'search' in el.get('semantic_role', '') or 'search' in el.get('text_content', '').lower()
        ]
        if search_elements:
            capabilities.append({
                'action_name': 'search',
                'description': 'Perform search on this page',
                'feasibility_score': 0.9,
                'required_elements': [el['element_id'] or el['element_class'] for el in search_elements[:2]],
                'complexity_score': 0.2
            })

        # Analyze navigation capabilities
        nav_links = [el for el in interactive_elements if el.get('tag_name') == 'a']
        if nav_links:
            capabilities.append({
                'action_name': 'navigation',
                'description': 'Navigate to other pages',
                'feasibility_score': 0.95,
                'required_elements': [el.get('href', '') for el in nav_links[:5]],
                'complexity_score': 0.1
            })

        return capabilities

    async def _capture_screenshot(self, page: Page, task_id: int) -> Optional[str]:
        """Capture screenshot of the page."""

        try:
            # Create screenshots directory if it doesn't exist
            import os
            screenshot_dir = "screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)

            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"task_{task_id}_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)

            # Capture screenshot
            await page.screenshot(
                path=filepath,
                full_page=True,
                quality=self.screenshot_quality
            )

            logger.info("Screenshot captured", task_id=task_id, path=filepath)
            return filepath

        except Exception as e:
            logger.error("Failed to capture screenshot", task_id=task_id, error=str(e))
            return None

    def _generate_content_hash(
        self,
        metadata: Dict[str, Any],
        interactive_elements: List[Dict[str, Any]],
        content_blocks: List[Dict[str, Any]]
    ) -> str:
        """Generate a hash of the page content for caching."""

        # Create a string representation of key content
        content_str = json.dumps({
            'title': metadata.get('title', ''),
            'element_count': len(interactive_elements),
            'content_count': len(content_blocks),
            'elements': [
                {
                    'type': el.get('tag_name'),
                    'text': el.get('text_content', '')[:50]  # First 50 chars
                }
                for el in interactive_elements[:20]  # First 20 elements
            ]
        }, sort_keys=True)

        return hashlib.md5(content_str.encode()).hexdigest()


# Global web parser service instance
web_parser_service = WebParserService()
