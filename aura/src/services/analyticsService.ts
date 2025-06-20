/**
 * Analytics Service
 * 
 * Revenue-optimized analytics service that drives strategic upgrades
 * through intelligent data presentation and value demonstration.
 */

import { apiService } from './apiService';
import { demoService } from './demoService';
import type { UsageMetrics, UserSubscription } from '../types/pricing';

export interface DashboardStats {
  subscription: UserSubscription;
  usage_metrics: UsageMetrics;
  recent_activities: Activity[];
  upgrade_opportunities: UpgradeOpportunity[];
  success_metrics: SuccessMetric[];
}

export interface Activity {
  id: string;
  type: 'parse' | 'plan' | 'execute' | 'system';
  title: string;
  description: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error' | 'info';
  metadata?: Record<string, any>;
}

export interface UpgradeOpportunity {
  id: string;
  type: 'usage_limit' | 'feature_unlock' | 'value_demonstration';
  title: string;
  description: string;
  urgency: 'low' | 'medium' | 'high';
  cta_text: string;
  cta_action: string;
  value_props: string[];
  estimated_roi?: string;
}

export interface SuccessMetric {
  label: string;
  value: string;
  trend: string;
  trend_direction: 'up' | 'down' | 'stable';
  benchmark?: string;
  tooltip?: string;
}

class AnalyticsService {
  
  /**
   * Get comprehensive dashboard statistics with revenue optimization
   */
  async getDashboardStats(): Promise<DashboardStats> {
    try {
      if (demoService.isDemoMode()) {
        console.log('🎭 Demo Mode: Using analytics demo data');
        return this.getDemoAnalytics();
      }

      // Production analytics - parallel API calls for performance
      const [subscription, usageMetrics, activities] = await Promise.all([
        this.getUserSubscription(),
        this.getUsageMetrics(),
        this.getRecentActivities()
      ]);

      const upgradeOpportunities = this.generateUpgradeOpportunities(subscription, usageMetrics);
      const successMetrics = this.calculateSuccessMetrics(usageMetrics);

      return {
        subscription,
        usage_metrics: usageMetrics,
        recent_activities: activities,
        upgrade_opportunities: upgradeOpportunities,
        success_metrics: successMetrics
      };

    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
      throw error;
    }
  }

  /**
   * Get user's current subscription details
   */
  async getUserSubscription(): Promise<UserSubscription> {
    return apiService.get<UserSubscription>('/analytics/subscription');
  }

  /**
   * Get detailed usage metrics across all platform components
   */
  async getUsageMetrics(hours: number = 24): Promise<UsageMetrics> {
    return apiService.get<UsageMetrics>(`/analytics/usage?hours=${hours}`);
  }

  /**
   * Get comprehensive analytics dashboard data
   */
  async getAnalyticsDashboard(): Promise<DashboardStats> {
    return apiService.get<DashboardStats>('/analytics/dashboard');
  }

  /**
   * Get strategic upgrade opportunities
   */
  async getUpgradeOpportunities(): Promise<UpgradeOpportunity[]> {
    return apiService.get<UpgradeOpportunity[]>('/analytics/upgrade-opportunities');
  }

  /**
   * Get component-specific metrics
   */
  async getComponentMetrics(component: string, hours: number = 24): Promise<any> {
    return apiService.get(`/analytics/component/${component}?hours=${hours}`);
  }

  /**
   * Get ROI calculation
   */
  async getROICalculation(hourlyRate: number = 50): Promise<any> {
    return apiService.get(`/analytics/roi-calculation?hourly_rate=${hourlyRate}`);
  }

  /**
   * Get success metrics for value demonstration
   */
  async getSuccessMetrics(): Promise<SuccessMetric[]> {
    return apiService.get<SuccessMetric[]>('/analytics/success-metrics');
  }

  /**
   * Get billing information
   */
  async getBillingInfo(): Promise<any> {
    return apiService.get('/analytics/billing');
  }

  /**
   * Track analytics events for conversion optimization
   */
  async trackEvent(eventType: string, eventData: any): Promise<void> {
    return apiService.post('/analytics/track-event', {
      event_type: eventType,
      event_data: eventData
    });
  }

  /**
   * Get recent activities with intelligent categorization
   */
  async getRecentActivities(): Promise<Activity[]> {
    return apiService.get<Activity[]>('/analytics/activities?limit=10');
  }

  /**
   * Get Reader (parsing) specific analytics
   */
  async getReaderAnalytics(timeframe: '7d' | '30d' | '90d' = '30d') {
    return apiService.get(`/analytics/reader?timeframe=${timeframe}`);
  }

  /**
   * Get Planner (AI planning) specific analytics  
   */
  async getPlannerAnalytics(timeframe: '7d' | '30d' | '90d' = '30d') {
    return apiService.get(`/analytics/planner?timeframe=${timeframe}`);
  }

