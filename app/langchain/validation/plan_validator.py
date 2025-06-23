"""
Plan validation and quality assurance for WebAgent execution plans.

This module provides comprehensive validation of AI-generated execution plans
to ensure safety, feasibility, and quality before execution.
"""

import re
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class PlanValidator:
    """
    Comprehensive validator for WebAgent execution plans.

    This class performs safety checks, feasibility analysis, and quality
    assessment of AI-generated execution plans.
    """

    def __init__(self):
        """Initialize the plan validator."""
        self.logger = structlog.get_logger(self.__class__.__name__)

        # Safety patterns to flag
        self.dangerous_patterns = [
            r"delete.*all",
            r"remove.*everything",
            r"clear.*data",
            r"format.*drive",
            r"drop.*table",
            r"truncate.*",
            r"rm\s+-rf",
            r"del\s+/s",
        ]

        # Sensitive action patterns
        self.sensitive_patterns = [
            r"payment",
            r"credit.*card",
            r"bank.*account",
            r"social.*security",
            r"password.*change",
            r"delete.*account",
            r"purchase",
            r"buy.*now",
            r"checkout",
            r"transfer.*money",
        ]

    async def validate_execution_plan(
        self, execution_plan: dict[str, Any], webpage_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform comprehensive validation of an execution plan.

        Args:
            execution_plan: The execution plan to validate
            webpage_data: Parsed webpage data for context

        Returns:
            Validation result with scores, issues, and recommendations
        """
        try:
            self.logger.info("Starting execution plan validation")

            # Initialize validation result
            validation_result = {
                "overall_status": "approved",
                "validation_timestamp": datetime.utcnow().isoformat(),
                "scores": {
                    "safety_score": 1.0,
                    "feasibility_score": 1.0,
                    "quality_score": 1.0,
                    "confidence_score": 0.0,
                },
                "findings": {
                    "critical_issues": [],
                    "warnings": [],
                    "recommendations": [],
                    "positive_aspects": [],
                },
                "approval_status": {
                    "requires_human_approval": False,
                    "approval_reason": "",
                    "risk_level": "low",
                },
            }

            # Perform validation checks
            await self._validate_safety(execution_plan, validation_result)
            await self._validate_feasibility(
                execution_plan, webpage_data, validation_result
            )
            await self._validate_quality(execution_plan, validation_result)
            await self._calculate_overall_scores(validation_result)
            await self._determine_approval_status(validation_result)

            self.logger.info(
                "Execution plan validation completed",
                status=validation_result["overall_status"],
                safety_score=validation_result["scores"]["safety_score"],
                feasibility_score=validation_result["scores"]["feasibility_score"],
            )

            return validation_result

        except Exception as e:
            self.logger.error("Plan validation failed", error=str(e))
            return {
                "overall_status": "rejected",
                "validation_timestamp": datetime.utcnow().isoformat(),
                "scores": {
                    "safety_score": 0.0,
                    "feasibility_score": 0.0,
                    "quality_score": 0.0,
                },
                "findings": {"critical_issues": [f"Validation error: {str(e)}"]},
                "approval_status": {
                    "requires_human_approval": True,
                    "risk_level": "high",
                },
            }

    async def _validate_safety(
        self, execution_plan: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Validate plan safety and identify potential risks."""
        safety_issues = []
        warnings = []
        safety_score = 1.0

        # Check plan metadata for safety flags
        plan_meta = execution_plan.get("execution_plan", {})
        if plan_meta.get("requires_sensitive_actions", False):
            warnings.append(
                "Plan involves sensitive actions that require careful review"
            )
            safety_score -= 0.2

        # Check action steps for dangerous patterns
        action_steps = execution_plan.get("action_steps", [])
        for step in action_steps:
            step_description = step.get("description", "").lower()
            step_name = step.get("step_name", "").lower()
            input_value = (
                step.get("input_value", "").lower() if step.get("input_value") else ""
            )

            # Check for dangerous patterns
            for pattern in self.dangerous_patterns:
                if (
                    re.search(pattern, step_description)
                    or re.search(pattern, step_name)
                    or re.search(pattern, input_value)
                ):
                    safety_issues.append(
                        f"Step {step.get('step_number')}: Contains potentially dangerous action pattern"
                    )
                    safety_score -= 0.5

            # Check for sensitive patterns
            for pattern in self.sensitive_patterns:
                if (
                    re.search(pattern, step_description)
                    or re.search(pattern, step_name)
                    or re.search(pattern, input_value)
                ):
                    warnings.append(
                        f"Step {step.get('step_number')}: Involves sensitive action requiring approval"
                    )
                    safety_score -= 0.1

            # Check for irreversible actions without confirmation
            if (
                step.get("is_critical", False)
                and not step.get("requires_confirmation", False)
                and any(
                    word in step_description
                    for word in ["delete", "remove", "clear", "submit"]
                )
            ):
                warnings.append(
                    f"Step {step.get('step_number')}: Critical action without confirmation"
                )
                safety_score -= 0.2

        # Update result
        result["scores"]["safety_score"] = max(0.0, safety_score)
        result["findings"]["critical_issues"].extend(safety_issues)
        result["findings"]["warnings"].extend(warnings)

        if safety_score > 0.8:
            result["findings"]["positive_aspects"].append(
                "Plan demonstrates good safety practices"
            )

    async def _validate_feasibility(
        self,
        execution_plan: dict[str, Any],
        webpage_data: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Validate plan feasibility against webpage data."""
        feasibility_issues = []
        warnings = []
        feasibility_score = 1.0

        interactive_elements = webpage_data.get("interactive_elements", [])
        element_selectors = {
            elem.get("selector", ""): elem for elem in interactive_elements
        }

        action_steps = execution_plan.get("action_steps", [])

        for step in action_steps:
            step_num = step.get("step_number", 0)
            target_selector = step.get("target_selector", "")
            action_type = step.get("action_type", "")
            confidence = step.get("confidence_score", 0.0)

            # Check if target element exists
            if target_selector and target_selector not in element_selectors:
                # Try to find similar selectors
                similar_found = False
                for selector in element_selectors.keys():
                    if target_selector in selector or selector in target_selector:
                        warnings.append(
                            f"Step {step_num}: Target selector may need adjustment"
                        )
                        feasibility_score -= 0.1
                        similar_found = True
                        break

                if not similar_found:
                    feasibility_issues.append(
                        f"Step {step_num}: Target element not found on page"
                    )
                    feasibility_score -= 0.3

            # Check action type compatibility
            if target_selector in element_selectors:
                element = element_selectors[target_selector]
                element_type = element.get("type", "")

                # Validate action-element compatibility
                if not self._is_action_compatible(action_type, element_type):
                    feasibility_issues.append(
                        f"Step {step_num}: Action '{action_type}' incompatible with element type '{element_type}'"
                    )
                    feasibility_score -= 0.2

            # Check confidence scores
            if confidence < 0.5:
                warnings.append(
                    f"Step {step_num}: Low confidence score ({confidence:.2f})"
                )
                feasibility_score -= 0.1
            elif confidence < 0.3:
                feasibility_issues.append(
                    f"Step {step_num}: Very low confidence score ({confidence:.2f})"
                )
                feasibility_score -= 0.2

        # Update result
        result["scores"]["feasibility_score"] = max(0.0, feasibility_score)
        result["findings"]["critical_issues"].extend(feasibility_issues)
        result["findings"]["warnings"].extend(warnings)

        if feasibility_score > 0.8:
            result["findings"]["positive_aspects"].append(
                "Plan shows high feasibility with available elements"
            )

    async def _validate_quality(
        self, execution_plan: dict[str, Any], result: dict[str, Any]
    ) -> None:
        """Validate plan quality and structure."""
        quality_issues = []
        warnings = []
        recommendations = []
        quality_score = 1.0

        plan_meta = execution_plan.get("execution_plan", {})
        action_steps = execution_plan.get("action_steps", [])

        # Check plan completeness
        required_fields = ["title", "description", "original_goal"]
        for field in required_fields:
            if not plan_meta.get(field):
                quality_issues.append(f"Missing required field: {field}")
                quality_score -= 0.2

        # Check action steps structure
        if not action_steps:
            quality_issues.append("Plan contains no action steps")
            quality_score -= 0.5
        else:
            # Check step numbering
            expected_step = 1
            for step in action_steps:
                if step.get("step_number") != expected_step:
                    warnings.append(
                        f"Step numbering inconsistency at step {expected_step}"
                    )
                    quality_score -= 0.1
                expected_step += 1

            # Check for missing critical step information
            for step in action_steps:
                step_num = step.get("step_number", 0)
                required_step_fields = ["step_name", "description", "action_type"]

                for field in required_step_fields:
                    if not step.get(field):
                        quality_issues.append(f"Step {step_num}: Missing {field}")
                        quality_score -= 0.1

                # Check timeout values
                timeout = step.get("timeout_seconds", 30)
                if timeout < 5 or timeout > 300:
                    warnings.append(
                        f"Step {step_num}: Unusual timeout value ({timeout}s)"
                    )
                    quality_score -= 0.05

        # Check for error handling
        has_error_handling = any(
            step.get("fallback_actions") or step.get("retry_count", 0) > 0
            for step in action_steps
        )

        if not has_error_handling:
            recommendations.append(
                "Consider adding error handling and fallback strategies"
            )
            quality_score -= 0.1

        # Check for validation criteria
        has_validation = any(
            step.get("expected_outcome") or step.get("validation_criteria")
            for step in action_steps
        )

        if not has_validation:
            recommendations.append("Add validation criteria to verify step success")
            quality_score -= 0.1

        # Update result
        result["scores"]["quality_score"] = max(0.0, quality_score)
        result["findings"]["critical_issues"].extend(quality_issues)
        result["findings"]["warnings"].extend(warnings)
        result["findings"]["recommendations"].extend(recommendations)

        if quality_score > 0.8:
            result["findings"]["positive_aspects"].append(
                "Plan demonstrates high quality structure"
            )

    def _is_action_compatible(self, action_type: str, element_type: str) -> bool:
        """Check if an action type is compatible with an element type."""
        compatibility_map = {
            "click": ["button", "link", "checkbox", "radio", "submit"],
            "type": ["input", "textarea"],
            "select": ["select", "dropdown"],
            "upload": ["input"],  # file input
            "submit": ["button", "submit"],
            "navigate": ["link"],
            "hover": ["button", "link", "div", "span"],
            "scroll": ["div", "body", "window"],
            "wait": ["any"],  # Wait can be used with any element
            "verify": ["any"],  # Verification can be done on any element
            "extract": ["any"],  # Extraction can be done on any element
            "screenshot": ["any"],  # Screenshots can be taken of any element
        }

        compatible_elements = compatibility_map.get(action_type.lower(), [])
        return (
            "any" in compatible_elements or element_type.lower() in compatible_elements
        )

    async def _calculate_overall_scores(self, result: dict[str, Any]) -> None:
        """Calculate overall validation scores."""
        scores = result["scores"]

        # Calculate weighted overall confidence
        safety_weight = 0.4
        feasibility_weight = 0.4
        quality_weight = 0.2

        overall_confidence = (
            scores["safety_score"] * safety_weight
            + scores["feasibility_score"] * feasibility_weight
            + scores["quality_score"] * quality_weight
        )

        scores["confidence_score"] = overall_confidence

        # Determine overall status
        if (
            scores["safety_score"] < 0.5
            or len(result["findings"]["critical_issues"]) > 0
        ):
            result["overall_status"] = "rejected"
        elif overall_confidence < 0.6:
            result["overall_status"] = "needs_revision"
        else:
            result["overall_status"] = "approved"

    async def _determine_approval_status(self, result: dict[str, Any]) -> None:
        """Determine if human approval is required."""
        approval_status = result["approval_status"]
        scores = result["scores"]
        findings = result["findings"]

        # Require approval for safety concerns
        if scores["safety_score"] < 0.8:
            approval_status["requires_human_approval"] = True
            approval_status["approval_reason"] = "Safety concerns detected"
            approval_status["risk_level"] = "high"

        # Require approval for low feasibility
        elif scores["feasibility_score"] < 0.6:
            approval_status["requires_human_approval"] = True
            approval_status["approval_reason"] = "Low feasibility score"
            approval_status["risk_level"] = "medium"

        # Require approval for critical issues
        elif len(findings["critical_issues"]) > 0:
            approval_status["requires_human_approval"] = True
            approval_status["approval_reason"] = "Critical issues found"
            approval_status["risk_level"] = "high"

        # Require approval for sensitive actions
        elif any("sensitive" in warning.lower() for warning in findings["warnings"]):
            approval_status["requires_human_approval"] = True
            approval_status["approval_reason"] = "Sensitive actions detected"
            approval_status["risk_level"] = "medium"

        else:
            approval_status["requires_human_approval"] = False
            approval_status["approval_reason"] = (
                "Plan meets safety and quality standards"
            )
            approval_status["risk_level"] = "low"
