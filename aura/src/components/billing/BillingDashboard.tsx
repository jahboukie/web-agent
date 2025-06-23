/**
 * Billing Dashboard Component
 *
 * Comprehensive billing management with strategic upgrade flows
 * and conversion-optimized subscription management.
 */

import React, { useState, useEffect } from "react";
import {
  CreditCard,
  Calendar,
  DollarSign,
  Download,
  AlertCircle,
  CheckCircle,
  Crown,
  TrendingUp,
  Gift,
  ArrowRight,
} from "lucide-react";
import { analyticsService } from "../../services";
import { cn } from "../../lib/utils";

interface BillingInfo {
  subscription: any;
  payment_method_type: string;
  last_four_digits: string;
  recent_invoices: any[];
  payment_history: any[];
  next_charge_amount: number;
  next_charge_date: string;
  account_credits: number;
  active_discounts: any[];
}

interface InvoiceItemProps {
  invoice: any;
}

const InvoiceItem: React.FC<InvoiceItemProps> = ({ invoice }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "paid":
        return "text-green-600 bg-green-100 dark:bg-green-900 dark:text-green-200";
      case "pending":
        return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-200";
      case "failed":
        return "text-red-600 bg-red-100 dark:bg-red-900 dark:text-red-200";
      default:
        return "text-gray-600 bg-gray-100 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  return (
    <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-center space-x-4">
        <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
          <CreditCard className="h-5 w-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p className="font-medium text-gray-900 dark:text-white">
            {invoice.description}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {new Date(invoice.date).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-right">
          <p className="font-medium text-gray-900 dark:text-white">
            ${invoice.amount.toFixed(2)}
          </p>
          <span
            className={cn(
              "inline-flex px-2 py-1 text-xs font-medium rounded-full",
              getStatusColor(invoice.status),
            )}
          >
            {invoice.status}
          </span>
        </div>

        {invoice.download_url && (
          <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <Download className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
};

interface UpgradePromptProps {
  currentTier: string;
  onUpgrade: () => void;
}

const UpgradePrompt: React.FC<UpgradePromptProps> = ({
  currentTier,
  onUpgrade,
}) => {
  if (currentTier !== "free") return null;

  return (
    <div className="card border-yellow-200 bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 dark:border-yellow-800">
      <div className="card-body">
        <div className="flex items-start space-x-4">
          <Crown className="h-8 w-8 text-yellow-500 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Unlock Premium Features
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              You're getting great value from WebAgent! Upgrade to unlock
              unlimited usage, advanced analytics, and priority support.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                <TrendingUp className="h-6 w-6 text-blue-500 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Unlimited Usage
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  No more limits
                </p>
              </div>
              <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                <Gift className="h-6 w-6 text-green-500 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  40% Savings
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  Complete Platform
                </p>
              </div>
              <div className="text-center p-3 bg-white dark:bg-gray-800 rounded-lg">
                <CheckCircle className="h-6 w-6 text-purple-500 mx-auto mb-2" />
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  Priority Support
                </p>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  Expert assistance
                </p>
              </div>
            </div>

            <button
              onClick={onUpgrade}
              className="w-full btn btn-primary flex items-center justify-center space-x-2"
            >
              <span>Upgrade to Complete Platform - $399/mo</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const BillingDashboard: React.FC = () => {
  const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBillingInfo();
  }, []);

  const loadBillingInfo = async () => {
    try {
      setLoading(true);
      const data = await analyticsService.getBillingInfo();
      setBillingInfo(data);
      setError(null);
    } catch (err) {
      console.error("Failed to load billing info:", err);
      setError("Failed to load billing information");
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = () => {
    // Track upgrade intent
    analyticsService.trackEvent("billing_upgrade_clicked", {
      current_tier: billingInfo?.subscription.tier,
      source: "billing_dashboard",
    });

    // Redirect to pricing page
    window.location.href = "/analytics?tab=pricing";
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
        <button onClick={loadBillingInfo} className="btn btn-primary">
          Retry
        </button>
      </div>
    );
  }

  if (!billingInfo) return null;

  return (
    <div className="space-y-6">
      {/* Upgrade Prompt for Free Users */}
      <UpgradePrompt
        currentTier={billingInfo.subscription.tier}
        onUpgrade={handleUpgrade}
      />

      {/* Current Subscription */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Current Subscription
          </h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Plan
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {billingInfo.subscription.tier === "free"
                  ? "Free Tier"
                  : billingInfo.subscription.tier}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Monthly Cost
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                ${billingInfo.subscription.monthly_cost.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Next Billing
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {billingInfo.next_charge_date
                  ? new Date(billingInfo.next_charge_date).toLocaleDateString()
                  : "N/A"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Payment Method */}
      {billingInfo.payment_method_type && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Payment Method
            </h3>
          </div>
          <div className="card-body">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                <CreditCard className="h-6 w-6 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  •••• •••• •••• {billingInfo.last_four_digits}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {billingInfo.payment_method_type.toUpperCase()}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Account Credits & Discounts */}
      {(billingInfo.account_credits > 0 ||
        billingInfo.active_discounts.length > 0) && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Credits & Discounts
            </h3>
          </div>
          <div className="card-body">
            {billingInfo.account_credits > 0 && (
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg mb-4">
                <div className="flex items-center space-x-2">
                  <Gift className="h-5 w-5 text-green-600" />
                  <span className="font-medium text-green-800 dark:text-green-200">
                    Account Credits
                  </span>
                </div>
                <span className="font-bold text-green-800 dark:text-green-200">
                  ${billingInfo.account_credits.toFixed(2)}
                </span>
              </div>
            )}

            {billingInfo.active_discounts.map((discount, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg"
              >
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-blue-800 dark:text-blue-200">
                    {discount.description}
                  </span>
                </div>
                <span className="font-bold text-blue-800 dark:text-blue-200">
                  -${discount.amount.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Invoices */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Invoices
          </h3>
        </div>
        <div className="card-body">
          <div className="space-y-4">
            {billingInfo.recent_invoices.length > 0 ? (
              billingInfo.recent_invoices.map((invoice, index) => (
                <InvoiceItem key={index} invoice={invoice} />
              ))
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                <Calendar className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No invoices yet</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
