"""
Custom LangChain tools for webpage analysis and action planning.

These tools provide the WebAgent planning agent with the ability to analyze
parsed webpage data and determine the best automation strategies.
"""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field
import json
import structlog

from .base_tool import WebAgentBaseTool

logger = structlog.get_logger(__name__)


class WebpageAnalysisInput(BaseModel):
    """Input schema for webpage analysis tool."""
    analysis_request: str = Field(
        description="What aspect of the webpage to analyze (e.g., 'find login form', 'identify navigation elements', 'analyze page structure')"
    )


class ElementInspectorInput(BaseModel):
    """Input schema for element inspector tool."""
    element_query: str = Field(
        description="Query to find specific elements (e.g., 'submit button', 'email input field', 'navigation menu')"
    )


class ActionCapabilityInput(BaseModel):
    """Input schema for action capability assessor."""
    goal_description: str = Field(
        description="Description of the goal to assess automation capability for"
    )


class WebpageAnalysisTool(WebAgentBaseTool):
    """
    Tool for analyzing webpage structure and content to understand automation possibilities.
    
    This tool helps the planning agent understand the webpage layout, identify key sections,
    and determine the overall automation strategy.
    """
    
    name: str = "webpage_analyzer"
    description: str = """
    Analyze webpage structure and content to understand automation possibilities.
    Use this tool to get an overview of the page, identify key sections, and understand
    the overall layout before planning specific actions.
    """
    args_schema: Type[BaseModel] = WebpageAnalysisInput
    
    def _execute_tool(self, analysis_request: str, **kwargs) -> str:
        """
        Analyze the webpage based on the analysis request.
        
        Args:
            analysis_request: What aspect of the webpage to analyze
            
        Returns:
            Detailed analysis of the requested webpage aspect
        """
        if not self.webpage_data:
            return "No webpage data available for analysis"
        
        analysis_request_lower = analysis_request.lower()
        
        # Route to specific analysis based on request
        if "structure" in analysis_request_lower or "layout" in analysis_request_lower:
            return self._analyze_page_structure()
        elif "form" in analysis_request_lower:
            return self._analyze_forms()
        elif "navigation" in analysis_request_lower or "menu" in analysis_request_lower:
            return self._analyze_navigation()
        elif "content" in analysis_request_lower:
            return self._analyze_content()
        elif "interactive" in analysis_request_lower or "element" in analysis_request_lower:
            return self._analyze_interactive_elements()
        else:
            # General analysis
            return self._analyze_general()
    
    def _analyze_page_structure(self) -> str:
        """Analyze the overall page structure."""
        analysis = ["=== PAGE STRUCTURE ANALYSIS ==="]
        
        # Basic page info
        analysis.append(f"URL: {self.webpage_data.get('url', 'Unknown')}")
        analysis.append(f"Title: {self.webpage_data.get('title', 'No title')}")
        
        # Content organization
        content_blocks = self.webpage_data.get('content_blocks', [])
        analysis.append(f"\nContent Organization:")
        analysis.append(f"- Total content blocks: {len(content_blocks)}")
        
        if content_blocks:
            block_types = {}
            for block in content_blocks:
                block_type = block.get('type', 'unknown')
                block_types[block_type] = block_types.get(block_type, 0) + 1
            
            for block_type, count in block_types.items():
                analysis.append(f"  - {block_type}: {count}")
        
        # Interactive elements overview
        interactive_elements = self.webpage_data.get('interactive_elements', [])
        analysis.append(f"\nInteractive Elements: {len(interactive_elements)} total")
        
        if interactive_elements:
            element_types = {}
            for elem in interactive_elements:
                elem_type = elem.get('type', 'unknown')
                element_types[elem_type] = element_types.get(elem_type, 0) + 1
            
            for elem_type, count in element_types.items():
                analysis.append(f"  - {elem_type}: {count}")
        
        return "\n".join(analysis)
    
    def _analyze_forms(self) -> str:
        """Analyze forms on the page."""
        analysis = ["=== FORM ANALYSIS ==="]
        
        # Find form-related elements
        form_elements = []
        for elem in self.webpage_data.get('interactive_elements', []):
            elem_type = elem.get('type', '').lower()
            if elem_type in ['input', 'textarea', 'select', 'button']:
                form_elements.append(elem)
        
        if not form_elements:
            analysis.append("No form elements detected on this page.")
            return "\n".join(analysis)
        
        analysis.append(f"Found {len(form_elements)} form-related elements:")
        
        # Group by likely forms (heuristic based on proximity and types)
        input_fields = [e for e in form_elements if e.get('type') in ['input', 'textarea', 'select']]
        buttons = [e for e in form_elements if e.get('type') == 'button']
        
        analysis.append(f"\nInput Fields ({len(input_fields)}):")
        for field in input_fields[:10]:  # Limit output
            field_type = field.get('input_type', field.get('type', 'unknown'))
            label = field.get('label', field.get('placeholder', 'No label'))
            analysis.append(f"  - {field_type}: {label}")
        
        analysis.append(f"\nButtons ({len(buttons)}):")
        for button in buttons[:10]:  # Limit output
            button_text = button.get('text', button.get('label', 'No text'))
            analysis.append(f"  - {button_text}")
        
        return "\n".join(analysis)
    
    def _analyze_navigation(self) -> str:
        """Analyze navigation elements."""
        analysis = ["=== NAVIGATION ANALYSIS ==="]
        
        # Find navigation-related elements
        nav_elements = []
        for elem in self.webpage_data.get('interactive_elements', []):
            elem_type = elem.get('type', '').lower()
            elem_text = elem.get('text', '').lower()
            elem_label = elem.get('label', '').lower()
            
            if (elem_type == 'link' or 
                'nav' in elem_text or 'menu' in elem_text or
                'nav' in elem_label or 'menu' in elem_label):
                nav_elements.append(elem)
        
        if not nav_elements:
            analysis.append("No clear navigation elements detected.")
            return "\n".join(analysis)
        
        analysis.append(f"Found {len(nav_elements)} navigation elements:")
        
        for nav_elem in nav_elements[:15]:  # Limit output
            text = nav_elem.get('text', nav_elem.get('label', 'No text'))
            href = nav_elem.get('href', '')
            if href:
                analysis.append(f"  - {text} → {href}")
            else:
                analysis.append(f"  - {text}")
        
        return "\n".join(analysis)
    
    def _analyze_content(self) -> str:
        """Analyze page content."""
        analysis = ["=== CONTENT ANALYSIS ==="]
        
        content_blocks = self.webpage_data.get('content_blocks', [])
        if not content_blocks:
            analysis.append("No content blocks available for analysis.")
            return "\n".join(analysis)
        
        analysis.append(f"Content Summary ({len(content_blocks)} blocks):")
        
        for i, block in enumerate(content_blocks[:10]):  # Limit output
            block_type = block.get('type', 'unknown')
            content = block.get('content', '')[:100]  # First 100 chars
            analysis.append(f"  {i+1}. {block_type}: {content}...")
        
        return "\n".join(analysis)
    
    def _analyze_interactive_elements(self) -> str:
        """Analyze all interactive elements."""
        analysis = ["=== INTERACTIVE ELEMENTS ANALYSIS ==="]
        
        elements = self.webpage_data.get('interactive_elements', [])
        if not elements:
            analysis.append("No interactive elements found.")
            return "\n".join(analysis)
        
        analysis.append(f"Total Interactive Elements: {len(elements)}")
        
        # Group by type and show details
        element_groups = {}
        for elem in elements:
            elem_type = elem.get('type', 'unknown')
            if elem_type not in element_groups:
                element_groups[elem_type] = []
            element_groups[elem_type].append(elem)
        
        for elem_type, elems in element_groups.items():
            analysis.append(f"\n{elem_type.upper()} Elements ({len(elems)}):")
            for elem in elems[:5]:  # Show first 5 of each type
                text = elem.get('text', elem.get('label', elem.get('placeholder', 'No text')))
                confidence = elem.get('confidence', 0)
                analysis.append(f"  - {text} (confidence: {confidence:.2f})")
        
        return "\n".join(analysis)
    
    def _analyze_general(self) -> str:
        """Perform general webpage analysis."""
        analysis = ["=== GENERAL WEBPAGE ANALYSIS ==="]
        
        # Combine key insights
        analysis.append(self._format_webpage_summary())
        
        # Add automation assessment
        elements = self.webpage_data.get('interactive_elements', [])
        if elements:
            high_confidence_elements = [e for e in elements if e.get('confidence', 0) > 0.8]
            analysis.append(f"\nAutomation Readiness:")
            analysis.append(f"- High confidence elements: {len(high_confidence_elements)}/{len(elements)}")
            analysis.append(f"- Automation feasibility: {'High' if len(high_confidence_elements) > len(elements) * 0.7 else 'Medium' if len(high_confidence_elements) > len(elements) * 0.4 else 'Low'}")
        
        return "\n".join(analysis)


