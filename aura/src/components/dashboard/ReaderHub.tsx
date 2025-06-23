/**
 * Reader Hub Analytics Component
 * Based on WebAgent Analytics Dashboard Wireframes
 *
 * Features:
 * - Parsing volume charts (bar/line graphs)
 * - Element accuracy pie/bar charts
 * - Performance trends line graphs
 * - Advanced analytics with feature locks
 * - Contextual upgrade CTAs
 */

import React, { useState, useEffect } from "react";
import {
  ArrowLeft,
  Eye,
  Target,
  Zap,
  TrendingUp,
  BarChart3,
  PieChart,
  Clock,
} from "lucide-react";
import { FeatureLockOverlay } from "./FeatureLockOverlay";
import { UsageCounter } from "./UsageCounter";
import { analyticsService } from "../../services/analyticsService";
import { cn } from "../../lib/utils";

interface ReaderHubProps {
  onBackClick: () => void;
  onUpgradeClick: () => void;
  userPlan?: string;
  className?: string;
}

// Mock data - in real app, this would come from API
const mockParsingData = {
  volume: [
    { date: "2025-06-14", parses: 45, success: 42 },
    { date: "2025-06-15", parses: 67, success: 64 },
    { date: "2025-06-16", parses: 89, success: 85 },
    { date: "2025-06-17", parses: 123, success: 118 },
    { date: "2025-06-18", parses: 156, success: 151 },
    { date: "2025-06-19", parses: 134, success: 129 },
    { date: "2025-06-20", parses: 178, success: 172 },
  ],
  accuracy: {
    successful: 92.3,
    partial: 5.2,
    failed: 2.5,
  },
  performance: {
    avgResponseTime: 1.2,
    avgElementsFound: 847,
    avgAccuracy: 94.7,
  },
  topSites: [
    { domain: "amazon.com", parses: 45, accuracy: 96.2 },
    { domain: "github.com", parses: 38, accuracy: 98.1 },
    { domain: "stackoverflow.com", parses: 32, accuracy: 94.8 },
    { domain: "linkedin.com", parses: 28, accuracy: 91.3 },
    { domain: "twitter.com", parses: 24, accuracy: 89.7 },
  ],
};

