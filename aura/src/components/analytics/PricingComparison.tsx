/**
 * Pricing Comparison Component
 *
 * Strategic pricing comparison with conversion-optimized design.
 * Showcases 2025 pricing model with clear value demonstration.
 */

import React, { useState } from "react";
import {
  Check,
  Crown,
  Zap,
  Eye,
  Brain,
  Target,
  Shield,
  Sparkles,
  TrendingUp,
  Users,
  ArrowRight,
} from "lucide-react";
import { analyticsService } from "../../services";
import { cn } from "../../lib/utils";

interface PricingTier {
  id: string;
  name: string;
  description: string;
  monthlyPrice: number;
  annualPrice?: number;
  annualDiscount?: number;
  popular?: boolean;
  enterprise?: boolean;
  features: string[];
  limits: {
    parses: number | string;
    plans: number | string;
    executions: number | string;
    storage: number | string;
  };
  icon: React.ReactNode;
  color: string;
  savings?: string;
}

const PRICING_TIERS: PricingTier[] = [
  {
    id: "free",
    name: "Free Tier",
    description:
      "Perfect for exploring WebAgent's revolutionary AI capabilities",
    monthlyPrice: 0,
    features: [
      "Basic website parsing",
      "Limited AI planning",
      "Basic automation",
      "Community support",
      "Basic analytics",
    ],
    limits: {
      parses: 200,
      plans: 20,
      executions: 10,
      storage: "1 GB",
    },
    icon: <Sparkles className="h-6 w-6" />,
    color: "gray",
  },
  {
    id: "reader_pro",
    name: "Reader Pro",
    description: "Unlimited website intelligence with advanced analytics",
    monthlyPrice: 129,
    annualPrice: 1290,
    annualDiscount: 15,
    features: [
      "Unlimited website parsing",
      "Advanced parsing analytics",
      "Performance optimization",
      "Priority support",
      "Trend analysis",
      "Element accuracy insights",
    ],
    limits: {
      parses: "Unlimited",
      plans: 20,
      executions: 10,
      storage: "10 GB",
    },
    icon: <Eye className="h-6 w-6" />,
    color: "blue",
  },
  {
    id: "planner_pro",
    name: "Planner Pro",
    description: "Unlimited AI reasoning with workflow analytics",
    monthlyPrice: 179,
    annualPrice: 1790,
    annualDiscount: 15,
    features: [
      "Unlimited AI planning",
      "Workflow analytics",
      "Confidence scoring",
      "Goal completion tracking",
      "AI reasoning performance",
      "Priority support",
    ],
    limits: {
      parses: 200,
      plans: "Unlimited",
      executions: 10,
      storage: "15 GB",
    },
    icon: <Brain className="h-6 w-6" />,
    color: "purple",
  },
  {
    id: "actor_pro",
    name: "Actor Pro",
    description: "Unlimited automation with execution analytics",
    monthlyPrice: 229,
    annualPrice: 2290,
    annualDiscount: 15,
    features: [
      "Unlimited automation",
      "Execution analytics",
      "Error monitoring",
      "ROI calculations",
      "Success metrics",
      "Priority support",
    ],
    limits: {
      parses: 200,
      plans: 20,
      executions: "Unlimited",
      storage: "25 GB",
    },
    icon: <Zap className="h-6 w-6" />,
    color: "green",
  },
  {
    id: "complete_platform",
    name: "Complete Platform",
    description: "All AI components with unified analytics - 40% savings!",
    monthlyPrice: 399,
    annualPrice: 3990,
    annualDiscount: 15,
    popular: true,
    savings: "Save $138/mo vs individual tools",
    features: [
      "All Reader Pro features",
      "All Planner Pro features",
      "All Actor Pro features",
      "Unified cross-tool analytics",
      "Integration monitoring",
      "Advanced success metrics",
      "Priority support",
      "40% savings vs individual",
    ],
    limits: {
      parses: "Unlimited",
      plans: "Unlimited",
      executions: "Unlimited",
      storage: "100 GB",
    },
    icon: <Crown className="h-6 w-6" />,
    color: "yellow",
  },
  {
    id: "enterprise_platform",
    name: "Enterprise Platform",
    description: "Complete enterprise solution with dedicated support",
    monthlyPrice: 1499,
    annualPrice: 14990,
    annualDiscount: 15,
    enterprise: true,
    features: [
      "All Complete Platform features",
      "Advanced compliance dashboards",
      "Custom branding & white-label",
      "Dedicated Customer Success Manager",
      "SLA monitoring & guarantees",
      "Early access to features",
      "Custom integrations",
      "Advanced security features",
    ],
    limits: {
      parses: "Unlimited",
      plans: "Unlimited",
      executions: "Unlimited",
      storage: "Unlimited",
    },
    icon: <Shield className="h-6 w-6" />,
    color: "indigo",
  },
];

