"""
Planning memory system for WebAgent AI planning.

This module provides memory capabilities for the planning agent to learn from
past executions and improve future plan generation.
"""

from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class PlanningMemory:
    """
    Memory system for WebAgent planning agent.

    This class manages the agent's memory of successful patterns, failure cases,
    and domain-specific knowledge to improve planning over time.
    """

    def __init__(self):
        """Initialize the planning memory system."""
        self.successful_patterns = {}  # Store successful plan patterns
        self.failure_analysis = {}  # Store failure patterns to avoid
        self.domain_knowledge = {}  # Website-specific knowledge
        self.element_patterns = {}  # Common element identification patterns
        self.logger = structlog.get_logger(self.__class__.__name__)

    async def store_planning_outcome(
        self,
        plan_id: int,
        goal: str,
        webpage_url: str,
        outcome: str,
        confidence_score: float,
        execution_success: bool | None = None,
        feedback: str | None = None,
        execution_time: int | None = None,
    ) -> None:
        """
        Store the outcome of a planning session for future learning.

        Args:
            plan_id: Unique identifier for the execution plan
            goal: User's original goal
            webpage_url: URL of the webpage that was analyzed
            outcome: Description of the planning outcome
            confidence_score: Confidence score of the generated plan
            execution_success: Whether the plan executed successfully (if known)
            feedback: User feedback on the plan quality
            execution_time: Time taken to execute the plan (if executed)
        """
        try:
            # Extract domain from URL
            domain = self._extract_domain(webpage_url)

            # Create outcome record
            outcome_record = {
                "plan_id": plan_id,
                "goal": goal,
                "webpage_url": webpage_url,
                "domain": domain,
                "outcome": outcome,
                "confidence_score": confidence_score,
                "execution_success": execution_success,
                "feedback": feedback,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
                "goal_category": self._categorize_goal(goal),
            }

            # Store in appropriate memory category
            if execution_success is True or confidence_score > 0.8:
                await self._store_successful_pattern(outcome_record)
            elif execution_success is False or confidence_score < 0.3:
                await self._store_failure_pattern(outcome_record)

            # Update domain knowledge
            await self._update_domain_knowledge(domain, outcome_record)

            self.logger.info(
                "Stored planning outcome",
                plan_id=plan_id,
                domain=domain,
                success=execution_success,
                confidence=confidence_score,
            )

        except Exception as e:
            self.logger.error("Failed to store planning outcome", error=str(e))

    async def retrieve_similar_plans(
        self, goal: str, webpage_url: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Retrieve similar successful plans for reference.

        Args:
            goal: Current user goal
            webpage_url: Current webpage URL
            limit: Maximum number of similar plans to return

        Returns:
            List of similar successful plan records
        """
        try:
            domain = self._extract_domain(webpage_url)
            goal_category = self._categorize_goal(goal)

            similar_plans = []

            # Search successful patterns
            for pattern_key, patterns in self.successful_patterns.items():
                for pattern in patterns:
                    similarity_score = self._calculate_similarity(
                        goal,
                        goal_category,
                        domain,
                        pattern["goal"],
                        pattern["goal_category"],
                        pattern["domain"],
                    )

                    if similarity_score > 0.5:  # Threshold for similarity
                        pattern["similarity_score"] = similarity_score
                        similar_plans.append(pattern)

            # Sort by similarity and return top results
            similar_plans.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_plans[:limit]

        except Exception as e:
            self.logger.error("Failed to retrieve similar plans", error=str(e))
            return []

    async def get_domain_insights(self, webpage_url: str) -> dict[str, Any]:
        """
        Get domain-specific insights and patterns.

        Args:
            webpage_url: URL to get insights for

        Returns:
            Domain-specific knowledge and patterns
        """
        try:
            domain = self._extract_domain(webpage_url)

            if domain not in self.domain_knowledge:
                return {
                    "domain": domain,
                    "common_patterns": [],
                    "success_rate": 0.0,
                    "avg_confidence": 0.0,
                    "recommendations": [],
                }

            domain_data = self.domain_knowledge[domain]

            return {
                "domain": domain,
                "common_patterns": domain_data.get("common_patterns", []),
                "success_rate": domain_data.get("success_rate", 0.0),
                "avg_confidence": domain_data.get("avg_confidence", 0.0),
                "total_plans": domain_data.get("total_plans", 0),
                "recommendations": domain_data.get("recommendations", []),
                "last_updated": domain_data.get("last_updated"),
            }

        except Exception as e:
            self.logger.error("Failed to get domain insights", error=str(e))
            return {}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return "unknown"

    def _categorize_goal(self, goal: str) -> str:
        """Categorize the goal into common automation patterns."""
        goal_lower = goal.lower()

        if any(word in goal_lower for word in ["login", "sign in", "authenticate"]):
            return "authentication"
        elif any(
            word in goal_lower for word in ["register", "sign up", "create account"]
        ):
            return "registration"
        elif any(word in goal_lower for word in ["search", "find", "look for"]):
            return "search"
        elif any(word in goal_lower for word in ["submit", "send", "post", "form"]):
            return "form_submission"
        elif any(word in goal_lower for word in ["navigate", "go to", "visit"]):
            return "navigation"
        elif any(word in goal_lower for word in ["download", "save", "export"]):
            return "download"
        elif any(word in goal_lower for word in ["upload", "attach", "import"]):
            return "upload"
        else:
            return "general"

    def _calculate_similarity(
        self,
        goal1: str,
        category1: str,
        domain1: str,
        goal2: str,
        category2: str,
        domain2: str,
    ) -> float:
        """Calculate similarity score between two planning contexts."""
        similarity = 0.0

        # Domain similarity (highest weight)
        if domain1 == domain2:
            similarity += 0.4

        # Category similarity
        if category1 == category2:
            similarity += 0.3

        # Goal text similarity (simple word overlap)
        words1 = set(goal1.lower().split())
        words2 = set(goal2.lower().split())
        if words1 and words2:
            word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
            similarity += 0.3 * word_overlap

        return min(similarity, 1.0)

    async def _store_successful_pattern(self, outcome_record: dict[str, Any]) -> None:
        """Store a successful planning pattern."""
        category = outcome_record["goal_category"]

        if category not in self.successful_patterns:
            self.successful_patterns[category] = []

        self.successful_patterns[category].append(outcome_record)

        # Keep only recent successful patterns (last 100 per category)
        if len(self.successful_patterns[category]) > 100:
            self.successful_patterns[category] = self.successful_patterns[category][
                -100:
            ]

    async def _store_failure_pattern(self, outcome_record: dict[str, Any]) -> None:
        """Store a failure pattern to avoid in the future."""
        category = outcome_record["goal_category"]

        if category not in self.failure_analysis:
            self.failure_analysis[category] = []

        self.failure_analysis[category].append(outcome_record)

        # Keep only recent failures (last 50 per category)
        if len(self.failure_analysis[category]) > 50:
            self.failure_analysis[category] = self.failure_analysis[category][-50:]

    async def _update_domain_knowledge(
        self, domain: str, outcome_record: dict[str, Any]
    ) -> None:
        """Update domain-specific knowledge."""
        if domain not in self.domain_knowledge:
            self.domain_knowledge[domain] = {
                "total_plans": 0,
                "successful_plans": 0,
                "total_confidence": 0.0,
                "common_patterns": [],
                "recommendations": [],
                "last_updated": None,
            }

        domain_data = self.domain_knowledge[domain]
        domain_data["total_plans"] += 1
        domain_data["total_confidence"] += outcome_record["confidence_score"]

        if outcome_record.get("execution_success"):
            domain_data["successful_plans"] += 1

        # Calculate success rate and average confidence
        domain_data["success_rate"] = (
            domain_data["successful_plans"] / domain_data["total_plans"]
        )
        domain_data["avg_confidence"] = (
            domain_data["total_confidence"] / domain_data["total_plans"]
        )
        domain_data["last_updated"] = datetime.utcnow().isoformat()

        # Update recommendations based on patterns
        self._update_domain_recommendations(domain_data, outcome_record)

    def _update_domain_recommendations(
        self, domain_data: dict[str, Any], outcome_record: dict[str, Any]
    ) -> None:
        """Update domain-specific recommendations."""
        recommendations = domain_data.get("recommendations", [])

        # Add recommendations based on success patterns
        if (
            outcome_record.get("execution_success")
            and outcome_record["confidence_score"] > 0.8
        ):
            goal_category = outcome_record["goal_category"]
            rec = f"High success rate for {goal_category} tasks on this domain"
            if rec not in recommendations:
                recommendations.append(rec)

        # Add warnings based on failure patterns
        elif outcome_record.get("execution_success") is False:
            goal_category = outcome_record["goal_category"]
            rec = f"Exercise caution with {goal_category} tasks on this domain"
            if rec not in recommendations:
                recommendations.append(rec)

        # Keep only recent recommendations
        domain_data["recommendations"] = recommendations[-10:]