  /**
   * Get Actor (execution) specific analytics
   */
  async getActorAnalytics(timeframe: '7d' | '30d' | '90d' = '30d') {
    return apiService.get(`/analytics/actor?timeframe=${timeframe}`);
  }

  /**
   * Get unified cross-platform analytics (Complete/Enterprise only)
   */
  async getUnifiedAnalytics(timeframe: '7d' | '30d' | '90d' = '30d') {
    return apiService.get(`/analytics/unified?timeframe=${timeframe}`);
  }

  /**
   * Get ROI and business impact metrics
   */
  async getROIMetrics() {
    return apiService.get('/analytics/roi');
  }

  /**
   * Generate intelligent upgrade opportunities based on usage patterns
   */
  private generateUpgradeOpportunities(
    subscription: UserSubscription, 
    metrics: UsageMetrics
  ): UpgradeOpportunity[] {
    const opportunities: UpgradeOpportunity[] = [];

    // Usage-based upgrade prompts
    if (subscription.tier === 'free') {
      const parseUsage = subscription.usage.parses_used / (subscription.limits.parses as number);
      const planUsage = subscription.usage.plans_used / (subscription.limits.plans as number);
      const execUsage = subscription.usage.executions_used / (subscription.limits.executions as number);

      if (parseUsage > 0.8 || planUsage > 0.8 || execUsage > 0.8) {
        opportunities.push({
          id: 'free_tier_limits',
          type: 'usage_limit',
          title: 'Approaching Free Tier Limits',
          description: `You've used ${Math.max(parseUsage, planUsage, execUsage) * 100}% of your allocation. Upgrade to avoid interruptions.`,
          urgency: 'high',
          cta_text: 'Upgrade to Complete Platform',
          cta_action: 'upgrade_complete',
          value_props: [
            'Unlimited everything for $399/mo',
            '40% savings vs individual tools',
            'Advanced analytics included'
          ],
          estimated_roi: 'Users save 15+ hours/week on average'
        });
      }

      // Value demonstration for free users
      if (metrics.unified.total_workflows > 5) {
        opportunities.push({
          id: 'success_demonstration',
          type: 'value_demonstration',
          title: 'Unlock Your Full Potential',
          description: 'You\'ve completed 5+ workflows! See how Complete Platform users achieve 97% automation success.',
          urgency: 'medium',
          cta_text: 'See Success Stories',
          cta_action: 'view_success_stories',
          value_props: [
            '3x better automation ROI',
            'Advanced workflow optimization',
            'Unified cross-tool insights'
          ]
        });
      }
    }

    // Individual tool users -> Bundle upgrade
    if (['reader_pro', 'planner_pro', 'actor_pro'].includes(subscription.tier)) {
      opportunities.push({
        id: 'bundle_savings',
        type: 'feature_unlock',
        title: 'Save 40% with Complete Platform',
        description: 'Unlock all tools + unified analytics for less than what you\'re paying now.',
        urgency: 'medium',
        cta_text: 'Calculate Savings',
        cta_action: 'show_bundle_calculator',
        value_props: [
          'Access all WebAgent tools',
          'Unified workflow analytics',
          'Save $138/month vs current plan'
        ],
        estimated_roi: '$1,656 annual savings'
      });
    }

    return opportunities;
  }

  /**
   * Calculate success metrics that demonstrate platform value
   */
  private calculateSuccessMetrics(metrics: UsageMetrics): SuccessMetric[] {
    return [
      {
        label: 'Automation Success Rate',
        value: `${Math.round(metrics.unified.end_to_end_success_rate * 100)}%`,
        trend: '+5%',
        trend_direction: 'up',
        benchmark: 'Industry avg: 73%',
        tooltip: 'Percentage of workflows completed successfully end-to-end'
      },
      {
        label: 'Time Saved This Month',
        value: `${Math.round(metrics.unified.roi_metrics.time_saved_hours)} hours`,
        trend: '+12 hours',
        trend_direction: 'up',
        tooltip: 'Total hours saved through automation vs manual processes'
      },
      {
        label: 'Cost Savings Generated',
        value: `$${Math.round(metrics.unified.roi_metrics.cost_saved_usd).toLocaleString()}`,
        trend: '+$1,250',
        trend_direction: 'up',
        tooltip: 'Estimated cost savings from automated workflows'
      },
      {
        label: 'User Satisfaction',
        value: `${Math.round(metrics.unified.user_satisfaction_score * 100)}%`,
        trend: 'stable',
        trend_direction: 'stable',
        benchmark: 'Enterprise avg: 94%'
      }
    ];
  }

