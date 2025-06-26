# === FORCE UPDATE ===
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from .browser_session import BrowserSession
    from .interactive_element import InteractiveElement
    from .task_execution import ActionCapability, ContentBlock


class WebPage(Base):
    __tablename__ = "web_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(
        String(2048), unique=True, index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    html_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    is_parsed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    last_accessed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    load_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_size_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)

    analysis_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    interactive_elements: Mapped[list[InteractiveElement]] = relationship(
        back_populates="web_page", cascade="all, delete-orphan"
    )
    content_blocks: Mapped[list[ContentBlock]] = relationship(
        back_populates="web_page", cascade="all, delete-orphan"
    )
    action_capabilities: Mapped[list[ActionCapability]] = relationship(
        back_populates="web_page", cascade="all, delete-orphan"
    )
    browser_sessions: Mapped[list[BrowserSession]] = relationship(
        back_populates="current_page"
    )
