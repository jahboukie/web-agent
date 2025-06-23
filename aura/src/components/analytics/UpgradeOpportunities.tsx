/**
 * Upgrade Opportunities Component
 *
 * Strategic upgrade opportunities for conversion optimization.
 * Designed to maximize revenue through intelligent value demonstration.
 */

import React, { useState, useEffect } from "react";
import {
  Crown,
  TrendingUp,
  Clock,
  Zap,
  DollarSign,
  ArrowRight,
  Sparkles,
  Target,
  Award,
  AlertTriangle,
} from "lucide-react";
import { analyticsService } from "../../services";
import { cn } from "../../lib/utils";

interface UpgradeOpportunity {
  type: string;
  priority: number;
  title: string;
  description: string;
  value_proposition: string;
  current_tier: string;
  recommended_tier: string;
  savings_amount: number;
  savings_percentage: number;
  cta_text: string;
  cta_url: string;
  usage_percentage: number;
  days_until_limit?: number;
  limited_time_offer: boolean;
}

interface UpgradeCardProps {
  opportunity: UpgradeOpportunity;
  onUpgrade: (opportunity: UpgradeOpportunity) => void;
}

const UpgradeCard: React.FC<UpgradeCardProps> = ({
  opportunity,
  onUpgrade,
}) => {
  const getTypeIcon = () => {
    switch (opportunity.type) {
      case "usage_limit":
        return <AlertTriangle className="h-6 w-6 text-yellow-500" />;
      case "feature_unlock":
        return <Sparkles className="h-6 w-6 text-purple-500" />;
      case "performance_boost":
        return <Zap className="h-6 w-6 text-blue-500" />;
      case "savings":
        return <DollarSign className="h-6 w-6 text-green-500" />;
      default:
        return <Crown className="h-6 w-6 text-yellow-500" />;
    }
  };

  const getPriorityColor = () => {
    switch (opportunity.priority) {
      case 1:
        return "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20";
      case 2:
        return "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20";
      case 3:
        return "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20";
      default:
        return "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50";
    }
  };

  const getUrgencyBadge = () => {
    if (opportunity.days_until_limit && opportunity.days_until_limit <= 7) {
      return (
        <div className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
          <Clock className="h-3 w-3 mr-1" />
          {opportunity.days_until_limit} days left
        </div>
      );
    }

    if (opportunity.limited_time_offer) {
      return (
        <div className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
          <Sparkles className="h-3 w-3 mr-1" />
          Limited Time
        </div>
      );
    }

    return null;
  };

  return (
    <div
      className={cn(
        "card border-2 transition-all duration-200 hover:shadow-lg",
        getPriorityColor(),
      )}
    >
      <div className="card-body">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            {getTypeIcon()}
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                {opportunity.title}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {opportunity.description}
              </p>
            </div>
          </div>
          {getUrgencyBadge()}
        </div>

        {/* Value Proposition */}
        <div className="mb-4 p-3 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            💡 Value Proposition
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {opportunity.value_proposition}
          </p>
        </div>

        {/* Savings Display */}
        {opportunity.savings_amount > 0 && (
          <div className="mb-4 flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                Monthly Savings
              </p>
              <p className="text-lg font-bold text-green-900 dark:text-green-100">
                ${opportunity.savings_amount}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-green-700 dark:text-green-300">
                {opportunity.savings_percentage.toFixed(0)}% off
              </p>
              <p className="text-xs text-green-600 dark:text-green-400">
                vs individual tools
              </p>
            </div>
          </div>
        )}

        {/* Usage Progress (if applicable) */}
        {opportunity.usage_percentage > 0 && (
          <div className="mb-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600 dark:text-gray-400">
                Current Usage
              </span>
              <span className="font-medium text-gray-900 dark:text-white">
                {opportunity.usage_percentage.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className={cn(
                  "h-2 rounded-full transition-all duration-300",
                  opportunity.usage_percentage > 80
                    ? "bg-red-500"
                    : opportunity.usage_percentage > 60
                      ? "bg-yellow-500"
                      : "bg-blue-500",
                )}
                style={{
                  width: `${Math.min(opportunity.usage_percentage, 100)}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Upgrade Button */}
        <button
          onClick={() => onUpgrade(opportunity)}
          className={cn(
            "w-full btn flex items-center justify-center space-x-2 transition-all duration-200",
            opportunity.priority === 1 ? "btn-primary" : "btn-secondary",
          )}
        >
          <span>{opportunity.cta_text}</span>
          <ArrowRight className="h-4 w-4" />
        </button>

        {/* Tier Comparison */}
        <div className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Current: {opportunity.current_tier}</span>
          <ArrowRight className="h-3 w-3" />
          <span>Recommended: {opportunity.recommended_tier}</span>
        </div>
      </div>
    </div>
  );
};

export const UpgradeOpportunities: React.FC = () => {
  const [opportunities, setOpportunities] = useState<UpgradeOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUpgradeOpportunities();
  }, []);

  const loadUpgradeOpportunities = async () => {
    try {
      setLoading(true);
      const data = await analyticsService.getUpgradeOpportunities();
      setOpportunities(data);
      setError(null);
    } catch (err) {
      console.error("Failed to load upgrade opportunities:", err);
      setError("Failed to load upgrade opportunities");
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (opportunity: UpgradeOpportunity) => {
    // Track conversion event
    await analyticsService.trackEvent("upgrade_opportunity_clicked", {
      type: opportunity.type,
      priority: opportunity.priority,
      current_tier: opportunity.current_tier,
      recommended_tier: opportunity.recommended_tier,
      savings_amount: opportunity.savings_amount,
    });

    // Redirect to upgrade flow
    window.location.href = opportunity.cta_url;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-6">
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <button onClick={loadUpgradeOpportunities} className="btn btn-primary">
          Retry
        </button>
      </div>
    );
  }

  if (opportunities.length === 0) {
    return (
      <div className="text-center py-8">
        <Award className="h-12 w-12 text-green-500 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          You're All Set!
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          No upgrade opportunities at this time. You're making great use of your
          current plan.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Upgrade Opportunities
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Unlock more value with strategic upgrades
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {opportunities.length} opportunity
            {opportunities.length !== 1 ? "s" : ""} available
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {opportunities.map((opportunity, index) => (
          <UpgradeCard
            key={index}
            opportunity={opportunity}
            onUpgrade={handleUpgrade}
          />
        ))}
      </div>

      {/* Success Stories Section */}
      <div className="card bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-blue-200 dark:border-blue-800">
        <div className="card-body">
          <div className="flex items-center space-x-3 mb-4">
            <Target className="h-6 w-6 text-blue-500" />
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Success Stories
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                97%
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Enterprise customers achieve automation success
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                3x
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                ROI with Complete Platform vs individual tools
              </p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                $2,400
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Average monthly savings for Enterprise users
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
