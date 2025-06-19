from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator


class InteractiveElementBase(BaseModel):
    element_id: Optional[str] = None
    element_class: Optional[str] = None
    tag_name: str
    element_type: str
    text_content: Optional[str] = None
    placeholder: Optional[str] = None
    xpath: str
    css_selector: Optional[str] = None
    x_coordinate: Optional[int] = None
    y_coordinate: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_visible: bool = True
    is_enabled: bool = True
    interaction_confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class InteractiveElementCreate(InteractiveElementBase):
    pass


class InteractiveElement(InteractiveElementBase):
    id: int
    web_page_id: int
    supported_interactions: List[str] = []
    semantic_role: Optional[str] = None
    semantic_labels: List[str] = []
    interaction_success_rate: float = 0.0
    discovered_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class ContentBlockBase(BaseModel):
    block_type: str
    text_content: Optional[str] = None
    html_content: Optional[str] = None
    url: Optional[HttpUrl] = None
    alt_text: Optional[str] = None
    x_coordinate: Optional[int] = None
    y_coordinate: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_visible: bool = True
    semantic_importance: float = Field(ge=0.0, le=1.0, default=0.0)


class ContentBlock(ContentBlockBase):
    id: int
    web_page_id: int
    content_hash: Optional[str] = None
    semantic_category: Optional[str] = None
    keywords: List[str] = []
    discovered_at: datetime

    class Config:
        from_attributes = True


class ActionCapabilityBase(BaseModel):
    action_name: str
    description: str
    required_elements: List[str] = []
    required_data: List[str] = []
    prerequisites: List[str] = []
    feasibility_score: float = Field(ge=0.0, le=1.0, default=0.0)
    complexity_score: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class ActionCapability(ActionCapabilityBase):
    id: int
    web_page_id: int
    attempted_count: int = 0
    success_count: int = 0
    last_attempted_at: Optional[datetime] = None
    last_successful_at: Optional[datetime] = None
    discovered_at: datetime

    class Config:
        from_attributes = True


class WebPageBase(BaseModel):
    url: HttpUrl
    canonical_url: Optional[HttpUrl] = None
    title: Optional[str] = None
    domain: str
    page_type: Optional[str] = None
    language: Optional[str] = None


class WebPageCreate(WebPageBase):
    semantic_data: Dict[str, Any] = {}
    has_javascript: bool = False
    has_spa_content: bool = False
    requires_authentication: bool = False


class WebPageUpdate(BaseModel):
    title: Optional[str] = None
    page_type: Optional[str] = None
    semantic_data: Optional[Dict[str, Any]] = None
    accessibility_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    complexity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    automation_difficulty: Optional[float] = Field(None, ge=0.0, le=100.0)


class WebPage(WebPageBase):
    id: int
    content_hash: str
    interactive_elements_count: int = 0
    form_count: int = 0
    link_count: int = 0
    image_count: int = 0
    semantic_data: Dict[str, Any] = {}
    accessibility_score: Optional[float] = None
    complexity_score: Optional[float] = None
    automation_difficulty: Optional[float] = None
    parsed_at: datetime
    parsing_duration_ms: Optional[int] = None
    success: bool = True
    cache_hit_count: int = 0
    
    # Relationships
    interactive_elements: List[InteractiveElement] = []
    content_blocks: List[ContentBlock] = []
    action_capabilities: List[ActionCapability] = []

    class Config:
        from_attributes = True

    @validator('domain')
    def extract_domain_from_url(cls, v, values):
        if 'url' in values and values['url']:
            from urllib.parse import urlparse
            return urlparse(str(values['url'])).netloc
        return v


class WebPageParseRequest(BaseModel):
    url: HttpUrl
    force_refresh: bool = False
    include_screenshot: bool = True
    wait_for_load: int = Field(default=3, ge=1, le=30)
    extract_forms: bool = True
    extract_links: bool = True
    semantic_analysis: bool = True


class WebPageParseResponse(BaseModel):
    web_page: WebPage
    processing_time_ms: int
    cache_hit: bool = False
    screenshots: List[str] = []  # List of screenshot URLs/paths
    warnings: List[str] = []
    errors: List[str] = []