/**
 * Enhanced Analytics Dashboard
 * Based on WebAgent Analytics Dashboard Wireframes
 * 
 * Features:
 * - Enhanced header with notifications and plan status
 * - Usage counters with upgrade CTAs
 * - Hub navigation (Reader, Planner, Actor)
 * - Feature lock overlays for premium features
 * - Revenue-optimized upgrade flows
 */

import React, { useState, useEffect } from 'react';
import { Eye, Brain, Bot, BarChart3, Settings, ArrowLeft } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { HeaderBar } from './dashboard/HeaderBar';
import { UsageCounter, UsageCounterPresets } from './dashboard/UsageCounter';
import { ReaderHub } from './dashboard/ReaderHub';
import { FeatureLockOverlay, FeatureLockPresets } from './dashboard/FeatureLockOverlay';
import { analyticsService } from '../services/analyticsService';
import type { DashboardStats } from '../services/analyticsService';
import { cn } from '../lib/utils';

type DashboardView = 'overview' | 'reader' | 'planner' | 'actor' | 'analytics';

export function EnhancedDashboard() {
  const { user } = useAuth();
  const [currentView, setCurrentView] = useState<DashboardView>('overview');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      const dashboardStats = await analyticsService.getDashboardStats();
      setStats(dashboardStats);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpgradeClick = () => {
    console.log('Navigate to upgrade page');
    // In real app, this would navigate to pricing/upgrade page
  };

  const userPlan = user?.subscription_tier || 'free';

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="animate-pulse p-6">
          <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Render specific hub views
  if (currentView === 'reader') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <HeaderBar onUpgradeClick={handleUpgradeClick} />
        <div className="p-6">
          <ReaderHub
            onBackClick={() => setCurrentView('overview')}
            onUpgradeClick={handleUpgradeClick}
            userPlan={userPlan}
          />
        </div>
      </div>
    );
  }

  // Main overview dashboard
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Enhanced Header */}
      <HeaderBar onUpgradeClick={handleUpgradeClick} />

      <div className="p-6 space-y-8">
        {/* Welcome Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Welcome back, {user?.full_name?.split(' ')[0]}! 🚀
              </h1>
              <p className="text-gray-600 dark:text-gray-300 text-lg">
                {userPlan === 'free' 
                  ? 'You\'re exploring WebAgent\'s revolutionary AI capabilities'
                  : 'Unleashing the full power of AI automation'
                }
              </p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-green-600 mb-1">
                $1,250 saved this month
              </div>
              <div className="text-sm text-gray-500">
                18.5 hours automated
              </div>
            </div>
          </div>
        </div>

        {/* Usage Counters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <UsageCounter
            {...UsageCounterPresets.reader(
              stats?.subscription.usage.parses_used || 167,
              userPlan === 'free' ? 200 : 999999,
              handleUpgradeClick
            )}
            trend={{
              direction: 'up',
              percentage: 23.5,
              period: 'this week',
            }}
            showUpgradeButton={userPlan === 'free'}
          />
          
          <UsageCounter
            {...UsageCounterPresets.planner(
              stats?.subscription.usage.plans_used || 18,
              userPlan === 'free' ? 20 : 999999,
              handleUpgradeClick
            )}
            trend={{
              direction: 'up',
              percentage: 15.2,
              period: 'this week',
            }}
            showUpgradeButton={userPlan === 'free'}
          />
          
          <UsageCounter
            {...UsageCounterPresets.actor(
              stats?.subscription.usage.executions_used || 9,
              userPlan === 'free' ? 10 : 999999,
              handleUpgradeClick
            )}
            trend={{
              direction: 'up',
              percentage: 28.7,
              period: 'this week',
            }}
            showUpgradeButton={userPlan === 'free'}
          />
        </div>

        {/* Hub Navigation */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Reader Hub */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-all duration-200 cursor-pointer"
               onClick={() => setCurrentView('reader')}>
            <div className="flex items-center space-x-4 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Eye className="h-6 w-6 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Reader Hub</h3>
                <p className="text-gray-600 dark:text-gray-300 text-sm">Website Intelligence</p>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Success Rate</span>
                <span className="font-medium text-green-600">94.7%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Avg Response</span>
                <span className="font-medium text-blue-600">1.2s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">Elements Found</span>
                <span className="font-medium text-purple-600">847 avg</span>
              </div>
            </div>
          </div>

          {/* Planner Hub */}
          <div className="relative">
            {userPlan === 'free' && (
              <FeatureLockOverlay
                {...FeatureLockPresets.aiPlanning(handleUpgradeClick)}
                size="small"
                style="blur"
              >
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 h-full">
                  <div className="flex items-center space-x-4 mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Brain className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Planner Hub</h3>
                      <p className="text-gray-600 dark:text-gray-300 text-sm">AI Reasoning</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Confidence Score</span>
                      <span className="font-medium text-green-600">96.2%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Goal Completion</span>
                      <span className="font-medium text-blue-600">89.4%</span>
                    </div>
                  </div>
                </div>
              </FeatureLockOverlay>
            )}
            {userPlan !== 'free' && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-all duration-200 cursor-pointer">
                <div className="flex items-center space-x-4 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
                    <Brain className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Planner Hub</h3>
                    <p className="text-gray-600 dark:text-gray-300 text-sm">AI Reasoning</p>
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Confidence Score</span>
                    <span className="font-medium text-green-600">96.2%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Goal Completion</span>
                    <span className="font-medium text-blue-600">89.4%</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Actor Hub */}
          <div className="relative">
            {userPlan === 'free' && (
              <FeatureLockOverlay
                {...FeatureLockPresets.automation(handleUpgradeClick)}
                size="small"
                style="blur"
              >
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 h-full">
                  <div className="flex items-center space-x-4 mb-4">
                    <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                      <Bot className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Actor Hub</h3>
                      <p className="text-gray-600 dark:text-gray-300 text-sm">Automation</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Success Rate</span>
                      <span className="font-medium text-green-600">97.8%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Avg Duration</span>
                      <span className="font-medium text-blue-600">2.4min</span>
                    </div>
                  </div>
                </div>
              </FeatureLockOverlay>
            )}
            {userPlan !== 'free' && (
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-all duration-200 cursor-pointer">
                <div className="flex items-center space-x-4 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-lg flex items-center justify-center">
                    <Bot className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Actor Hub</h3>
                    <p className="text-gray-600 dark:text-gray-300 text-sm">Automation</p>
                  </div>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Success Rate</span>
                    <span className="font-medium text-green-600">97.8%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">Avg Duration</span>
                    <span className="font-medium text-blue-600">2.4min</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Success Metrics */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">Your Success Story</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 mb-2">92%</div>
              <div className="text-gray-600 dark:text-gray-300">Automation Success</div>
              <div className="text-sm text-green-600">+5% this month</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2">18.5h</div>
              <div className="text-gray-600 dark:text-gray-300">Time Saved</div>
              <div className="text-sm text-blue-600">This month</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600 mb-2">$2,750</div>
              <div className="text-gray-600 dark:text-gray-300">Cost Savings</div>
              <div className="text-sm text-purple-600">ROI: 27.5x</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600 mb-2">$1,250</div>
              <div className="text-gray-600 dark:text-gray-300">Automation Value</div>
              <div className="text-sm text-orange-600">This month</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
