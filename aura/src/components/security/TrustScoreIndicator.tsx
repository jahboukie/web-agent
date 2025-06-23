/**
 * Trust Score Indicator Component
 *
 * Displays Zero Trust security score with visual indicators,
 * risk factors, and security recommendations.
 */

import React, { useState, useEffect } from "react";
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  Info,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { apiService } from "../../services";
import {
  cn,
  getTrustScoreColor,
  getTrustScoreLabel,
  formatRelativeTime,
} from "../../lib/utils";

interface TrustAssessment {
  assessment_id: string;
  user_id: number;
  timestamp: string;
  trust_score: number;
  trust_level: string;
  risk_score: number;
  confidence_score: number;
  trust_factors: {
    authentication_strength: number;
    device_trust_score: number;
    location_trust_score: number;
    behavioral_trust_score: number;
    network_trust_score: number;
  };
  risk_factors: string[];
  required_actions: string[];
  session_restrictions: Record<string, any>;
  next_verification_in: number;
}

interface TrustScoreIndicatorProps {
  className?: string;
  showDetails?: boolean;
  size?: "sm" | "md" | "lg";
}

export function TrustScoreIndicator({
  className,
  showDetails = false,
  size = "md",
}: TrustScoreIndicatorProps) {
  const { user, trustScore, updateTrustScore } = useAuth();
  const [assessment, setAssessment] = useState<TrustAssessment | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [showFullDetails, setShowFullDetails] = useState(false);

  useEffect(() => {
    if (user && showDetails) {
      fetchTrustAssessment();
    }
  }, [user, showDetails]);

  const fetchTrustAssessment = async () => {
    if (!user) return;

    setIsLoading(true);
    try {
      const data = await apiService.getTrustAssessment();
      setAssessment(data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error("Failed to fetch trust assessment:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    await updateTrustScore();
    if (showDetails) {
      await fetchTrustAssessment();
    }
  };

  if (!user) return null;

  const score = trustScore ?? user.trust_score ?? 0;
  const scoreLabel = getTrustScoreLabel(score);
  const scoreColor = getTrustScoreColor(score);

  const sizeClasses = {
    sm: "h-6 w-6",
    md: "h-8 w-8",
    lg: "h-12 w-12",
  };

  const textSizeClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };

  return (
    <div className={cn("flex items-center space-x-2", className)}>
      {/* Trust Score Badge */}
      <div className="flex items-center space-x-2">
        <div className="relative">
          <Shield className={cn(sizeClasses[size], "text-gray-400")} />
          <div
            className={cn(
              "absolute inset-0 rounded-full",
              scoreColor.includes("very-high")
                ? "bg-green-500"
                : scoreColor.includes("high")
                  ? "bg-lime-500"
                  : scoreColor.includes("medium")
                    ? "bg-yellow-500"
                    : scoreColor.includes("low")
                      ? "bg-orange-500"
                      : "bg-red-500",
            )}
            style={{
              clipPath: `polygon(0 0, ${score * 100}% 0, ${score * 100}% 100%, 0 100%)`,
              opacity: 0.3,
            }}
          />
        </div>

        <div className="flex flex-col">
          <div className="flex items-center space-x-1">
            <span className={cn("font-medium", textSizeClasses[size])}>
              {Math.round(score * 100)}%
            </span>
            <span
              className={cn(
                "security-indicator",
                scoreColor,
                textSizeClasses[size],
              )}
            >
              {scoreLabel}
            </span>
          </div>

          {lastUpdated && (
            <span className="text-xs text-gray-500">
              Updated {formatRelativeTime(lastUpdated)}
            </span>
          )}
        </div>

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          title="Refresh trust score"
        >
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
        </button>
      </div>

      {/* Detailed View Toggle */}
      {showDetails && (
        <button
          onClick={() => setShowFullDetails(!showFullDetails)}
          className="text-xs text-primary-600 hover:text-primary-500 dark:text-primary-400"
        >
          {showFullDetails ? "Hide" : "Show"} Details
        </button>
      )}

      {/* Detailed Assessment */}
      {showDetails && showFullDetails && assessment && (
        <div className="absolute top-full left-0 mt-2 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4 z-50">
          <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Trust Assessment
              </h3>
              <span className="text-xs text-gray-500">
                ID: {assessment.assessment_id.slice(0, 8)}...
              </span>
            </div>

            {/* Trust Factors */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Trust Factors
              </h4>
              <div className="space-y-2">
                {Object.entries(assessment.trust_factors).map(
                  ([factor, value]) => (
                    <div
                      key={factor}
                      className="flex items-center justify-between"
                    >
                      <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                        {factor.replace(/_/g, " ")}
                      </span>
                      <div className="flex items-center space-x-2">
                        <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                          <div
                            className={cn(
                              "h-2 rounded-full",
                              value >= 0.8
                                ? "bg-green-500"
                                : value >= 0.6
                                  ? "bg-lime-500"
                                  : value >= 0.4
                                    ? "bg-yellow-500"
                                    : value >= 0.2
                                      ? "bg-orange-500"
                                      : "bg-red-500",
                            )}
                            style={{ width: `${value * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600 dark:text-gray-400 w-8">
                          {Math.round(value * 100)}%
                        </span>
                      </div>
                    </div>
                  ),
                )}
              </div>
            </div>

            {/* Risk Factors */}
            {assessment.risk_factors.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Risk Factors
                </h4>
                <div className="space-y-1">
                  {assessment.risk_factors.map((factor, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                        {factor.replace(/_/g, " ")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Required Actions */}
            {assessment.required_actions.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Required Actions
                </h4>
                <div className="space-y-1">
                  {assessment.required_actions.map((action, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <Info className="h-4 w-4 text-blue-500" />
                      <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                        {action.replace(/_/g, " ")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Session Restrictions */}
            {Object.keys(assessment.session_restrictions).length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Session Restrictions
                </h4>
                <div className="space-y-1">
                  {Object.entries(assessment.session_restrictions).map(
                    ([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center justify-between"
                      >
                        <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
                          {key.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs text-gray-900 dark:text-white">
                          {typeof value === "boolean"
                            ? value
                              ? "Yes"
                              : "No"
                            : String(value)}
                        </span>
                      </div>
                    ),
                  )}
                </div>
              </div>
            )}

            {/* Next Verification */}
            <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  Next verification in:
                </span>
                <span className="text-xs text-gray-900 dark:text-white">
                  {Math.round(assessment.next_verification_in / 60)} minutes
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  Confidence score:
                </span>
                <span className="text-xs text-gray-900 dark:text-white">
                  {Math.round(assessment.confidence_score * 100)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
