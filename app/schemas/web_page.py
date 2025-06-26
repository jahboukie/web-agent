from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class InteractiveElementBase(BaseModel):
    element_id: str | None = None
    element_class: str | None = None
    tag_name: str
    element_type: str
    text_content: str | None = None
    placeholder: str | None = None
    xpath: str
    css_selector: str | None = None
    x_coordinate: int | None = None
    y_coordinate: int | None = None
    width: int | None = None
    height: int | None = None
    is_visible: bool = True
    is_enabled: bool = True
    interaction_confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class InteractiveElementCreate(InteractiveElementBase):
    pass


class InteractiveElement(InteractiveElementBase):
    id: int
    web_page_id: int
    supported_interactions: list[str] = []
    semantic_role: str | None = None
    semantic_labels: list[str] = []
    interaction_success_rate: float = 0.0
    discovered_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class ContentBlockBase(BaseModel):
    block_type: str
    text_content: str | None = None
    html_content: str | None = None
    url: HttpUrl | None = None
    alt_text: str | None = None
    x_coordinate: int | None = None
    y_coordinate: int | None = None
    width: int | None = None
    height: int | None = None
    is_visible: bool = True
    semantic_importance: float = Field(ge=0.0, le=1.0, default=0.0)


class ContentBlock(ContentBlockBase):
    id: int
    web_page_id: int
    content_hash: str | None = None
    semantic_category: str | None = None
    keywords: list[str] = []
    discovered_at: datetime

    class Config:
        from_attributes = True


class ActionCapabilityBase(BaseModel):
    action_name: str
    description: str
    required_elements: list[str] = []
    required_data: list[str] = []
    prerequisites: list[str] = []
    feasibility_score: float = Field(ge=0.0, le=1.0, default=0.0)
    complexity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class ActionCapability(ActionCapabilityBase):
    id: int
    web_page_id: int
    attempted_count: int = 0
    success_count: int = 0
    last_attempted_at: datetime | None = None
    last_successful_at: datetime | None = None
    discovered_at: datetime

    class Config:
        from_attributes = True


class WebPageBase(BaseModel):
    url: HttpUrl
    canonical_url: HttpUrl | None = None
    title: str | None = None
    domain: str
    page_type: str | None = None
    language: str | None = None


class WebPageCreate(WebPageBase):
    semantic_data: dict[str, Any] = {}
    has_javascript: bool = False
    has_spa_content: bool = False
    requires_authentication: bool = False


class WebPageUpdate(BaseModel):
    title: str | None = None
    page_type: str | None = None
    semantic_data: dict[str, Any] | None = None
    accessibility_score: float | None = Field(None, ge=0.0, le=100.0)
    complexity_score: float | None = Field(None, ge=0.0, le=100.0)
    automation_difficulty: float | None = Field(None, ge=0.0, le=100.0)


class WebPage(WebPageBase):
    id: int
    content_hash: str
    interactive_elements_count: int = 0
    form_count: int = 0
    link_count: int = 0
    image_count: int = 0
    semantic_data: dict[str, Any] = {}
    accessibility_score: float | None = None
    complexity_score: float | None = None
    automation_difficulty: float | None = None
    parsed_at: datetime
    parsing_duration_ms: int | None = None
    success: bool = True
    cache_hit_count: int = 0

    # Relationships
    interactive_elements: list[InteractiveElement] = []
    content_blocks: list[ContentBlock] = []
    action_capabilities: list[ActionCapability] = []

    class Config:
        from_attributes = True

    @field_validator("domain")
    @classmethod
    def extract_domain_from_url(cls, v: str, values: Any) -> str:
        if "url" in values.data and values.data["url"]:
            from urllib.parse import urlparse

            return urlparse(str(values.data["url"])).netloc
        return v


class WebPageParseRequest(BaseModel):
    url: HttpUrl
    force_refresh: bool = False
    include_screenshot: bool = True
    wait_for_load: int = Field(default=3, ge=1, le=30)
    wait_for_network_idle: bool = False
    extract_forms: bool = True
    extract_links: bool = True
    semantic_analysis: bool = True


class WebPageParseResponse(BaseModel):
    web_page: WebPage
    processing_time_ms: int
    cache_hit: bool = False
    screenshots: list[str] = []  # List of screenshot URLs/paths
    warnings: list[str] = []
    errors: list[str] = []
