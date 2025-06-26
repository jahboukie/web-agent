"""
Base tool class for WebAgent LangChain tools.

This module provides the foundation for all custom tools used by the WebAgent
planning agent to analyze webpages and generate execution plans.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class WebAgentToolInput(BaseModel):
    """Base input schema for WebAgent tools."""

    query: str = Field(description="The query or instruction for the tool")


class WebAgentBaseTool(BaseTool, ABC):
    """
    Base class for all WebAgent custom tools.

    This class provides common functionality for tools that analyze webpage data
    and assist in generating execution plans.
    """

    name: str = "webagent_base_tool"
    description: str = "Base tool for WebAgent planning"
    args_schema: type[BaseModel] = WebAgentToolInput  # type: ignore
    webpage_data: dict[str, Any] = Field(default_factory=dict)
    _logger: Any = Field(default=None, exclude=True)

    def __init__(self, webpage_data: dict[str, Any] | None = None, **kwargs: Any):
        """
        Initialize the tool with webpage data.

        Args:
            webpage_data: Parsed webpage data from WebParser service
            **kwargs: Additional tool configuration
        """
        if webpage_data is not None:
            kwargs["webpage_data"] = webpage_data
        super().__init__(**kwargs)
        # Set logger as a private attribute to avoid Pydantic field issues
        self._logger = structlog.get_logger(self.__class__.__name__)

    @property
    def logger(self) -> Any:
        """Get the logger instance."""
        return self._logger

    def _run(self, query: str, **kwargs: Any) -> str:
        """
        Synchronous execution of the tool.

        Args:
            query: The query or instruction for the tool
            **kwargs: Additional parameters

        Returns:
            Tool execution result as string
        """
        try:
            self.logger.info("Executing tool", tool=self.name, query=query[:100])
            result = self._execute_tool(query, **kwargs)
            self.logger.info(
                "Tool execution completed",
                tool=self.name,
                result_length=len(str(result)),
            )
            return result
        except Exception as e:
            self.logger.error("Tool execution failed", tool=self.name, error=str(e))
            return f"Error executing {self.name}: {str(e)}"

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """
        Asynchronous execution of the tool.

        Args:
            query: The query or instruction for the tool
            **kwargs: Additional parameters

        Returns:
            Tool execution result as string
        """
        # For now, just call the sync version
        # Can be overridden by subclasses for true async execution
        return self._run(query, **kwargs)

    @abstractmethod
    def _execute_tool(self, query: str, **kwargs: Any) -> str:
        """
        Execute the tool's core functionality.

        This method must be implemented by subclasses to provide the actual
        tool functionality.

        Args:
            query: The query or instruction for the tool
            **kwargs: Additional parameters

        Returns:
            Tool execution result as string
        """
        pass

    def _format_webpage_summary(self) -> str:
        """
        Create a formatted summary of the webpage data.

        Returns:
            Formatted webpage summary for agent context
        """
        if not self.webpage_data:
            return "No webpage data available"

        summary_parts = []

        # Basic page info
        if "url" in self.webpage_data:
            summary_parts.append(f"URL: {self.webpage_data['url']}")

        if "title" in self.webpage_data:
            summary_parts.append(f"Title: {self.webpage_data['title']}")

        # Interactive elements
        if "interactive_elements" in self.webpage_data:
            elements = self.webpage_data["interactive_elements"]
            summary_parts.append(f"Interactive Elements: {len(elements)} found")

            # Group by type
            element_types: dict[str, list[Any]] = {}
            for element in elements[:10]:  # Limit to first 10 for summary
                elem_type = element.get("type", "unknown")
                if elem_type not in element_types:
                    element_types[elem_type] = []
                element_types[elem_type].append(element)

            for elem_type, elems in element_types.items():
                summary_parts.append(f"  - {elem_type}: {len(elems)} elements")

        # Content blocks
        if "content_blocks" in self.webpage_data:
            blocks = self.webpage_data["content_blocks"]
            summary_parts.append(f"Content Blocks: {len(blocks)} found")

        return "\n".join(summary_parts)

    def _get_interactive_elements_by_type(
        self, element_type: str
    ) -> list[dict[str, Any]]:
        """
        Get interactive elements filtered by type.

        Args:
            element_type: Type of elements to retrieve (button, input, link, etc.)

        Returns:
            List of elements matching the specified type
        """
        if not self.webpage_data.get("interactive_elements"):
            return []

        return [
            elem
            for elem in self.webpage_data["interactive_elements"]
            if elem.get("type", "").lower() == element_type.lower()
        ]

    def _find_elements_by_text(
        self, text: str, partial_match: bool = True
    ) -> list[dict[str, Any]]:
        """
        Find interactive elements containing specific text.

        Args:
            text: Text to search for
            partial_match: Whether to allow partial text matches

        Returns:
            List of elements containing the specified text
        """
        if not self.webpage_data.get("interactive_elements"):
            return []

        matching_elements = []
        search_text = text.lower()

        for elem in self.webpage_data["interactive_elements"]:
            element_text = elem.get("text", "").lower()
            element_label = elem.get("label", "").lower()
            element_placeholder = elem.get("placeholder", "").lower()

            if partial_match:
                if (
                    search_text in element_text
                    or search_text in element_label
                    or search_text in element_placeholder
                ):
                    matching_elements.append(elem)
            else:
                if (
                    search_text == element_text
                    or search_text == element_label
                    or search_text == element_placeholder
                ):
                    matching_elements.append(elem)

        return matching_elements
