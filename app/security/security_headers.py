"""
Security Headers Middleware

Implementation of comprehensive security headers including CSP, HSTS,
and other security-focused HTTP headers for enterprise applications.
"""

import secrets
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CSPDirective:
    """Content Security Policy directive builder."""

    def __init__(self):
        self.directives: dict[str, list[str]] = {}

    def add_directive(self, directive: str, sources: list[str]) -> "CSPDirective":
        """Add or update a CSP directive."""
        if directive not in self.directives:
            self.directives[directive] = []
        self.directives[directive].extend(sources)
        return self

    def default_src(self, sources: list[str]) -> "CSPDirective":
        """Set default-src directive."""
        return self.add_directive("default-src", sources)

    def script_src(self, sources: list[str]) -> "CSPDirective":
        """Set script-src directive."""
        return self.add_directive("script-src", sources)

    def style_src(self, sources: list[str]) -> "CSPDirective":
        """Set style-src directive."""
        return self.add_directive("style-src", sources)

    def img_src(self, sources: list[str]) -> "CSPDirective":
        """Set img-src directive."""
        return self.add_directive("img-src", sources)

    def connect_src(self, sources: list[str]) -> "CSPDirective":
        """Set connect-src directive."""
        return self.add_directive("connect-src", sources)

    def font_src(self, sources: list[str]) -> "CSPDirective":
        """Set font-src directive."""
        return self.add_directive("font-src", sources)

    def object_src(self, sources: list[str]) -> "CSPDirective":
        """Set object-src directive."""
        return self.add_directive("object-src", sources)

    def media_src(self, sources: list[str]) -> "CSPDirective":
        """Set media-src directive."""
        return self.add_directive("media-src", sources)

    def frame_src(self, sources: list[str]) -> "CSPDirective":
        """Set frame-src directive."""
        return self.add_directive("frame-src", sources)

    def frame_ancestors(self, sources: list[str]) -> "CSPDirective":
        """Set frame-ancestors directive."""
        return self.add_directive("frame-ancestors", sources)

    def form_action(self, sources: list[str]) -> "CSPDirective":
        """Set form-action directive."""
        return self.add_directive("form-action", sources)

    def base_uri(self, sources: list[str]) -> "CSPDirective":
        """Set base-uri directive."""
        return self.add_directive("base-uri", sources)

    def upgrade_insecure_requests(self) -> "CSPDirective":
        """Add upgrade-insecure-requests directive."""
        return self.add_directive("upgrade-insecure-requests", [])

    def block_all_mixed_content(self) -> "CSPDirective":
        """Add block-all-mixed-content directive."""
        return self.add_directive("block-all-mixed-content", [])

    def build(self) -> str:
        """Build the CSP header value."""
        policy_parts = []

        for directive, sources in self.directives.items():
            if sources:
                policy_parts.append(f"{directive} {' '.join(sources)}")
            else:
                policy_parts.append(directive)

        return "; ".join(policy_parts)