export function ReaderHub({
  onBackClick,
  onUpgradeClick,
  userPlan = "free",
  className,
}: ReaderHubProps) {
  const [activeTab, setActiveTab] = useState<
    "overview" | "performance" | "accuracy" | "sites"
  >("overview");
  const [readerData, setReaderData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isProUser =
    userPlan === "reader_pro" ||
    userPlan === "complete" ||
    userPlan === "enterprise";

  useEffect(() => {
    fetchReaderData();
  }, []);

  const fetchReaderData = async () => {
    try {
      setIsLoading(true);
      const data = await analyticsService.getReaderAnalytics("7d");
      setReaderData(data);
    } catch (error) {
      console.warn("Failed to fetch reader analytics, using mock data:", error);
      setReaderData(mockParsingData);
    } finally {
      setIsLoading(false);
    }
  };

  const currentData = readerData || mockParsingData;
  const totalParses =
    currentData.volume?.reduce((sum, day) => sum + day.parses, 0) || 0;
  const totalSuccess =
    currentData.volume?.reduce((sum, day) => sum + day.success, 0) || 0;
  const overallAccuracy =
    totalParses > 0 ? (totalSuccess / totalParses) * 100 : 0;

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBackClick}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-300" />
          </button>
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <Eye className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Reader Analytics
              </h1>
              <p className="text-gray-600 dark:text-gray-300">
                Website Intelligence & Parsing Insights
              </p>
            </div>
          </div>
        </div>
        {!isProUser && (
          <button
            onClick={onUpgradeClick}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Upgrade to Reader Pro
          </button>
        )}
      </div>

      {/* Usage Counter */}
      <UsageCounter
        type="reader"
        label="Website Parsing"
        current={totalParses}
        max={isProUser ? 999999 : 200}
        unit="parses"
        trend={{
          direction: "up",
          percentage: 23.5,
          period: "this week",
        }}
        onUpgradeClick={onUpgradeClick}
        showUpgradeButton={!isProUser}
      />

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8">
          {[
            { id: "overview", label: "Overview", icon: BarChart3 },
            { id: "performance", label: "Performance", icon: Zap },
            { id: "accuracy", label: "Accuracy", icon: Target },
            { id: "sites", label: "Top Sites", icon: TrendingUp },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={cn(
                  "flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors",
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300",
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Parsing Volume Chart */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Parsing Volume (7 days)
              </h3>
              <div className="space-y-3">
                {mockParsingData.volume.map((day, index) => (
                  <div key={day.date} className="flex items-center space-x-3">
                    <span className="text-sm text-gray-500 w-16">
                      {new Date(day.date).toLocaleDateString("en-US", {
                        weekday: "short",
                      })}
                    </span>
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full"
                        style={{ width: `${(day.parses / 200) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-900 dark:text-white w-12">
                      {day.parses}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Key Metrics */}
            <div className="space-y-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Key Metrics
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-300">
                      Overall Accuracy
                    </span>
                    <span className="text-2xl font-bold text-green-600">
                      {overallAccuracy.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-300">
                      Avg Response Time
                    </span>
                    <span className="text-2xl font-bold text-blue-600">
                      {mockParsingData.performance.avgResponseTime}s
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-300">
                      Elements Found
                    </span>
                    <span className="text-2xl font-bold text-purple-600">
                      {mockParsingData.performance.avgElementsFound}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "accuracy" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Accuracy Breakdown */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Parsing Accuracy Breakdown
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <span className="text-gray-600 dark:text-gray-300">
                      Successful
                    </span>
                  </div>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {mockParsingData.accuracy.successful}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                    <span className="text-gray-600 dark:text-gray-300">
                      Partial
                    </span>
                  </div>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {mockParsingData.accuracy.partial}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    <span className="text-gray-600 dark:text-gray-300">
                      Failed
                    </span>
                  </div>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {mockParsingData.accuracy.failed}%
                  </span>
                </div>
              </div>
            </div>

            {/* Advanced Analytics (Locked for Free Users) */}
            <div className="relative">
              {!isProUser && (
                <FeatureLockOverlay
                  featureName="Advanced Accuracy Analytics"
                  requiredPlan="reader_pro"
                  onUpgradeClick={onUpgradeClick}
                  style="blur"
                >
                  <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 h-64">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      Element Detection Heatmap
                    </h3>
                    <div className="space-y-2">
                      <div className="h-4 bg-gradient-to-r from-green-500 to-yellow-500 rounded"></div>
                      <div className="h-4 bg-gradient-to-r from-blue-500 to-purple-500 rounded"></div>
                      <div className="h-4 bg-gradient-to-r from-red-500 to-pink-500 rounded"></div>
                    </div>
                  </div>
                </FeatureLockOverlay>
              )}
              {isProUser && (
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    Element Detection Heatmap
                  </h3>
                  <div className="space-y-2">
                    <div className="h-4 bg-gradient-to-r from-green-500 to-yellow-500 rounded"></div>
                    <div className="h-4 bg-gradient-to-r from-blue-500 to-purple-500 rounded"></div>
                    <div className="h-4 bg-gradient-to-r from-red-500 to-pink-500 rounded"></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "sites" && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Top Parsed Websites
            </h3>
            <div className="space-y-3">
              {mockParsingData.topSites.map((site, index) => (
                <div
                  key={site.domain}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-sm font-medium text-gray-500 w-6">
                      #{index + 1}
                    </span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {site.domain}
                    </span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-600 dark:text-gray-300">
                      {site.parses} parses
                    </span>
                    <span className="text-sm font-medium text-green-600">
                      {site.accuracy}% accuracy
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