class ElementInspectorTool(WebAgentBaseTool):
    """
    Tool for inspecting and finding specific elements on a webpage.

    This tool helps the planning agent locate specific elements needed for automation,
    providing detailed information about their properties and automation capabilities.
    """

    name: str = "element_inspector"
    description: str = """
    Inspect and find specific elements on the webpage for automation planning.
    Use this tool to locate buttons, input fields, links, and other interactive elements
    needed to accomplish the user's goal.
    """
    args_schema: Type[BaseModel] = ElementInspectorInput

    def _execute_tool(self, element_query: str, **kwargs) -> str:
        """
        Find and inspect elements based on the query.

        Args:
            element_query: Query describing the elements to find

        Returns:
            Detailed information about matching elements
        """
        if not self.webpage_data:
            return "No webpage data available for element inspection"

        query_lower = element_query.lower()
        results = ["=== ELEMENT INSPECTION RESULTS ==="]
        results.append(f"Query: {element_query}")

        # Find elements based on query
        matching_elements = self._find_matching_elements(query_lower)

        if not matching_elements:
            results.append("No matching elements found.")
            # Suggest alternatives
            results.append("\nAvailable element types:")
            element_types = set()
            for elem in self.webpage_data.get('interactive_elements', []):
                element_types.add(elem.get('type', 'unknown'))
            for elem_type in sorted(element_types):
                results.append(f"  - {elem_type}")
            return "\n".join(results)

        results.append(f"\nFound {len(matching_elements)} matching elements:")

        for i, elem in enumerate(matching_elements[:10], 1):  # Limit to 10 results
            results.append(f"\n{i}. {self._format_element_details(elem)}")

        return "\n".join(results)

    def _find_matching_elements(self, query: str) -> List[Dict[str, Any]]:
        """Find elements matching the query."""
        elements = self.webpage_data.get('interactive_elements', [])
        matching = []

        for elem in elements:
            if self._element_matches_query(elem, query):
                matching.append(elem)

        # Sort by confidence score (highest first)
        matching.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return matching

    def _element_matches_query(self, element: Dict[str, Any], query: str) -> bool:
        """Check if an element matches the query."""
        # Check element type
        elem_type = element.get('type', '').lower()
        if elem_type in query:
            return True

        # Check text content
        text_fields = ['text', 'label', 'placeholder', 'title', 'alt']
        for field in text_fields:
            field_value = element.get(field, '').lower()
            if field_value and any(word in field_value for word in query.split()):
                return True

        # Check specific patterns
        if 'submit' in query and (elem_type == 'button' and 'submit' in element.get('text', '').lower()):
            return True
        if 'login' in query and ('login' in element.get('text', '').lower() or 'sign in' in element.get('text', '').lower()):
            return True
        if 'email' in query and element.get('input_type') == 'email':
            return True
        if 'password' in query and element.get('input_type') == 'password':
            return True

        return False

    def _format_element_details(self, element: Dict[str, Any]) -> str:
        """Format detailed element information."""
        details = []

        # Basic info
        elem_type = element.get('type', 'unknown')
        details.append(f"Type: {elem_type}")

        # Text content
        text = element.get('text', element.get('label', element.get('placeholder', '')))
        if text:
            details.append(f"Text: '{text}'")

        # Input type for input elements
        if elem_type == 'input' and 'input_type' in element:
            details.append(f"Input Type: {element['input_type']}")

        # Selector information
        if 'selector' in element:
            details.append(f"Selector: {element['selector']}")

        # Confidence score
        confidence = element.get('confidence', 0)
        details.append(f"Confidence: {confidence:.2f}")

        # Automation capabilities
        capabilities = element.get('capabilities', [])
        if capabilities:
            details.append(f"Capabilities: {', '.join(capabilities)}")

        return " | ".join(details)