class SecurityHeadersConfig:
    """Configuration for security headers."""

    def __init__(self):
        self.environment = getattr(settings, "ENVIRONMENT", "development")
        self.debug = getattr(settings, "DEBUG", False)

        # CSP Configuration
        self.enable_csp = True
        self.csp_report_only = self.debug  # Use report-only in debug mode
        self.csp_report_uri = "/api/v1/security/csp-report"

        # Nonce configuration
        self.use_nonce = True
        self.nonce_length = 16

    def get_csp_policy(self, nonce: str | None = None) -> CSPDirective:
        """Get CSP policy based on environment."""
        csp = CSPDirective()

        if self.environment == "production":
            # Strict production CSP
            csp.default_src(["'self'"])

            if nonce:
                csp.script_src(["'self'", f"'nonce-{nonce}'", "'strict-dynamic'"])
                csp.style_src(
                    ["'self'", f"'nonce-{nonce}'", "'unsafe-inline'"]
                )  # unsafe-inline needed for some CSS frameworks
            else:
                csp.script_src(["'self'"])
                csp.style_src(["'self'", "'unsafe-inline'"])

            csp.img_src(["'self'", "data:", "https:"])
            csp.connect_src(["'self'", "https:", "wss:", "ws:"])
            csp.font_src(["'self'", "data:", "https:"])
            csp.object_src(["'none'"])
            csp.media_src(["'self'"])
            csp.frame_src(["'none'"])
            csp.frame_ancestors(["'none'"])
            csp.form_action(["'self'"])
            csp.base_uri(["'self'"])
            csp.upgrade_insecure_requests()
            csp.block_all_mixed_content()

        else:
            # Development CSP (more permissive)
            csp.default_src(["'self'", "'unsafe-inline'", "'unsafe-eval'"])
            csp.script_src(
                [
                    "'self'",
                    "'unsafe-inline'",
                    "'unsafe-eval'",
                    "localhost:*",
                    "127.0.0.1:*",
                ]
            )
            csp.style_src(["'self'", "'unsafe-inline'", "localhost:*", "127.0.0.1:*"])
            csp.img_src(["'self'", "data:", "http:", "https:"])
            csp.connect_src(
                [
                    "'self'",
                    "http:",
                    "https:",
                    "ws:",
                    "wss:",
                    "localhost:*",
                    "127.0.0.1:*",
                ]
            )
            csp.font_src(["'self'", "data:", "http:", "https:"])
            csp.object_src(["'none'"])
            csp.media_src(["'self'", "http:", "https:"])
            csp.frame_src(["'self'", "localhost:*", "127.0.0.1:*"])
            csp.frame_ancestors(["'self'"])
            csp.form_action(["'self'"])
            csp.base_uri(["'self'"])

        return csp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add comprehensive security headers to HTTP responses.

    Includes:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(self, app: ASGIApp, config: SecurityHeadersConfig | None = None):
        super().__init__(app)
        self.config = config or SecurityHeadersConfig()
        self.nonce_store: dict[str, str] = {}  # In production, use Redis

    def generate_nonce(self) -> str:
        """Generate a cryptographic nonce for CSP."""
        return secrets.token_urlsafe(self.config.nonce_length)

    def get_security_headers(
        self, request: Request, nonce: str | None = None
    ) -> dict[str, str]:
        """Get all security headers for the request."""
        headers = {}

        # Content Security Policy
        if self.config.enable_csp:
            csp_policy = self.config.get_csp_policy(nonce)
            csp_header = csp_policy.build()

            if self.config.csp_report_uri:
                csp_header += f"; report-uri {self.config.csp_report_uri}"

            if self.config.csp_report_only:
                headers["Content-Security-Policy-Report-Only"] = csp_header
            else:
                headers["Content-Security-Policy"] = csp_header

        # HTTP Strict Transport Security (HSTS)
        if self.config.environment == "production":
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # X-Content-Type-Options
        headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (deprecated but still used by some browsers)
        headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (Feature Policy replacement)
        permissions_policy = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "accelerometer=()",
            "gyroscope=()",
            "fullscreen=(self)",
            "autoplay=()",
        ]
        headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # Cross-Origin Embedder Policy
        headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # Cross-Origin Opener Policy
        headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin Resource Policy
        headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Clear-Site-Data (for logout endpoints)
        if request.url.path.endswith("/logout"):
            headers["Clear-Site-Data"] = '"cache", "cookies", "storage"'

        # Expect-CT (Certificate Transparency)
        if self.config.environment == "production":
            headers["Expect-CT"] = "max-age=86400, enforce"

        return headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers to response."""
        try:
            # Generate nonce for this request
            nonce = None
            if self.config.use_nonce:
                nonce = self.generate_nonce()
                # Store nonce in request state for use in templates
                request.state.csp_nonce = nonce

            # Process the request
            response = await call_next(request)

            # Add security headers
            security_headers = self.get_security_headers(request, nonce)

            for header_name, header_value in security_headers.items():
                response.headers[header_name] = header_value

            # Log security headers application
            logger.debug(
                "Security headers applied",
                path=request.url.path,
                headers_count=len(security_headers),
                has_nonce=nonce is not None,
            )

            return response

        except Exception as e:
            logger.error(f"Security headers middleware error: {str(e)}")
            # Continue without security headers rather than breaking the request
            return await call_next(request)


class CSPReportHandler:
    """Handler for CSP violation reports."""

    def __init__(self):
        self.violation_log: list[dict[str, Any]] = []

    async def handle_csp_report(self, request: Request) -> JSONResponse:
        """Handle CSP violation report."""
        try:
            report_data = await request.json()

            # Extract CSP violation details
            csp_report = report_data.get("csp-report", {})

            violation_info = {
                "timestamp": str(request.headers.get("date", "")),
                "user_agent": request.headers.get("user-agent", ""),
                "document_uri": csp_report.get("document-uri", ""),
                "violated_directive": csp_report.get("violated-directive", ""),
                "blocked_uri": csp_report.get("blocked-uri", ""),
                "original_policy": csp_report.get("original-policy", ""),
                "source_file": csp_report.get("source-file", ""),
                "line_number": csp_report.get("line-number", ""),
                "column_number": csp_report.get("column-number", ""),
                "ip_address": request.client.host if request.client else "unknown",
            }

            # Store violation (in production, send to SIEM)
            self.violation_log.append(violation_info)

            # Log the violation
            logger.warning(
                "CSP violation reported",
                violated_directive=violation_info["violated_directive"],
                blocked_uri=violation_info["blocked_uri"],
                document_uri=violation_info["document_uri"],
                user_agent=violation_info["user_agent"][:100],
            )

            # Check for potential attacks
            await self._analyze_violation(violation_info)

            return JSONResponse({"status": "received"}, status_code=204)

        except Exception as e:
            logger.error(f"Failed to process CSP report: {str(e)}")
            return JSONResponse({"error": "Failed to process report"}, status_code=400)

    async def _analyze_violation(self, violation: dict[str, Any]) -> None:
        """Analyze CSP violation for potential security issues."""
        try:
            blocked_uri = violation.get("blocked_uri", "").lower()
            violated_directive = violation.get("violated_directive", "").lower()

            # Check for common attack patterns
            suspicious_patterns = [
                "javascript:",
                "data:",
                "eval",
                "inline",
                "malicious",
                "attack",
                "xss",
                "injection",
            ]

            is_suspicious = any(
                pattern in blocked_uri for pattern in suspicious_patterns
            )

            if is_suspicious or "script-src" in violated_directive:
                logger.warning(
                    "Suspicious CSP violation detected",
                    violation=violation,
                    severity="high",
                )

                # In production, trigger incident response
                # await incident_response_system.create_incident(...)

        except Exception as e:
            logger.error(f"CSP violation analysis failed: {str(e)}")

    def get_violation_stats(self) -> dict[str, Any]:
        """Get CSP violation statistics."""
        total_violations = len(self.violation_log)

        if total_violations == 0:
            return {"total_violations": 0}

        # Analyze violations
        directive_counts = {}
        uri_counts = {}

        for violation in self.violation_log:
            directive = violation.get("violated_directive", "unknown")
            uri = violation.get("blocked_uri", "unknown")

            directive_counts[directive] = directive_counts.get(directive, 0) + 1
            uri_counts[uri] = uri_counts.get(uri, 0) + 1

        return {
            "total_violations": total_violations,
            "top_violated_directives": sorted(
                directive_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "top_blocked_uris": sorted(
                uri_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "recent_violations": self.violation_log[-10:],  # Last 10 violations
        }


# Global instances
security_headers_config = SecurityHeadersConfig()
csp_report_handler = CSPReportHandler()


def get_csp_nonce(request: Request) -> str | None:
    """Get CSP nonce from request state."""
    return getattr(request.state, "csp_nonce", None)


def create_security_headers_middleware(
    config: SecurityHeadersConfig | None = None,
) -> SecurityHeadersMiddleware:
    """Create security headers middleware with optional custom config."""
    return SecurityHeadersMiddleware(app=None, config=config or security_headers_config)
