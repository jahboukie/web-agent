/**
 * Revenue-Optimized Analytics Dashboard
 *
 * Comprehensive dashboard showcasing WebAgent's revolutionary AI capabilities
 * while driving strategic revenue growth through intelligent upgrade prompts.
 */

import React, { useState, useEffect } from "react";
import {
  Shield,
  Activity,
  Users,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  Server,
  Lock,
  Eye,
  Zap,
  Brain,
  Play,
  BarChart3,
  DollarSign,
  Sparkles,
  ArrowUpRight,
  Target,
  Award,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { TrustScoreIndicator } from "./security/TrustScoreIndicator";
import { analyticsService } from "../services/analyticsService";
import type { DashboardStats } from "../services/analyticsService";
import { cn, formatNumber, formatRelativeTime } from "../lib/utils";
import { PRICING_TIERS } from "../types/pricing";
import type {
  Activity as ActivityType,
  UpgradeOpportunity,
  SuccessMetric,
} from "../services/analyticsService";

export function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [selectedTimeframe, setSelectedTimeframe] = useState<
    "7d" | "30d" | "90d"
  >("30d");

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [selectedTimeframe]);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const dashboardStats = await analyticsService.getDashboardStats();
      setStats(dashboardStats);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"
              ></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
        <div className="flex">
          <AlertTriangle className="h-5 w-5 text-red-400" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-400">
              Error loading dashboard
            </h3>
            <p className="mt-1 text-sm text-red-700 dark:text-red-300">
              {error}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Subscription Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back, {user?.full_name?.split(" ")[0]}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {stats?.subscription.tier === "free"
              ? "Exploring WebAgent's revolutionary AI capabilities"
              : `${PRICING_TIERS.find((t) => t.id === stats?.subscription.tier)?.name} - Unleashing automation power`}
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Subscription Badge */}
          <div
            className={cn(
              "px-3 py-1 rounded-full text-sm font-medium",
              stats?.subscription.tier === "free"
                ? "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
                : stats?.subscription.tier === "enterprise"
                  ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
                  : "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
            )}
          >
            {PRICING_TIERS.find((t) => t.id === stats?.subscription.tier)
              ?.name || "Free"}
          </div>
          <TrustScoreIndicator showDetails size="lg" />
        </div>
      </div>

      {/* Upgrade Opportunities Banner */}
      {stats?.upgrade_opportunities?.length &&
        stats.upgrade_opportunities.length > 0 && (
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-6 border border-blue-200 dark:border-blue-800">
            <div className="flex items-start space-x-4">
              <Sparkles className="h-8 w-8 text-blue-600 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                  {stats?.upgrade_opportunities?.[0]?.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-3">
                  {stats?.upgrade_opportunities?.[0]?.description}
                </p>
                <div className="flex flex-wrap gap-2 mb-4">
                  {stats?.upgrade_opportunities?.[0]?.value_props?.map(
                    (prop, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 text-sm rounded-md"
                      >
                        <CheckCircle className="h-3 w-3 mr-1" />
                        {prop}
                      </span>
                    ),
                  )}
                </div>
                <button
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                  onClick={() =>
                    console.log(
                      "Upgrade action:",
                      stats?.upgrade_opportunities?.[0]?.cta_action,
                    )
                  }
                >
                  {stats?.upgrade_opportunities?.[0]?.cta_text}
                  <ArrowUpRight className="h-4 w-4 ml-1 inline" />
                </button>
              </div>
            </div>
          </div>
        )}

      {/* Success Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats?.success_metrics.map((metric, idx) => (
          <StatCard
            key={idx}
            title={metric.label}
            value={metric.value}
            icon={getMetricIcon(metric.label)}
            color={getMetricColor(metric.trend_direction)}
            trend={metric.trend}
            benchmark={metric.benchmark}
            tooltip={metric.tooltip}
          />
        ))}
      </div>

      {/* Usage Overview - Strategic Feature Gating */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <UsageCard
          title="Reader (Website Intelligence)"
          icon={<Eye className="h-6 w-6" />}
          usage={stats?.subscription.usage.parses_used || 0}
          limit={stats?.subscription.limits.parses || 0}
          color="blue"
          tier={stats?.subscription.tier}
          upgradeAction="upgrade_reader_pro"
        />

        <UsageCard
          title="Planner (AI Reasoning)"
          icon={<Brain className="h-6 w-6" />}
          usage={stats?.subscription.usage.plans_used || 0}
          limit={stats?.subscription.limits.plans || 0}
          color="purple"
          tier={stats?.subscription.tier}
          upgradeAction="upgrade_planner_pro"
        />

        <UsageCard
          title="Actor (Automation)"
          icon={<Play className="h-6 w-6" />}
          usage={stats?.subscription.usage.executions_used || 0}
          limit={stats?.subscription.limits.executions || 0}
          color="green"
          tier={stats?.subscription.tier}
          upgradeAction="upgrade_actor_pro"
        />
      </div>

      {/* Main Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activities with Revenue Context */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Activities
            </h3>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {stats?.usage_metrics.unified.total_workflows} workflows completed
            </div>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {stats?.recent_activities.length > 0 ? (
                stats.recent_activities.map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent activities</p>
                  <button
                    className="mt-2 text-blue-600 hover:text-blue-700 text-sm"
                    onClick={() => console.log("Create first workflow")}
                  >
                    Create your first workflow
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ROI & Success Showcase */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Your Success Story
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Award className="h-5 w-5 text-green-600" />
                  <span className="font-medium text-green-800 dark:text-green-200">
                    Time Saved This Month
                  </span>
                </div>
                <div className="text-2xl font-bold text-green-800 dark:text-green-200">
                  {stats?.usage_metrics.unified.roi_metrics.time_saved_hours.toFixed(
                    1,
                  )}{" "}
                  hours
                </div>
                <div className="text-sm text-green-600 dark:text-green-300">
                  Worth $
                  {Math.round(
                    (stats?.usage_metrics.unified.roi_metrics
                      .time_saved_hours || 0) * 75,
                  )}{" "}
                  in productivity
                </div>
              </div>

              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <DollarSign className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-blue-800 dark:text-blue-200">
                    Cost Savings Generated
                  </span>
                </div>
                <div className="text-2xl font-bold text-blue-800 dark:text-blue-200">
                  $
                  {stats?.usage_metrics.unified.roi_metrics.cost_saved_usd.toLocaleString()}
                </div>
                <div className="text-sm text-blue-600 dark:text-blue-300">
                  ROI:{" "}
                  {Math.round(
                    (stats?.usage_metrics.unified.roi_metrics.cost_saved_usd ||
                      0) / 100,
                  )}
                  x
                </div>
              </div>

              {stats?.subscription.tier === "free" && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4 border border-yellow-200 dark:border-yellow-800">
                  <div className="text-sm text-yellow-800 dark:text-yellow-200">
                    <strong>🚀 Imagine this with unlimited usage!</strong>
                    <br />
                    Complete Platform users average 3x better results.
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Revenue-Optimized Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Quick Actions
          </h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <QuickActionButton
              title="Parse Website"
              description="Extract data intelligently"
              icon={<Eye className="h-6 w-6" />}
              onClick={() => console.log("Navigate to Reader")}
              disabled={false}
            />
            <QuickActionButton
              title="Create Plan"
              description="AI-powered automation planning"
              icon={<Brain className="h-6 w-6" />}
              onClick={() => console.log("Navigate to Planner")}
              disabled={false}
            />
            <QuickActionButton
              title="Execute Workflow"
              description="Run automation sequences"
              icon={<Play className="h-6 w-6" />}
              onClick={() => console.log("Navigate to Actor")}
              disabled={false}
            />
            <QuickActionButton
              title={
                stats?.subscription.tier === "free"
                  ? "Unlock Analytics"
                  : "Advanced Analytics"
              }
              description={
                stats?.subscription.tier === "free"
                  ? "Enterprise insights"
                  : "Deep performance data"
              }
              icon={<BarChart3 className="h-6 w-6" />}
              onClick={() => console.log("Navigate to Analytics")}
              disabled={stats?.subscription.tier === "free"}
              premium={stats?.subscription.tier === "free"}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// Stat Card Component
interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: "blue" | "green" | "orange" | "purple";
  trend?: string;
  benchmark?: string;
  tooltip?: string;
}

function StatCard({
  title,
  value,
  icon,
  color,
  trend,
  benchmark,
  tooltip,
}: StatCardProps) {
  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    orange: "bg-orange-500",
    purple: "bg-purple-500",
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {value}
            </p>
            {trend && (
              <div className="flex items-center mt-1">
                <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                <span className="text-sm text-green-600 dark:text-green-400">
                  {trend}
                </span>
              </div>
            )}
          </div>
          <div className={cn("p-3 rounded-lg", colorClasses[color])}>
            <div className="text-white">{icon}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Usage Card Component with Strategic Upgrade Triggers
interface UsageCardProps {
  title: string;
  icon: React.ReactNode;
  usage: number;
  limit: number | "unlimited";
  color: "blue" | "green" | "orange" | "purple";
  tier?: string;
  upgradeAction?: string;
}

function UsageCard({
  title,
  icon,
  usage,
  limit,
  color,
  tier,
  upgradeAction,
}: UsageCardProps) {
  const isUnlimited = limit === "unlimited";
  const percentage = isUnlimited ? 0 : (usage / (limit as number)) * 100;
  const isNearLimit = percentage > 80;

  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    orange: "bg-orange-500",
    purple: "bg-purple-500",
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
            <Zap className="h-5 w-5 text-yellow-500" />
          )}
        </div>

        {!isUnlimited && (
          <div className="mb-3">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600 dark:text-gray-400">Usage</span>
              <span
                className={cn(
                  "font-medium",
                  isNearLimit
                    ? "text-yellow-600 dark:text-yellow-400"
                    : "text-gray-900 dark:text-white",
                )}
              >
                {percentage.toFixed(0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={cn(
                  "h-2 rounded-full transition-all duration-300",
                  isNearLimit ? "bg-yellow-500" : colorClasses[color],
                )}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
          </div>
        )}

        {tier === "free" && isNearLimit && (
          <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 border border-yellow-200 dark:border-yellow-800">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  Approaching limit
                </p>
                <p className="text-xs text-yellow-700 dark:text-yellow-300 mb-2">
                  Upgrade to avoid interruptions
                </p>
                <button
                  className="text-xs bg-yellow-600 hover:bg-yellow-700 text-white px-2 py-1 rounded transition-colors"
                  onClick={() => console.log("Upgrade:", upgradeAction)}
                >
                  Upgrade Now
                </button>
              </div>
            </div>
          </div>
        )}

        {isUnlimited && (
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
            <CheckCircle className="h-5 w-5 text-green-600 mx-auto mb-1" />
            <p className="text-sm font-medium text-green-800 dark:text-green-200">
              Unlimited Usage
            </p>
            <p className="text-xs text-green-600 dark:text-green-400">
              No limits, maximum productivity
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Enhanced Activity Item Component
interface ActivityItemProps {
  activity: ActivityType;
}

function ActivityItem({ activity }: ActivityItemProps) {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case "parse":
        return <Eye className="h-4 w-4" />;
      case "plan":
        return <Brain className="h-4 w-4" />;
      case "execute":
        return <Play className="h-4 w-4" />;
      case "system":
        return <Server className="h-4 w-4" />;
      default:
        return <Activity className="h-4 w-4" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30";
      case "warning":
        return "text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30";
      case "error":
        return "text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30";
      case "info":
        return "text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30";
      default:
        return "text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-900/30";
    }
  };

  return (
    <div className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div
        className={cn("p-1.5 rounded-full", getStatusColor(activity.status))}
      >
        {getActivityIcon(activity.type)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {activity.title}
          </p>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatRelativeTime(activity.timestamp)}
          </span>
        </div>
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          {activity.description}
        </p>
        {activity.metadata && (
          <div className="flex items-center space-x-2 mt-2">
            {Object.entries(activity.metadata).map(([key, value], idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-xs text-gray-600 dark:text-gray-400 rounded"
              >
                {key}: {value}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Security Metric Component
interface SecurityMetricProps {
  label: string;
  value: string;
  status: "success" | "warning" | "error";
  icon: React.ReactNode;
}

function SecurityMetric({ label, value, status, icon }: SecurityMetricProps) {
  const statusColors = {
    success: "text-green-600 dark:text-green-400",
    warning: "text-yellow-600 dark:text-yellow-400",
    error: "text-red-600 dark:text-red-400",
  };

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className={cn(statusColors[status])}>{icon}</div>
        <span className="text-sm text-gray-700 dark:text-gray-300">
          {label}
        </span>
      </div>
      <span className={cn("text-sm font-medium", statusColors[status])}>
        {value}
      </span>
    </div>
  );
}

// Enhanced Quick Action Button Component
interface QuickActionButtonProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  premium?: boolean;
}

function QuickActionButton({
  title,
  description,
  icon,
  onClick,
  disabled = false,
  premium = false,
}: QuickActionButtonProps) {
  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={cn(
        "p-4 text-left border rounded-lg transition-all duration-200 relative",
        disabled
          ? "border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed"
          : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-700",
      )}
    >
      {premium && (
        <div className="absolute -top-1 -right-1 bg-gradient-to-r from-yellow-400 to-orange-500 text-white text-xs px-2 py-0.5 rounded-full font-medium">
          Pro
        </div>
      )}
      <div className="flex items-center space-x-3">
        <div
          className={cn(
            "transition-colors",
            disabled
              ? "text-gray-400 dark:text-gray-600"
              : "text-primary-600 dark:text-primary-500",
          )}
        >
          {icon}
        </div>
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4
              className={cn(
                "text-sm font-medium",
                disabled
                  ? "text-gray-500 dark:text-gray-600"
                  : "text-gray-900 dark:text-white",
              )}
            >
              {title}
            </h4>
            {premium && <Lock className="h-3 w-3 text-yellow-600" />}
          </div>
          <p
            className={cn(
              "text-xs mt-1",
              disabled
                ? "text-gray-400 dark:text-gray-600"
                : "text-gray-500 dark:text-gray-400",
            )}
          >
            {description}
          </p>
          {premium && (
            <p className="text-xs text-yellow-600 dark:text-yellow-500 mt-1 font-medium">
              Upgrade to unlock
            </p>
          )}
        </div>
      </div>
    </button>
  );
}

// Helper Functions
function getMetricIcon(label: string) {
  switch (label.toLowerCase()) {
    case "automation success rate":
    case "success rate":
      return <Target className="h-6 w-6" />;
    case "time saved this month":
    case "time saved":
      return <Clock className="h-6 w-6" />;
    case "cost savings generated":
    case "cost savings":
      return <DollarSign className="h-6 w-6" />;
    case "user satisfaction":
    case "satisfaction":
      return <Award className="h-6 w-6" />;
    default:
      return <TrendingUp className="h-6 w-6" />;
  }
}

function getMetricColor(
  direction: "up" | "down" | "stable",
): "blue" | "green" | "orange" | "purple" {
  switch (direction) {
    case "up":
      return "green";
    case "down":
      return "orange";
    case "stable":
      return "blue";
    default:
      return "purple";
  }
}
