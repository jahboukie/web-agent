/**
 * Analytics Dashboard Component
 *
 * Revenue-optimized analytics dashboard that showcases WebAgent's revolutionary
 * AI capabilities while driving strategic business growth through 2025 pricing model.
 */

import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  Eye,
  Brain,
  Zap,
  DollarSign,
  Clock,
  Target,
  Award,
  ArrowUp,
  ArrowDown,
  Minus,
  Crown,
  Sparkles,
} from "lucide-react";
import { analyticsService } from "../../services";
import { useAuth } from "../../contexts/AuthContext";
import { cn } from "../../lib/utils";

interface DashboardStats {
  subscription: any;
  usage_metrics: any;
  success_metrics: any[];
  upgrade_opportunities: any[];
  roi_calculation: any;
  billing_info: any;
}

interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: "blue" | "purple" | "green" | "yellow" | "red";
  trend?: number;
  benchmark?: string;
  tooltip?: string;
  upgradePrompt?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color,
  trend,
  benchmark,
  tooltip,
  upgradePrompt,
}) => {
  const colorClasses = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
  };

  const getTrendIcon = () => {
    if (!trend) return <Minus className="h-4 w-4 text-gray-400" />;
    if (trend > 0) return <ArrowUp className="h-4 w-4 text-green-500" />;
    if (trend < 0) return <ArrowDown className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  return (
    <div
      className={cn(
        "card relative overflow-hidden",
        upgradePrompt && "ring-2 ring-yellow-400 ring-opacity-50",
      )}
    >
      {upgradePrompt && (
        <div className="absolute top-2 right-2">
          <Crown className="h-5 w-5 text-yellow-500" />
        </div>
      )}

      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <div className={cn("p-3 rounded-lg", colorClasses[color])}>
            <div className="text-white">{icon}</div>
          </div>
          {trend !== undefined && (
            <div className="flex items-center space-x-1">
              {getTrendIcon()}
              <span
                className={cn(
                  "text-sm font-medium",
                  trend > 0
                    ? "text-green-600"
                    : trend < 0
                      ? "text-red-600"
                      : "text-gray-500",
                )}
              >
                {trend > 0 ? "+" : ""}
                {trend.toFixed(1)}%
              </span>
            </div>
          )}
        </div>

        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {value}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            {title}
          </p>
          {benchmark && (
            <p className="text-xs text-gray-500 dark:text-gray-500">
              {benchmark}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

interface UsageCardProps {
  title: string;
  icon: React.ReactNode;
  usage: number;
  limit: number | string;
  color: "blue" | "purple" | "green" | "yellow";
  tier: string;
  upgradeAction?: string;
}

const UsageCard: React.FC<UsageCardProps> = ({
  title,
  icon,
  usage,
  limit,
  color,
  tier,
  upgradeAction,
}) => {
  const isUnlimited = limit === "unlimited";
  const usagePercentage = isUnlimited ? 0 : (usage / (limit as number)) * 100;
  const isNearLimit = usagePercentage > 80;

  const colorClasses = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
  };

  const progressColorClasses = {
    blue: "bg-blue-200 dark:bg-blue-900",
    purple: "bg-purple-200 dark:bg-purple-900",
    green: "bg-green-200 dark:bg-green-900",
    yellow: "bg-yellow-200 dark:bg-yellow-900",
  };

  const progressFillClasses = {
    blue: "bg-blue-500",
    purple: "bg-purple-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className={cn("p-2 rounded-lg", colorClasses[color])}>
              <div className="text-white">{icon}</div>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 dark:text-white">
                {title}
              </h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {isUnlimited ? "Unlimited" : `${usage} / ${limit}`}
              </p>
            </div>
          </div>
          {tier === "free" && isNearLimit && (
            <Sparkles className="h-5 w-5 text-yellow-500" />
          )}
        </div>

        {!isUnlimited && (
          <div className="mb-4">
            <div
              className={cn(
                "w-full h-2 rounded-full",
                progressColorClasses[color],
              )}
            >
              <div
                className={cn(
                  "h-2 rounded-full transition-all duration-300",
                  progressFillClasses[color],
                  isNearLimit && "bg-yellow-500",
                )}
                style={{ width: `${Math.min(usagePercentage, 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{usagePercentage.toFixed(1)}% used</span>
              {isNearLimit && (
                <span className="text-yellow-600">Approaching limit</span>
              )}
            </div>
          </div>
        )}

        {tier === "free" && isNearLimit && upgradeAction && (
          <button
            className="w-full btn btn-primary btn-sm"
            onClick={() =>
              analyticsService.trackEvent("upgrade_prompt_clicked", {
                component: title,
                action: upgradeAction,
              })
            }
          >
            Upgrade for Unlimited
          </button>
        )}
      </div>
    </div>
  );
};

export const AnalyticsDashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const dashboardData = await analyticsService.getAnalyticsDashboard();
      setStats(dashboardData);
      setError(null);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
      setError("Failed to load analytics data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button onClick={loadDashboardData} className="btn btn-primary mt-4">
          Retry
        </button>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      {/* Header with Subscription Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back, {user?.full_name?.split(" ")[0]}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {stats.subscription.tier === "free"
              ? "Exploring WebAgent's revolutionary AI capabilities"
              : `${stats.subscription.tier} - Unleashing automation power`}
          </p>
        </div>

        {stats.subscription.tier === "free" && (
          <div className="text-right">
            <div className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
              <Crown className="h-4 w-4 mr-1" />
              Free Tier
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Upgrade to unlock full potential
            </p>
          </div>
        )}
      </div>

      {/* Success Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.success_metrics.map((metric: any, idx: number) => (
          <StatCard
            key={idx}
            title={metric.label}
            value={metric.value}
            icon={getMetricIcon(metric.label)}
            color={getMetricColor(metric.trend_direction)}
            trend={metric.trend}
            benchmark={metric.benchmark}
            tooltip={metric.tooltip}
            upgradePrompt={metric.upgrade_trigger}
          />
        ))}
      </div>

      {/* Usage Overview - Strategic Feature Gating */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <UsageCard
          title="Reader (Website Intelligence)"
          icon={<Eye className="h-6 w-6" />}
          usage={stats.usage_metrics.parses_used || 0}
          limit={stats.subscription.limits.parses || 0}
          color="blue"
          tier={stats.subscription.tier}
          upgradeAction="upgrade_reader_pro"
        />

        <UsageCard
          title="Planner (AI Reasoning)"
          icon={<Brain className="h-6 w-6" />}
          usage={stats.usage_metrics.plans_used || 0}
          limit={stats.subscription.limits.plans || 0}
          color="purple"
          tier={stats.subscription.tier}
          upgradeAction="upgrade_planner_pro"
        />

        <UsageCard
          title="Actor (Automation)"
          icon={<Zap className="h-6 w-6" />}
          usage={stats.usage_metrics.executions_used || 0}
          limit={stats.subscription.limits.executions || 0}
          color="green"
          tier={stats.subscription.tier}
          upgradeAction="upgrade_actor_pro"
        />
      </div>

      {/* ROI Calculator Section */}
      {stats.roi_calculation && (
        <div className="card bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 border-green-200 dark:border-green-800">
          <div className="card-body">
            <div className="flex items-center space-x-3 mb-6">
              <DollarSign className="h-6 w-6 text-green-500" />
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                Your ROI This Month
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {stats.roi_calculation.time_saved_hours.toFixed(1)}h
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Time Saved
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  ${stats.roi_calculation.labor_cost_saved.toFixed(0)}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Labor Cost Saved
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {stats.roi_calculation.roi_percentage.toFixed(0)}%
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">ROI</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  ${stats.roi_calculation.annual_value.toFixed(0)}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Annual Value
                </p>
              </div>
            </div>

            {stats.subscription.tier === "free" &&
              stats.roi_calculation.annual_value > 1000 && (
                <div className="mt-6 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200 text-center">
                    💡 <strong>Upgrade Opportunity:</strong> You're generating $
                    {stats.roi_calculation.annual_value.toFixed(0)} in annual
                    value. Complete Platform pays for itself in just{" "}
                    {Math.ceil(
                      4790 / (stats.roi_calculation.annual_value / 12),
                    )}{" "}
                    months!
                  </p>
                </div>
              )}
          </div>
        </div>
      )}

      {/* Upgrade Opportunities */}
      {stats.upgrade_opportunities &&
        stats.upgrade_opportunities.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recommended Upgrades
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {stats.upgrade_opportunities
                .slice(0, 2)
                .map((opportunity: any, index: number) => (
                  <div
                    key={index}
                    className="card border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20"
                  >
                    <div className="card-body">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h4 className="font-medium text-gray-900 dark:text-white">
                            {opportunity.title}
                          </h4>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {opportunity.description}
                          </p>
                        </div>
                        {opportunity.savings_amount > 0 && (
                          <div className="text-right">
                            <p className="text-sm font-medium text-green-600 dark:text-green-400">
                              Save ${opportunity.savings_amount}/mo
                            </p>
                          </div>
                        )}
                      </div>
                      <button
                        type="button"
                        className="w-full btn btn-primary btn-sm"
                        onClick={() =>
                          analyticsService.trackEvent(
                            "upgrade_prompt_clicked",
                            opportunity,
                          )
                        }
                      >
                        {opportunity.cta_text}
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
    </div>
  );
};

// Helper functions
const getMetricIcon = (label: string) => {
  if (label.includes("Success")) return <Target className="h-6 w-6" />;
  if (label.includes("Time")) return <Clock className="h-6 w-6" />;
  if (label.includes("Cost") || label.includes("Value"))
    return <DollarSign className="h-6 w-6" />;
  return <Award className="h-6 w-6" />;
};

const getMetricColor = (
  direction: string,
): "blue" | "purple" | "green" | "yellow" | "red" => {
  if (direction === "up") return "green";
  if (direction === "down") return "red";
  return "blue";
};