interface PricingCardProps {
  tier: PricingTier;
  billingCycle: "monthly" | "annual";
  currentTier?: string;
  onSelect: (tierId: string) => void;
}

const PricingCard: React.FC<PricingCardProps> = ({
  tier,
  billingCycle,
  currentTier,
  onSelect,
}) => {
  const isCurrentTier = currentTier === tier.id;
  const price =
    billingCycle === "annual" && tier.annualPrice
      ? tier.annualPrice / 12
      : tier.monthlyPrice;

  const colorClasses = {
    gray: "border-gray-200 dark:border-gray-700",
    blue: "border-blue-200 dark:border-blue-800",
    purple: "border-purple-200 dark:border-purple-800",
    green: "border-green-200 dark:border-green-800",
    yellow:
      "border-yellow-200 dark:border-yellow-800 ring-2 ring-yellow-400 ring-opacity-50",
    indigo: "border-indigo-200 dark:border-indigo-800",
  };

  const iconColorClasses = {
    gray: "bg-gray-500",
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    indigo: "bg-indigo-500",
  };

  return (
    <div
      className={cn(
        "card relative transition-all duration-200 hover:shadow-lg",
        colorClasses[tier.color as keyof typeof colorClasses],
        tier.popular && "transform scale-105",
      )}
    >
      {tier.popular && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <div className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-yellow-500 text-white font-medium">
            <Crown className="h-4 w-4 mr-1" />
            Most Popular
          </div>
        </div>
      )}

      {tier.enterprise && (
        <div className="absolute -top-3 right-4">
          <div className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-500 text-white font-medium">
            <Users className="h-4 w-4 mr-1" />
            Enterprise
          </div>
        </div>
      )}

      <div className="card-body">
        {/* Header */}
        <div className="text-center mb-6">
          <div
            className={cn(
              "inline-flex p-3 rounded-lg mb-4",
              iconColorClasses[tier.color as keyof typeof iconColorClasses],
            )}
          >
            <div className="text-white">{tier.icon}</div>
          </div>

          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            {tier.name}
          </h3>

          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            {tier.description}
          </p>

          {tier.savings && (
            <div className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 mb-4">
              <TrendingUp className="h-3 w-3 mr-1" />
              {tier.savings}
            </div>
          )}

          <div className="mb-4">
            <div className="flex items-baseline justify-center">
              <span className="text-3xl font-bold text-gray-900 dark:text-white">
                ${price.toFixed(0)}
              </span>
              <span className="text-gray-500 dark:text-gray-400 ml-1">
                /month
              </span>
            </div>

            {billingCycle === "annual" && tier.annualDiscount && (
              <p className="text-sm text-green-600 dark:text-green-400 mt-1">
                Save {tier.annualDiscount}% annually
              </p>
            )}
          </div>
        </div>

        {/* Usage Limits */}
        <div className="mb-6 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">
            Usage Limits
          </h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">Parses:</span>
              <span className="font-medium text-gray-900 dark:text-white ml-1">
                {tier.limits.parses}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Plans:</span>
              <span className="font-medium text-gray-900 dark:text-white ml-1">
                {tier.limits.plans}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">
                Executions:
              </span>
              <span className="font-medium text-gray-900 dark:text-white ml-1">
                {tier.limits.executions}
              </span>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Storage:</span>
              <span className="font-medium text-gray-900 dark:text-white ml-1">
                {tier.limits.storage}
              </span>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="mb-6">
          <h4 className="font-medium text-gray-900 dark:text-white mb-3">
            Features
          </h4>
          <ul className="space-y-2">
            {tier.features.map((feature, index) => (
              <li key={index} className="flex items-start space-x-2">
                <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {feature}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Action Button */}
        <button
          onClick={() => onSelect(tier.id)}
          disabled={isCurrentTier}
          className={cn(
            "w-full btn flex items-center justify-center space-x-2",
            isCurrentTier
              ? "btn-secondary opacity-50 cursor-not-allowed"
              : tier.popular
                ? "btn-primary"
                : "btn-secondary",
          )}
        >
          {isCurrentTier ? (
            <span>Current Plan</span>
          ) : (
            <>
              <span>
                {tier.monthlyPrice === 0 ? "Get Started" : "Upgrade Now"}
              </span>
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

interface PricingComparisonProps {
  currentTier?: string;
  onUpgrade?: (tierId: string) => void;
}

export const PricingComparison: React.FC<PricingComparisonProps> = ({
  currentTier = "free",
  onUpgrade,
}) => {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">(
    "monthly",
  );

  const handleTierSelect = async (tierId: string) => {
    // Track selection event
    await analyticsService.trackEvent("pricing_tier_selected", {
      selected_tier: tierId,
      current_tier: currentTier,
      billing_cycle: billingCycle,
    });

    if (onUpgrade) {
      onUpgrade(tierId);
    } else {
      // Default upgrade flow
      window.location.href = `/billing/upgrade?tier=${tierId}&cycle=${billingCycle}`;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Choose Your WebAgent Plan
        </h2>
        <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
          Unlock the full potential of AI-powered automation
        </p>

        {/* Billing Toggle */}
        <div className="inline-flex items-center p-1 rounded-lg bg-gray-100 dark:bg-gray-800">
          <button
            onClick={() => setBillingCycle("monthly")}
            className={cn(
              "px-4 py-2 rounded-md text-sm font-medium transition-all",
              billingCycle === "monthly"
                ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow"
                : "text-gray-600 dark:text-gray-400",
            )}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingCycle("annual")}
            className={cn(
              "px-4 py-2 rounded-md text-sm font-medium transition-all",
              billingCycle === "annual"
                ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow"
                : "text-gray-600 dark:text-gray-400",
            )}
          >
            Annual
            <span className="ml-1 text-xs text-green-600 dark:text-green-400">
              Save 15%
            </span>
          </button>
        </div>
      </div>

      {/* Pricing Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {PRICING_TIERS.map((tier) => (
          <PricingCard
            key={tier.id}
            tier={tier}
            billingCycle={billingCycle}
            currentTier={currentTier}
            onSelect={handleTierSelect}
          />
        ))}
      </div>

      {/* Value Proposition */}
      <div className="text-center py-8 border-t border-gray-200 dark:border-gray-700">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Why Choose WebAgent?
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          <div className="text-center">
            <Target className="h-8 w-8 text-blue-500 mx-auto mb-2" />
            <h4 className="font-medium text-gray-900 dark:text-white mb-1">
              97% Success Rate
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Industry-leading automation accuracy
            </p>
          </div>
          <div className="text-center">
            <TrendingUp className="h-8 w-8 text-green-500 mx-auto mb-2" />
            <h4 className="font-medium text-gray-900 dark:text-white mb-1">
              3x ROI Average
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Proven return on investment
            </p>
          </div>
          <div className="text-center">
            <Shield className="h-8 w-8 text-purple-500 mx-auto mb-2" />
            <h4 className="font-medium text-gray-900 dark:text-white mb-1">
              Enterprise Security
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              SOC2 compliant with Zero Trust
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
