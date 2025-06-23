/**
 * Analytics Page
 *
 * Comprehensive analytics page showcasing WebAgent's revenue-optimized
 * dashboard with strategic upgrade opportunities and value demonstration.
 */

import React, { useState } from "react";
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Crown,
  Target,
  Settings,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import {
  AnalyticsDashboard,
  UpgradeOpportunities,
  PricingComparison,
  SavingsCalculator,
  MetricsVisualization,
} from "../components/analytics";
import { cn } from "../lib/utils";

type TabType =
  | "overview"
  | "opportunities"
  | "pricing"
  | "calculator"
  | "metrics"
  | "settings";

interface TabButtonProps {
  id: TabType;
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: (tab: TabType) => void;
  badge?: string;
}

const TabButton: React.FC<TabButtonProps> = ({
  id,
  label,
  icon,
  active,
  onClick,
  badge,
}) => (
  <button
    onClick={() => onClick(id)}
    className={cn(
      "flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200",
      active
        ? "bg-blue-600 text-white shadow-md"
        : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800",
    )}
  >
    {icon}
    <span>{label}</span>
    {badge && (
      <span
        className={cn(
          "px-2 py-0.5 rounded-full text-xs font-medium",
          active
            ? "bg-blue-500 text-white"
            : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
        )}
      >
        {badge}
      </span>
    )}
  </button>
);

export const AnalyticsPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  const tabs = [
    {
      id: "overview" as TabType,
      label: "Analytics Overview",
      icon: <BarChart3 className="h-5 w-5" />,
    },
    {
      id: "opportunities" as TabType,
      label: "Upgrade Opportunities",
      icon: <TrendingUp className="h-5 w-5" />,
      badge: "3", // Would be dynamic based on actual opportunities
    },
    {
      id: "pricing" as TabType,
      label: "Pricing Plans",
      icon: <Crown className="h-5 w-5" />,
    },
    {
      id: "calculator" as TabType,
      label: "ROI Calculator",
      icon: <DollarSign className="h-5 w-5" />,
    },
    {
      id: "metrics" as TabType,
      label: "Performance Metrics",
      icon: <BarChart3 className="h-5 w-5" />,
    },
    {
      id: "settings" as TabType,
      label: "Settings",
      icon: <Settings className="h-5 w-5" />,
    },
  ];

  const renderTabContent = () => {
    switch (activeTab) {
      case "overview":
        return <AnalyticsDashboard />;

      case "opportunities":
        return (
          <div className="space-y-6">
            <div className="text-center py-6">
              <Target className="h-12 w-12 text-blue-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Strategic Upgrade Opportunities
              </h2>
              <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                Unlock more value from WebAgent's revolutionary AI capabilities.
                Our intelligent recommendations are based on your usage patterns
                and business goals.
              </p>
            </div>
            <UpgradeOpportunities />
          </div>
        );

      case "pricing":
        return (
          <div className="space-y-6">
            <div className="text-center py-6">
              <Crown className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Choose Your WebAgent Plan
              </h2>
              <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                Unlock the full potential of AI-powered automation with our
                2025-optimized pricing. Save up to 40% with our Complete
                Platform bundle.
              </p>
            </div>
            <PricingComparison
              currentTier="free" // Would be dynamic based on user's actual tier
              onUpgrade={(tierId) => {
                console.log("Upgrading to:", tierId);
                // Handle upgrade flow
              }}
            />
          </div>
        );

      case "calculator":
        return (
          <div className="space-y-6">
            <SavingsCalculator />
          </div>
        );

      case "metrics":
        return (
          <div className="space-y-6">
            <MetricsVisualization />
          </div>
        );

      case "settings":
        return (
          <div className="space-y-6">
            <div className="text-center py-6">
              <Settings className="h-12 w-12 text-gray-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Analytics Settings
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Configure your analytics preferences and data collection
                settings.
              </p>
            </div>

            <div className="card">
              <div className="card-body">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Data Collection Preferences
                </h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Usage Analytics
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Track usage patterns for optimization recommendations
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        defaultChecked
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Performance Monitoring
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Monitor system performance and response times
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        defaultChecked
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        ROI Calculations
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Calculate return on investment and value metrics
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        defaultChecked
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-body">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Notification Preferences
                </h3>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Usage Limit Alerts
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Get notified when approaching usage limits
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        defaultChecked
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                    </label>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        Upgrade Recommendations
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Receive personalized upgrade suggestions
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        defaultChecked
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return <AnalyticsDashboard />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Analytics & Insights
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Track your automation success and discover optimization
            opportunities
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <DollarSign className="h-6 w-6 text-green-500" />
          <div className="text-right">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              This Month's Value
            </p>
            <p className="text-lg font-bold text-green-600 dark:text-green-400">
              $1,250 saved
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-700 pb-4">
        {tabs.map((tab) => (
          <TabButton
            key={tab.id}
            id={tab.id}
            label={tab.label}
            icon={tab.icon}
            active={activeTab === tab.id}
            onClick={setActiveTab}
            badge={tab.badge}
          />
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[600px]">{renderTabContent()}</div>
    </div>
  );
};
