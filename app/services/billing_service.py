"""
Billing Service

Manages billing, payments, and subscription lifecycle for WebAgent's revenue-optimized pricing.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import BillingInfo
from app.services.subscription_service import SubscriptionService

logger = structlog.get_logger(__name__)


class BillingService:
    """
    Billing and payment management service for subscription lifecycle.
    """

    def __init__(self):
        self.subscription_service = SubscriptionService()

    async def get_billing_info(self, db: AsyncSession, user_id: int) -> BillingInfo:
        """
        Get comprehensive billing information for the user.
        """

        # Get current subscription
        subscription = await self.subscription_service.get_user_subscription(
            db, user_id
        )

        # Generate sample billing data (would integrate with Stripe/payment processor)
        recent_invoices = await self._get_recent_invoices(user_id)
        payment_history = await self._get_payment_history(user_id)

        # Calculate next charge
        next_charge_amount = subscription.monthly_cost
        next_charge_date = subscription.next_billing_date

        # Account credits and discounts
        account_credits = 0.0
        active_discounts = []

        # Add annual discount if applicable
        if subscription.annual_discount > 0:
            active_discounts.append(
                {
                    "type": "annual_discount",
                    "description": f"{subscription.annual_discount*100:.0f}% Annual Discount",
                    "amount": subscription.monthly_cost * subscription.annual_discount,
                }
            )

        return BillingInfo(
            subscription=subscription,
            payment_method_type="card",  # Sample
            last_four_digits="4242",  # Sample
            recent_invoices=recent_invoices,
            payment_history=payment_history,
            next_charge_amount=next_charge_amount,
            next_charge_date=next_charge_date,
            account_credits=account_credits,
            active_discounts=active_discounts,
        )

    async def _get_recent_invoices(self, user_id: int) -> list[dict[str, Any]]:
        """
        Get recent invoices for the user.
        """

        # Sample invoice data (would query from billing system)
        return [
            {
                "id": "inv_001",
                "date": "2025-06-01",
                "amount": 0.0,
                "status": "paid",
                "description": "Free Tier - No Charge",
                "download_url": None,
            }
        ]

    async def _get_payment_history(self, user_id: int) -> list[dict[str, Any]]:
        """
        Get payment history for the user.
        """

        # Sample payment history (would query from billing system)
        return [
            {
                "id": "pay_001",
                "date": "2025-06-01",
                "amount": 0.0,
                "status": "succeeded",
                "description": "Free Tier - No Charge",
                "method": "N/A",
            }
        ]

    async def create_checkout_session(
        self,
        db: AsyncSession,
        user_id: int,
        target_tier: str,
        billing_cycle: str = "monthly",
    ) -> dict[str, str]:
        """
        Create a checkout session for subscription upgrade.
        """

        logger.info(
            "Creating checkout session",
            user_id=user_id,
            target_tier=target_tier,
            billing_cycle=billing_cycle,
        )

        # Get tier pricing
        from app.schemas.analytics import SubscriptionTier

        tier = SubscriptionTier(target_tier)
        monthly_cost = self.subscription_service.get_tier_cost(tier)

        # Calculate final amount based on billing cycle
        if billing_cycle == "annual":
            annual_discount = self.subscription_service.PRICING_TIERS[tier].get(
                "annual_discount", 0.0
            )
            final_amount = monthly_cost * 12 * (1 - annual_discount)
        else:
            final_amount = monthly_cost

        # This would integrate with Stripe or other payment processor
        # For now, return sample checkout session
        checkout_session = {
            "session_id": f"cs_{user_id}_{target_tier}_{int(datetime.utcnow().timestamp())}",
            "checkout_url": f"https://checkout.stripe.com/pay/cs_test_sample#{target_tier}",
            "amount": final_amount,
            "currency": "usd",
            "billing_cycle": billing_cycle,
        }

        logger.info(
            "Checkout session created",
            user_id=user_id,
            session_id=checkout_session["session_id"],
            amount=final_amount,
        )

        return checkout_session

    async def handle_successful_payment(
        self, db: AsyncSession, user_id: int, session_id: str, target_tier: str
    ) -> bool:
        """
        Handle successful payment and upgrade subscription.
        """

        logger.info(
            "Processing successful payment",
            user_id=user_id,
            session_id=session_id,
            target_tier=target_tier,
        )

        try:
            # Upgrade subscription
            from app.schemas.analytics import SubscriptionTier

            tier = SubscriptionTier(target_tier)
            await self.subscription_service.upgrade_subscription(db, user_id, tier)

            # Record payment (would integrate with billing system)
            await self._record_payment(user_id, session_id, target_tier)

            # Send confirmation email (would integrate with email service)
            await self._send_upgrade_confirmation(user_id, target_tier)

            logger.info(
                "Payment processed successfully", user_id=user_id, new_tier=target_tier
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to process payment",
                user_id=user_id,
                session_id=session_id,
                error=str(e),
            )
            return False

    async def _record_payment(self, user_id: int, session_id: str, target_tier: str):
        """
        Record payment in billing system.
        """

        logger.info(
            "Recording payment",
            user_id=user_id,
            session_id=session_id,
            target_tier=target_tier,
        )

        # Implementation would store payment record in database
        pass

    async def _send_upgrade_confirmation(self, user_id: int, target_tier: str):
        """
        Send upgrade confirmation email.
        """

        logger.info(
            "Sending upgrade confirmation", user_id=user_id, target_tier=target_tier
        )

        # Implementation would send email via email service
        pass

    async def calculate_proration(
        self, db: AsyncSession, user_id: int, target_tier: str
    ) -> dict[str, float]:
        """
        Calculate proration for mid-cycle upgrades.
        """

        current_subscription = await self.subscription_service.get_user_subscription(
            db, user_id
        )

        # Calculate days remaining in current period
        now = datetime.utcnow()
        days_remaining = (current_subscription.current_period_end - now).days
        days_in_period = (
            current_subscription.current_period_end
            - current_subscription.current_period_start
        ).days

        # Calculate proration
        from app.schemas.analytics import SubscriptionTier

        target_tier_enum = SubscriptionTier(target_tier)

        current_daily_rate = current_subscription.monthly_cost / days_in_period
        target_daily_rate = (
            self.subscription_service.get_tier_cost(target_tier_enum) / days_in_period
        )

        # Credit for unused current subscription
        current_credit = current_daily_rate * days_remaining

        # Charge for new subscription
        target_charge = target_daily_rate * days_remaining

        # Net amount
        net_amount = target_charge - current_credit

        return {
            "current_credit": current_credit,
            "target_charge": target_charge,
            "net_amount": max(0, net_amount),  # Never negative
            "days_remaining": days_remaining,
            "proration_date": now.isoformat(),
        }

    async def get_usage_overage_charges(
        self, db: AsyncSession, user_id: int
    ) -> dict[str, float]:
        """
        Calculate overage charges for usage beyond limits.
        """

        subscription = await self.subscription_service.get_user_subscription(
            db, user_id
        )

        # Overage rates (per unit beyond limit)
        overage_rates = {
            "parses": 0.10,  # $0.10 per parse
            "plans": 2.00,  # $2.00 per plan
            "executions": 5.00,  # $5.00 per execution
            "storage_gb": 1.00,  # $1.00 per GB
        }

        overage_charges = {}
        total_overage = 0.0

        for limit_type, limit_value in subscription.limits.items():
            if limit_value == "unlimited":
                continue

            usage_attr = f"{limit_type}_used"
            if hasattr(subscription.usage, usage_attr):
                current_usage = getattr(subscription.usage, usage_attr)

                if current_usage > limit_value:
                    overage_units = current_usage - limit_value
                    overage_cost = overage_units * overage_rates.get(limit_type, 0)
                    overage_charges[limit_type] = overage_cost
                    total_overage += overage_cost

        overage_charges["total"] = total_overage

        return overage_charges

    async def apply_discount_code(
        self, db: AsyncSession, user_id: int, discount_code: str
    ) -> dict[str, Any]:
        """
        Apply discount code to user's account.
        """

        # Sample discount codes
        discount_codes = {
            "WELCOME20": {
                "type": "percentage",
                "value": 0.20,
                "description": "20% off first month",
            },
            "SAVE50": {"type": "fixed", "value": 50.0, "description": "$50 credit"},
            "ANNUAL15": {
                "type": "percentage",
                "value": 0.15,
                "description": "15% off annual plans",
            },
        }

        if discount_code not in discount_codes:
            return {"success": False, "message": "Invalid discount code"}

        discount = discount_codes[discount_code]

        logger.info(
            "Applying discount code",
            user_id=user_id,
            discount_code=discount_code,
            discount=discount,
        )

        # Implementation would apply discount to user's account

        return {
            "success": True,
            "message": f"Discount applied: {discount['description']}",
            "discount": discount,
        }
