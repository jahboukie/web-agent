/**
 * Pricing and Subscription Types
 *
 * Revenue-optimized pricing model with strategic tiered offerings
 */

export interface PricingTier {
  id: string;
  name: string;
  price: number;
  period: "month" | "year";
  description: string;
  features: string[];
  limits: {
    parses: number | "unlimited";
    plans: number | "unlimited";
    executions: number | "unlimited";
    storage_gb: number | "unlimited";
    api_calls: number | "unlimited";
  };
  upgrade_cta?: string;
  popular?: boolean;
  savings?: string;
  badge?: string;
}

export interface UserSubscription {
  tier: string;
  status: "active" | "cancelled" | "past_due" | "trialing";
  current_period_start: string;
  current_period_end: string;
  usage: {
    parses_used: number;
    plans_used: number;
    executions_used: number;
    storage_used_gb: number;
    api_calls_used: number;
  };
  limits: {
    parses: number | "unlimited";
    plans: number | "unlimited";
    executions: number | "unlimited";
    storage_gb: number | "unlimited";
    api_calls: number | "unlimited";
  };
  next_billing_date?: string;
  amount_due?: number;
}

export interface UsageMetrics {
  reader: {
    total_parses: number;
    successful_parses: number;
    failed_parses: number;
    success_rate: number;
    avg_parse_time_ms: number;
    domains_parsed: string[];
    performance_trend: { date: string; value: number }[];
  };
  planner: {
    total_plans: number;
    successful_plans: number;
    failed_plans: number;
    avg_confidence_score: number;
    avg_plan_complexity: number;
    plan_types: { type: string; count: number }[];
    confidence_trend: { date: string; value: number }[];
  };
  actor: {
    total_executions: number;
    successful_executions: number;
    failed_executions: number;
    success_rate: number;
    avg_execution_time_ms: number;
    actions_per_execution: number;
    error_categories: { category: string; count: number }[];
    performance_trend: { date: string; value: number }[];
  };
  unified: {
    total_workflows: number;
    end_to_end_success_rate: number;
    avg_workflow_time_ms: number;
    roi_metrics: {
      time_saved_hours: number;
      cost_saved_usd: number;
      automation_value: number;
    };
    user_satisfaction_score: number;
  };
}

export interface PlatformAnalytics {
  overview: {
    total_users: number;
    active_users_30d: number;
    revenue_mrr: number;
    churn_rate: number;
  };
  usage_by_tier: {
    tier: string;
    users: number;
    usage_percentage: number;
    revenue_percentage: number;
  }[];
  conversion_funnel: {
    free_signups: number;
    trial_conversions: number;
    paid_conversions: number;
    upgrades_to_enterprise: number;
  };
  feature_adoption: {
    feature: string;
    adoption_rate: number;
    usage_frequency: number;
  }[];
}

