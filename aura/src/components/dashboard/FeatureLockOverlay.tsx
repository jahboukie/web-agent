/**
 * Feature Lock Overlay Component
 * Based on WebAgent Analytics Dashboard Wireframes
 *
 * Features:
 * - Contextual upgrade prompts for locked features
 * - Plan-specific messaging and CTAs
 * - Blur/lock visual effects
 * - Responsive design
 * - Multiple overlay styles
 */

import React from "react";
import { Lock, Crown, Star, Shield, ArrowRight, Sparkles } from "lucide-react";
import { cn } from "../../lib/utils";

export interface FeatureLockOverlayProps {
  featureName: string;
  requiredPlan:
    | "reader_pro"
    | "planner_pro"
    | "actor_pro"
    | "complete"
    | "enterprise";
  currentPlan?: string;
  onUpgradeClick: () => void;
  className?: string;
  style?: "blur" | "solid" | "gradient";
  size?: "small" | "medium" | "large";
  showBenefits?: boolean;
  customMessage?: string;
  children?: React.ReactNode;
}

const planInfo = {
  reader_pro: {
    name: "Reader Pro",
    price: "$129/mo",
    icon: Star,
    color: "from-blue-500 to-blue-600",
    benefits: [
      "Unlimited website parsing",
      "Advanced element detection",
      "Performance analytics",
    ],
  },
  planner_pro: {
    name: "Planner Pro",
    price: "$179/mo",
    icon: Crown,
    color: "from-purple-500 to-purple-600",
    benefits: [
      "Unlimited AI planning",
      "Confidence scoring",
      "Workflow optimization",
    ],
  },
  actor_pro: {
    name: "Actor Pro",
    price: "$229/mo",
    icon: Shield,
    color: "from-green-500 to-green-600",
    benefits: ["Unlimited automation", "Error monitoring", "ROI tracking"],
  },
  complete: {
    name: "Complete Platform",
    price: "$399/mo",
    icon: Crown,
    color: "from-orange-500 to-orange-600",
    benefits: [
      "All tools included",
      "Cross-platform analytics",
      "Priority support",
      "Save 40%",
    ],
  },
  enterprise: {
    name: "Enterprise Platform",
    price: "$1,499/mo",
    icon: Shield,
    color: "from-red-500 to-red-600",
    benefits: [
      "White-label branding",
      "Dedicated CSM",
      "SLA guarantees",
      "Compliance tools",
    ],
  },
};