class ActionCapabilityAssessor(WebAgentBaseTool):
    """
    Tool for assessing the automation capability for a specific goal.

    This tool evaluates whether a given goal can be accomplished on the current webpage
    and provides confidence scores and recommendations.
    """

    name: str = "action_capability_assessor"
    description: str = """
    Assess the automation capability for accomplishing a specific goal on this webpage.
    Use this tool to evaluate feasibility, identify required elements, and get confidence
    scores for automation success.
    """
    args_schema: Type[BaseModel] = ActionCapabilityInput

    def _execute_tool(self, goal_description: str, **kwargs) -> str:
        """
        Assess automation capability for the given goal.

        Args:
            goal_description: Description of the goal to assess

        Returns:
            Detailed capability assessment
        """
        if not self.webpage_data:
            return "No webpage data available for capability assessment"

        assessment = ["=== AUTOMATION CAPABILITY ASSESSMENT ==="]
        assessment.append(f"Goal: {goal_description}")

        # Analyze goal requirements
        required_actions = self._analyze_goal_requirements(goal_description)
        assessment.append(f"\nRequired Actions: {', '.join(required_actions)}")

        # Assess element availability
        element_assessment = self._assess_element_availability(required_actions)
        assessment.append(f"\nElement Availability Assessment:")

        overall_confidence = 0
        total_requirements = len(required_actions)

        for action, elements in element_assessment.items():
            if elements:
                best_element = max(elements, key=lambda x: x.get('confidence', 0))
                confidence = best_element.get('confidence', 0)
                overall_confidence += confidence
                assessment.append(f"  - {action}: ✓ Available (confidence: {confidence:.2f})")
                assessment.append(f"    Best match: {best_element.get('text', best_element.get('type', 'Unknown'))}")
            else:
                assessment.append(f"  - {action}: ✗ Not found")

        # Calculate overall confidence
        if total_requirements > 0:
            overall_confidence = overall_confidence / total_requirements

        assessment.append(f"\nOverall Automation Confidence: {overall_confidence:.2f}")
        assessment.append(f"Feasibility: {'High' if overall_confidence > 0.8 else 'Medium' if overall_confidence > 0.5 else 'Low'}")

        # Provide recommendations
        recommendations = self._generate_recommendations(overall_confidence, element_assessment)
        if recommendations:
            assessment.append(f"\nRecommendations:")
            for rec in recommendations:
                assessment.append(f"  - {rec}")

        return "\n".join(assessment)

    def _analyze_goal_requirements(self, goal: str) -> List[str]:
        """Analyze what actions are required to accomplish the goal."""
        goal_lower = goal.lower()
        required_actions = []

        # Common goal patterns
        if any(word in goal_lower for word in ['login', 'sign in', 'authenticate']):
            required_actions.extend(['find_email_input', 'find_password_input', 'find_login_button'])

        if any(word in goal_lower for word in ['register', 'sign up', 'create account']):
            required_actions.extend(['find_email_input', 'find_password_input', 'find_signup_button'])

        if any(word in goal_lower for word in ['search', 'find', 'look for']):
            required_actions.extend(['find_search_input', 'find_search_button'])

        if any(word in goal_lower for word in ['submit', 'send', 'post']):
            required_actions.append('find_submit_button')

        if any(word in goal_lower for word in ['navigate', 'go to', 'visit']):
            required_actions.append('find_navigation_link')

        if any(word in goal_lower for word in ['fill', 'enter', 'input']):
            required_actions.append('find_input_fields')

        # If no specific patterns found, add generic requirements
        if not required_actions:
            required_actions = ['find_interactive_elements', 'assess_page_structure']

        return required_actions

    def _assess_element_availability(self, required_actions: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Assess availability of elements for required actions."""
        elements = self.webpage_data.get('interactive_elements', [])
        assessment = {}

        for action in required_actions:
            matching_elements = []

            if action == 'find_email_input':
                matching_elements = [e for e in elements if e.get('input_type') == 'email' or 'email' in e.get('placeholder', '').lower()]

            elif action == 'find_password_input':
                matching_elements = [e for e in elements if e.get('input_type') == 'password']

            elif action == 'find_login_button':
                matching_elements = [e for e in elements if e.get('type') == 'button' and
                                   any(word in e.get('text', '').lower() for word in ['login', 'sign in', 'log in'])]

            elif action == 'find_signup_button':
                matching_elements = [e for e in elements if e.get('type') == 'button' and
                                   any(word in e.get('text', '').lower() for word in ['sign up', 'register', 'create'])]

            elif action == 'find_search_input':
                matching_elements = [e for e in elements if e.get('type') == 'input' and
                                   'search' in e.get('placeholder', '').lower()]

            elif action == 'find_search_button':
                matching_elements = [e for e in elements if e.get('type') == 'button' and
                                   'search' in e.get('text', '').lower()]

            elif action == 'find_submit_button':
                matching_elements = [e for e in elements if e.get('type') == 'button' and
                                   any(word in e.get('text', '').lower() for word in ['submit', 'send', 'post'])]

            elif action == 'find_navigation_link':
                matching_elements = [e for e in elements if e.get('type') == 'link']

            elif action == 'find_input_fields':
                matching_elements = [e for e in elements if e.get('type') in ['input', 'textarea', 'select']]

            elif action == 'find_interactive_elements':
                matching_elements = elements

            elif action == 'assess_page_structure':
                # This is always available if we have webpage data
                matching_elements = [{'type': 'page_structure', 'confidence': 1.0, 'text': 'Page structure available'}]

            assessment[action] = matching_elements

        return assessment

    def _generate_recommendations(self, confidence: float, element_assessment: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Generate recommendations based on the assessment."""
        recommendations = []

        if confidence < 0.3:
            recommendations.append("Low automation confidence. Consider manual verification of element selectors.")
            recommendations.append("Review page structure and identify alternative automation approaches.")

        elif confidence < 0.7:
            recommendations.append("Medium automation confidence. Test thoroughly before deployment.")
            recommendations.append("Consider adding fallback strategies for unreliable elements.")

        else:
            recommendations.append("High automation confidence. Proceed with plan generation.")

        # Check for missing critical elements
        missing_actions = [action for action, elements in element_assessment.items() if not elements]
        if missing_actions:
            recommendations.append(f"Missing elements for: {', '.join(missing_actions)}")
            recommendations.append("Consider alternative selectors or manual element identification.")

        return recommendations