export const PRICING_TIERS: PricingTier[] = [
  {
    id: "free",
    name: "Free Tier",
    price: 0,
    period: "month",
    description:
      "Perfect for exploring WebAgent's revolutionary AI capabilities",
    features: [
      "200 website parses/month",
      "20 AI plans/month",
      "10 automations/month",
      "Basic analytics dashboard",
      "Community support",
      "Full platform UI access",
    ],
    limits: {
      parses: 200,
      plans: 20,
      executions: 10,
      storage_gb: 1,
      api_calls: 1000,
    },
    upgrade_cta: "See how Enterprise customers achieve 97% automation success",
  },
  {
    id: "reader_pro",
    name: "Reader Pro",
    price: 129,
    period: "month",
    description:
      "Unlimited intelligent website parsing with advanced analytics",
    features: [
      "Unlimited website parsing",
      "Advanced parsing analytics",
      "Performance optimization insights",
      "Element accuracy tracking",
      "Domain intelligence reports",
      "Priority support",
    ],
    limits: {
      parses: "unlimited",
      plans: 20,
      executions: 10,
      storage_gb: 10,
      api_calls: 10000,
    },
  },
  {
    id: "planner_pro",
    name: "Planner Pro",
    price: 179,
    period: "month",
    description:
      "Unlimited AI planning with confidence scoring and workflow analytics",
    features: [
      "Unlimited AI planning",
      "Workflow analytics dashboard",
      "Confidence scoring trends",
      "Goal completion tracking",
      "AI reasoning performance",
      "Advanced plan optimization",
    ],
    limits: {
      parses: 200,
      plans: "unlimited",
      executions: 10,
      storage_gb: 10,
      api_calls: 10000,
    },
  },
  {
    id: "actor_pro",
    name: "Actor Pro",
    price: 229,
    period: "month",
    description: "Unlimited automation execution with comprehensive monitoring",
    features: [
      "Unlimited automation execution",
      "Execution analytics dashboard",
      "Error monitoring & alerts",
      "ROI calculation tools",
      "Performance optimization",
      "Success rate tracking",
    ],
    limits: {
      parses: 200,
      plans: 20,
      executions: "unlimited",
      storage_gb: 25,
      api_calls: 25000,
    },
  },
  {
    id: "complete",
    name: "Complete Platform",
    price: 399,
    period: "month",
    description: "Full WebAgent platform with unified analytics - 40% savings!",
    features: [
      "Unlimited everything",
      "Unified cross-tool analytics",
      "Workflow optimization insights",
      "Advanced ROI calculations",
      "Integration monitoring",
      "Priority support & training",
    ],
    limits: {
      parses: "unlimited",
      plans: "unlimited",
      executions: "unlimited",
      storage_gb: 100,
      api_calls: 100000,
    },
    popular: true,
    savings: "40% vs individual tools",
    badge: "Best Value",
  },
  {
    id: "enterprise",
    name: "Enterprise Platform",
    price: 1499,
    period: "month",
    description:
      "Enterprise-grade platform with dedicated support and compliance",
    features: [
      "Everything in Complete Platform",
      "Advanced compliance dashboards",
      "Custom branding & white-label",
      "Dedicated Customer Success Manager",
      "SLA monitoring & guarantees",
      "Early access to new features",
      "Custom integrations",
      "Advanced security controls",
    ],
    limits: {
      parses: "unlimited",
      plans: "unlimited",
      executions: "unlimited",
      storage_gb: "unlimited",
      api_calls: "unlimited",
    },
    badge: "Enterprise",
  },
];

export const ADD_ON_PRICING = [
  {
    id: "advanced_analytics",
    name: "Advanced Analytics Dashboard",
    price: 99,
    period: "month",
    description: "Enhanced compliance reporting and custom insights",
    compatible_tiers: ["reader_pro", "planner_pro", "actor_pro", "complete"],
  },
];

export interface UpgradePrompt {
  trigger: "usage_threshold" | "feature_gate" | "billing_cycle";
  threshold_percentage: number;
  title: string;
  message: string;
  cta_text: string;
  cta_action: string;
  urgency: "low" | "medium" | "high";
  value_props: string[];
}

export const UPGRADE_PROMPTS: UpgradePrompt[] = [
  {
    trigger: "usage_threshold",
    threshold_percentage: 80,
    title: "Approaching Usage Limit",
    message:
      "You've used 80% of your monthly allocation. Upgrade to avoid interruptions.",
    cta_text: "Upgrade Now",
    cta_action: "open_pricing",
    urgency: "medium",
    value_props: [
      "Never hit limits again",
      "Advanced analytics included",
      "40% savings with Complete Platform",
    ],
  },
  {
    trigger: "feature_gate",
    threshold_percentage: 0,
    title: "Unlock Advanced Analytics",
    message:
      "Enterprise customers achieve 3x better automation ROI with advanced insights.",
    cta_text: "See Enterprise Features",
    cta_action: "view_enterprise",
    urgency: "low",
    value_props: [
      "Compliance dashboards",
      "Custom success metrics",
      "Dedicated support team",
    ],
  },
];