export function FeatureLockOverlay({
  featureName,
  requiredPlan,
  onUpgradeClick,
  className,
  style = "blur",
  size = "medium",
  showBenefits = true,
  customMessage,
  children,
}: FeatureLockOverlayProps) {
  const plan = planInfo[requiredPlan];
  const PlanIcon = plan.icon;

  const sizeClasses = {
    small: "p-4",
    medium: "p-6",
    large: "p-8",
  };

  const getOverlayStyle = () => {
    switch (style) {
      case "solid":
        return "bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm";
      case "gradient":
        return `bg-gradient-to-br ${plan.color} text-white`;
      case "blur":
      default:
        return "bg-white/80 dark:bg-gray-900/80 backdrop-blur-md";
    }
  };

  const defaultMessage = `Unlock ${featureName} with ${plan.name}`;

  return (
    <div className={cn("relative", className)}>
      {/* Background content (blurred/dimmed) */}
      {children && (
        <div
          className={cn(
            "relative",
            style === "blur" && "blur-sm opacity-50",
            style === "solid" && "opacity-30",
            style === "gradient" && "opacity-20",
          )}
        >
          {children}
        </div>
      )}

      {/* Overlay */}
      <div
        className={cn(
          "absolute inset-0 flex items-center justify-center",
          getOverlayStyle(),
          sizeClasses[size],
          "rounded-lg border border-gray-200 dark:border-gray-700",
        )}
      >
        <div className="text-center max-w-md">
          {/* Lock Icon */}
          <div
            className={cn(
              "mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4",
              style === "gradient"
                ? "bg-white/20"
                : `bg-gradient-to-br ${plan.color}`,
            )}
          >
            <Lock
              className={cn(
                "h-8 w-8",
                style === "gradient" ? "text-white" : "text-white",
              )}
            />
          </div>

          {/* Feature Name */}
          <h3
            className={cn(
              "text-xl font-bold mb-2",
              style === "gradient"
                ? "text-white"
                : "text-gray-900 dark:text-white",
            )}
          >
            {customMessage || defaultMessage}
          </h3>

          {/* Plan Info */}
          <div
            className={cn(
              "flex items-center justify-center space-x-2 mb-4",
              style === "gradient"
                ? "text-white/90"
                : "text-gray-600 dark:text-gray-300",
            )}
          >
            <PlanIcon className="h-5 w-5" />
            <span className="font-medium">{plan.name}</span>
            <span className="text-sm">•</span>
            <span className="font-bold">{plan.price}</span>
          </div>

          {/* Benefits */}
          {showBenefits && (
            <div className="mb-6">
              <ul className="space-y-2">
                {plan.benefits.slice(0, 3).map((benefit, index) => (
                  <li
                    key={index}
                    className={cn(
                      "flex items-center justify-center space-x-2 text-sm",
                      style === "gradient"
                        ? "text-white/80"
                        : "text-gray-600 dark:text-gray-300",
                    )}
                  >
                    <Sparkles className="h-4 w-4 text-yellow-500" />
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* CTA Button */}
          <button
            onClick={onUpgradeClick}
            className={cn(
              "inline-flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all duration-200",
              "hover:scale-105 hover:shadow-lg",
              style === "gradient"
                ? "bg-white text-gray-900 hover:bg-gray-100"
                : `bg-gradient-to-r ${plan.color} text-white hover:shadow-xl`,
            )}
          >
            <span>Upgrade to {plan.name}</span>
            <ArrowRight className="h-4 w-4" />
          </button>

          {/* Additional Info */}
          <p
            className={cn(
              "text-xs mt-3",
              style === "gradient"
                ? "text-white/70"
                : "text-gray-500 dark:text-gray-400",
            )}
          >
            {requiredPlan === "complete" && "Save 40% with Complete Platform"}
            {requiredPlan === "enterprise" &&
              "Includes dedicated customer success manager"}
            {!["complete", "enterprise"].includes(requiredPlan) &&
              "Upgrade anytime • Cancel anytime"}
          </p>
        </div>
      </div>
    </div>
  );
}

// Preset configurations for common locked features
export const FeatureLockPresets = {
  advancedAnalytics: (onUpgradeClick: () => void) => ({
    featureName: "Advanced Analytics",
    requiredPlan: "complete" as const,
    onUpgradeClick,
    customMessage: "Unlock powerful cross-platform analytics",
    showBenefits: true,
  }),

  unlimitedParsing: (onUpgradeClick: () => void) => ({
    featureName: "Unlimited Website Parsing",
    requiredPlan: "reader_pro" as const,
    onUpgradeClick,
    customMessage: "Parse unlimited websites with Reader Pro",
    showBenefits: true,
  }),

  aiPlanning: (onUpgradeClick: () => void) => ({
    featureName: "Advanced AI Planning",
    requiredPlan: "planner_pro" as const,
    onUpgradeClick,
    customMessage: "Unlock unlimited AI reasoning power",
    showBenefits: true,
  }),

  automation: (onUpgradeClick: () => void) => ({
    featureName: "Unlimited Automation",
    requiredPlan: "actor_pro" as const,
    onUpgradeClick,
    customMessage: "Scale your automation with Actor Pro",
    showBenefits: true,
  }),

  enterpriseFeatures: (onUpgradeClick: () => void) => ({
    featureName: "Enterprise Features",
    requiredPlan: "enterprise" as const,
    onUpgradeClick,
    customMessage: "Unlock enterprise-grade capabilities",
    showBenefits: true,
    style: "gradient" as const,
  }),
};
