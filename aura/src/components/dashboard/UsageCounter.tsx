/**
 * Usage Counter Component
 * Based on WebAgent Analytics Dashboard Wireframes
 *
 * Features:
 * - Visual progress bars with usage indicators
 * - Contextual upgrade CTAs
 * - Color-coded status (green, yellow, red)
 * - Responsive design
 * - Hover tooltips with details
 */

import React from "react";
import { TrendingUp, AlertTriangle, CheckCircle, ArrowUp } from "lucide-react";
import { cn } from "../../lib/utils";

export interface UsageCounterProps {
  type: "reader" | "planner" | "actor" | "storage" | "api_calls";
  label: string;
  current: number;
  max: number;
  unit?: string;
  trend?: {
    direction: "up" | "down" | "stable";
    percentage: number;
    period: string;
  };
  onUpgradeClick?: () => void;
  className?: string;
  showUpgradeButton?: boolean;
  upgradeMessage?: string;
}

const typeIcons = {
  reader: "👁️",
  planner: "🧠",
  actor: "🤖",
  storage: "💾",
  api_calls: "🔗",
};

const typeColors = {
  reader: "from-blue-500 to-blue-600",
  planner: "from-purple-500 to-purple-600",
  actor: "from-green-500 to-green-600",
  storage: "from-orange-500 to-orange-600",
  api_calls: "from-pink-500 to-pink-600",
};

export function UsageCounter({
  type,
  label,
  current,
  max,
  unit = "",
  trend,
  onUpgradeClick,
  className,
  showUpgradeButton = true,
  upgradeMessage,
}: UsageCounterProps) {
  const percentage = Math.min((current / max) * 100, 100);
  const isNearLimit = percentage >= 80;
  const isAtLimit = percentage >= 95;

  const getStatusColor = () => {
    if (isAtLimit) return "text-red-600 bg-red-50 border-red-200";
    if (isNearLimit) return "text-yellow-600 bg-yellow-50 border-yellow-200";
    return "text-green-600 bg-green-50 border-green-200";
  };

  const getProgressColor = () => {
    if (isAtLimit) return "bg-red-500";
    if (isNearLimit) return "bg-yellow-500";
    return `bg-gradient-to-r ${typeColors[type]}`;
  };

  const getStatusIcon = () => {
    if (isAtLimit) return <AlertTriangle className="h-4 w-4" />;
    if (isNearLimit) return <AlertTriangle className="h-4 w-4" />;
    return <CheckCircle className="h-4 w-4" />;
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const defaultUpgradeMessage = isAtLimit
    ? `Upgrade to unlock unlimited ${label.toLowerCase()}`
    : isNearLimit
      ? `Running low on ${label.toLowerCase()}? Upgrade for more`
      : `Upgrade for unlimited ${label.toLowerCase()}`;

  return (
    <div
      className={cn(
        "bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4",
        "hover:shadow-md transition-all duration-200",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{typeIcons[type]}</span>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-white text-sm">
              {label}
            </h3>
            {trend && (
              <div className="flex items-center space-x-1 text-xs">
                <TrendingUp
                  className={cn(
                    "h-3 w-3",
                    trend.direction === "up"
                      ? "text-green-500"
                      : trend.direction === "down"
                        ? "text-red-500"
                        : "text-gray-500",
                  )}
                />
                <span
                  className={cn(
                    trend.direction === "up"
                      ? "text-green-600"
                      : trend.direction === "down"
                        ? "text-red-600"
                        : "text-gray-600",
                  )}
                >
                  {trend.direction === "up"
                    ? "+"
                    : trend.direction === "down"
                      ? "-"
                      : ""}
                  {trend.percentage}% {trend.period}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Status Badge */}
        <div
          className={cn(
            "flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium border",
            getStatusColor(),
          )}
        >
          {getStatusIcon()}
          <span>
            {isAtLimit ? "Limit Reached" : isNearLimit ? "Near Limit" : "Good"}
          </span>
        </div>
      </div>

      {/* Usage Numbers */}
      <div className="mb-3">
        <div className="flex items-baseline justify-between">
          <div className="flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">
              {formatNumber(current)}
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              / {formatNumber(max)} {unit}
            </span>
          </div>
          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
            {percentage.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className={cn(
              "h-2 rounded-full transition-all duration-500",
              getProgressColor(),
            )}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          />
        </div>
        {/* Usage breakdown */}
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
          <span>Used: {formatNumber(current)}</span>
          <span>Remaining: {formatNumber(Math.max(0, max - current))}</span>
        </div>
      </div>

      {/* Upgrade CTA */}
      {(isNearLimit || isAtLimit) && showUpgradeButton && (
        <div
          className={cn(
            "p-3 rounded-lg border-l-4",
            isAtLimit
              ? "bg-red-50 border-red-400 dark:bg-red-900/20"
              : "bg-yellow-50 border-yellow-400 dark:bg-yellow-900/20",
          )}
        >
          <div className="flex items-center justify-between">
            <div>
              <p
                className={cn(
                  "text-sm font-medium",
                  isAtLimit
                    ? "text-red-800 dark:text-red-200"
                    : "text-yellow-800 dark:text-yellow-200",
                )}
              >
                {isAtLimit ? "Usage Limit Reached" : "Approaching Limit"}
              </p>
              <p
                className={cn(
                  "text-xs mt-1",
                  isAtLimit
                    ? "text-red-600 dark:text-red-300"
                    : "text-yellow-600 dark:text-yellow-300",
                )}
              >
                {upgradeMessage || defaultUpgradeMessage}
              </p>
            </div>
            <button
              onClick={onUpgradeClick}
              className={cn(
                "flex items-center space-x-1 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                isAtLimit
                  ? "bg-red-600 hover:bg-red-700 text-white"
                  : "bg-yellow-600 hover:bg-yellow-700 text-white",
              )}
            >
              <ArrowUp className="h-3 w-3" />
              <span>Upgrade</span>
            </button>
          </div>
        </div>
      )}

      {/* Upgrade suggestion for non-critical usage */}
      {!isNearLimit && showUpgradeButton && (
        <button
          onClick={onUpgradeClick}
          className="w-full text-center py-2 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
        >
          Upgrade for unlimited {label.toLowerCase()} →
        </button>
      )}
    </div>
  );
}

// Preset configurations for common usage types
export const UsageCounterPresets = {
  reader: (current: number, max: number, onUpgradeClick?: () => void) => ({
    type: "reader" as const,
    label: "Website Parsing",
    current,
    max,
    unit: "parses",
    onUpgradeClick,
    upgradeMessage: "Unlock unlimited website intelligence with Reader Pro",
  }),

  planner: (current: number, max: number, onUpgradeClick?: () => void) => ({
    type: "planner" as const,
    label: "AI Planning",
    current,
    max,
    unit: "plans",
    onUpgradeClick,
    upgradeMessage: "Get unlimited AI reasoning with Planner Pro",
  }),

  actor: (current: number, max: number, onUpgradeClick?: () => void) => ({
    type: "actor" as const,
    label: "Automation Executions",
    current,
    max,
    unit: "executions",
    onUpgradeClick,
    upgradeMessage: "Scale your automation with Actor Pro",
  }),
};