  /**
   * Demo mode analytics data
   */
  private async getDemoAnalytics(): Promise<DashboardStats> {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    return {
      subscription: {
        tier: 'free',
        status: 'active',
        current_period_start: thirtyDaysAgo.toISOString(),
        current_period_end: new Date(now.getTime() + 5 * 24 * 60 * 60 * 1000).toISOString(),
        usage: {
          parses_used: 87,
          plans_used: 12,
          executions_used: 6,
          storage_used_gb: 0.3,
          api_calls_used: 234
        },
        limits: {
          parses: 200,
          plans: 20,
          executions: 10,
          storage_gb: 1,
          api_calls: 1000
        }
      },
      usage_metrics: {
        reader: {
          total_parses: 87,
          successful_parses: 82,
          failed_parses: 5,
          success_rate: 0.94,
          avg_parse_time_ms: 1250,
          domains_parsed: ['github.com', 'stackoverflow.com', 'docs.python.org'],
          performance_trend: [
            { date: '2025-06-15', value: 1.2 },
            { date: '2025-06-16', value: 1.3 },
            { date: '2025-06-17', value: 1.1 },
            { date: '2025-06-18', value: 1.25 },
            { date: '2025-06-19', value: 1.2 },
            { date: '2025-06-20', value: 1.25 }
          ]
        },
        planner: {
          total_plans: 12,
          successful_plans: 11,
          failed_plans: 1,
          avg_confidence_score: 0.87,
          avg_plan_complexity: 6.4,
          plan_types: [
            { type: 'web_scraping', count: 5 },
            { type: 'form_filling', count: 4 },
            { type: 'data_extraction', count: 3 }
          ],
          confidence_trend: [
            { date: '2025-06-15', value: 0.85 },
            { date: '2025-06-16', value: 0.88 },
            { date: '2025-06-17', value: 0.86 },
            { date: '2025-06-18', value: 0.89 },
            { date: '2025-06-19', value: 0.87 },
            { date: '2025-06-20', value: 0.87 }
          ]
        },
        actor: {
          total_executions: 6,
          successful_executions: 6,
          failed_executions: 0,
          success_rate: 1.0,
          avg_execution_time_ms: 45000,
          actions_per_execution: 12.5,
          error_categories: [],
          performance_trend: [
            { date: '2025-06-18', value: 42 },
            { date: '2025-06-19', value: 48 },
            { date: '2025-06-20', value: 45 }
          ]
        },
        unified: {
          total_workflows: 6,
          end_to_end_success_rate: 0.92,
          avg_workflow_time_ms: 180000,
          roi_metrics: {
            time_saved_hours: 18.5,
            cost_saved_usd: 2750,
            automation_value: 4200
          },
          user_satisfaction_score: 0.95
        }
      },
      recent_activities: [
        {
          id: '1',
          type: 'execute',
          title: 'Workflow Completed Successfully',
          description: 'Data extraction from GitHub repositories completed',
          timestamp: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString(),
          status: 'success',
          metadata: { execution_time: '2m 15s', actions: 8 }
        },
        {
          id: '2', 
          type: 'plan',
          title: 'New Automation Plan Created',
          description: 'AI planning completed for form filling workflow',
          timestamp: new Date(now.getTime() - 4 * 60 * 60 * 1000).toISOString(),
          status: 'success',
          metadata: { confidence: 0.89, complexity: 7 }
        },
        {
          id: '3',
          type: 'parse',
          title: 'Website Parsing Completed',
          description: 'Extracted 45 data points from stackoverflow.com',
          timestamp: new Date(now.getTime() - 6 * 60 * 60 * 1000).toISOString(),
          status: 'success',
          metadata: { elements_found: 45, parse_time: '1.2s' }
        }
      ],
      upgrade_opportunities: [
        {
          id: 'demo_upgrade',
          type: 'value_demonstration',
          title: 'You\'re Doing Great! 🚀',
          description: 'You\'ve automated 6 workflows successfully. See how Complete Platform users achieve 97% success rates.',
          urgency: 'medium',
          cta_text: 'Explore Complete Platform',
          cta_action: 'view_complete_features',
          value_props: [
            'Unlimited everything for $399/mo',
            'Advanced cross-tool analytics',
            '40% savings vs individual tools'
          ],
          estimated_roi: 'Users typically save 15+ hours/week'
        }
      ],
      success_metrics: [
        {
          label: 'Success Rate',
          value: '92%',
          trend: '+8%',
          trend_direction: 'up',
          benchmark: 'Your best yet!'
        },
        {
          label: 'Time Saved',
          value: '18.5 hours',
          trend: '+6 hours',
          trend_direction: 'up'
        },
        {
          label: 'Cost Savings',
          value: '$2,750',
          trend: '+$850',
          trend_direction: 'up'
        },
        {
          label: 'Satisfaction',
          value: '95%',
          trend: 'stable',
          trend_direction: 'stable'
        }
      ]
    };
  }
}

export const analyticsService = new AnalyticsService();
export default analyticsService;