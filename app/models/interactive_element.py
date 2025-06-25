# === FORCE UPDATE ===
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .execution_plan import AtomicAction
    from .web_page import WebPage


class ElementType(str, Enum):
    BUTTON = "button"
    INPUT = "input"
    TEXTAREA = "textarea"
    SELECT = "select"
    LINK = "link"
    IMAGE = "image"
    VIDEO = "video"
    FORM = "form"
    UNKNOWN = "unknown"


class InteractionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    HOVER = "hover"
    SCROLL_TO = "scroll_to"


class InteractiveElement(Base):
    __tablename__ = "interactive_elements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    web_page_id: Mapped[int] = mapped_column(ForeignKey("web_pages.id"))

    element_type: Mapped[ElementType] = mapped_column(SQLEnum(ElementType))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    x_coordinate: Mapped[int] = mapped_column(Integer)
    y_coordinate: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    dom_path: Mapped[str] = mapped_column(String(1000))
    
    possible_interactions: Mapped[list[InteractionType]] = mapped_column(JSON)
    is_interactive: Mapped[bool] = mapped_column(Boolean, default=False)
    
    inferred_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)

    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    web_page: Mapped["WebPage"] = relationship(back_populates="interactive_elements")
    actions_taken: Mapped[list["AtomicAction"]] = relationship(back_populates="target_element")
