/**
 * Tenant Management Component
 *
 * Enterprise tenant management interface for WebAgent Aura.
 * Provides tenant creation, configuration, and monitoring capabilities.
 */

import React, { useState, useEffect } from "react";
import {
  Building,
  Users,
  Shield,
  Settings,
  Plus,
  Edit,
  Trash2,
  CheckCircle,
  AlertCircle,
  Eye,
} from "lucide-react";
import { usePermissions } from "../../contexts/AuthContext";
import { apiService } from "../../services";
import { cn, formatNumber, formatDate } from "../../lib/utils";

interface Tenant {
  id: number;
  tenant_id: string;
  name: string;
  display_name: string;
  domain: string;
  is_active: boolean;
  is_enterprise: boolean;
  compliance_level: string;
  subscription_tier: string;
  max_users: number;
  current_users: number;
  max_concurrent_sessions: number;
  api_rate_limit: number;
  enforce_sso: boolean;
  require_mfa: boolean;
  session_timeout_minutes: number;
  data_region: string;
  encryption_required: boolean;
  audit_retention_days: number;
  admin_email: string;
  created_at: string;
  updated_at: string;
}

export function TenantManagement() {
  const { isAdmin } = usePermissions();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    if (isAdmin()) {
      fetchTenants();
    }
  }, []);

  const fetchTenants = async () => {
    try {
      setIsLoading(true);
      // Mock data for demonstration
      const mockTenants: Tenant[] = [
        {
          id: 1,
          tenant_id: "acme-corp",
          name: "ACME Corporation",
          display_name: "ACME Corp",
          domain: "acme.com",
          is_active: true,
          is_enterprise: true,
          compliance_level: "restricted",
          subscription_tier: "enterprise",
          max_users: 1000,
          current_users: 245,
          max_concurrent_sessions: 500,
          api_rate_limit: 10000,
          enforce_sso: true,
          require_mfa: true,
          session_timeout_minutes: 480,
          data_region: "us-east-1",
          encryption_required: true,
          audit_retention_days: 2555,
          admin_email: "admin@acme.com",
          created_at: "2024-01-15T10:00:00Z",
          updated_at: "2024-06-20T14:30:00Z",
        },
        {
          id: 2,
          tenant_id: "startup-inc",
          name: "Startup Inc",
          display_name: "Startup Inc",
          domain: "startup.com",
          is_active: true,
          is_enterprise: false,
          compliance_level: "internal",
          subscription_tier: "professional",
          max_users: 50,
          current_users: 12,
          max_concurrent_sessions: 25,
          api_rate_limit: 1000,
          enforce_sso: false,
          require_mfa: false,
          session_timeout_minutes: 240,
          data_region: "us-west-2",
          encryption_required: false,
          audit_retention_days: 90,
          admin_email: "admin@startup.com",
          created_at: "2024-03-10T09:15:00Z",
          updated_at: "2024-06-18T11:20:00Z",
        },
      ];

      setTenants(mockTenants);
    } catch (err: any) {
      setError(err.message || "Failed to load tenants");
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAdmin()) {
    return (
      <div className="text-center py-12">
        <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          Access Denied
        </h3>
        <p className="text-gray-600 dark:text-gray-400">
          You don't have permission to manage tenants.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-24 bg-gray-200 dark:bg-gray-700 rounded-lg"
              ></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Tenant Management
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage enterprise tenants and their configurations
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="h-4 w-4" />
          <span>Create Tenant</span>
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
          <div className="flex">
            <AlertCircle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <p className="text-sm text-red-800 dark:text-red-400">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tenants Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {tenants.map((tenant) => (
          <TenantCard
            key={tenant.id}
            tenant={tenant}
            onEdit={() => setSelectedTenant(tenant)}
            onView={() => setSelectedTenant(tenant)}
          />
        ))}
      </div>

      {/* Empty State */}
      {tenants.length === 0 && !isLoading && (
        <div className="text-center py-12">
          <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No tenants found
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Get started by creating your first tenant.
          </p>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
          >
            Create Tenant
          </button>
        </div>
      )}
    </div>
  );
}

// Tenant Card Component
interface TenantCardProps {
  tenant: Tenant;
  onEdit: () => void;
  onView: () => void;
}

function TenantCard({ tenant, onEdit, onView }: TenantCardProps) {
  const complianceColors = {
    internal:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400",
    confidential:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400",
    restricted:
      "bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400",
    top_secret: "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400",
  };

  const tierColors = {
    basic: "bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400",
    professional:
      "bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400",
    enterprise:
      "bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400",
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <Building className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {tenant.display_name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {tenant.domain}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                tenant.is_active
                  ? "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                  : "bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400",
              )}
            >
              {tenant.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
      </div>

      <div className="card-body">
        <div className="space-y-4">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">Users</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {formatNumber(tenant.current_users)} /{" "}
                {formatNumber(tenant.max_users)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Compliance
              </p>
              <span
                className={cn(
                  "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize",
                  complianceColors[
                    tenant.compliance_level as keyof typeof complianceColors
                  ],
                )}
              >
                {tenant.compliance_level.replace("_", " ")}
              </span>
            </div>
          </div>

          {/* Subscription Tier */}
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
              Subscription
            </p>
            <span
              className={cn(
                "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize",
                tierColors[tenant.subscription_tier as keyof typeof tierColors],
              )}
            >
              {tenant.subscription_tier}
            </span>
          </div>

          {/* Security Features */}
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              Security Features
            </p>
            <div className="flex flex-wrap gap-2">
              {tenant.enforce_sso && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                  SSO
                </span>
              )}
              {tenant.require_mfa && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                  MFA
                </span>
              )}
              {tenant.encryption_required && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                  Encryption
                </span>
              )}
            </div>
          </div>

          {/* Last Updated */}
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Last updated: {formatDate(tenant.updated_at)}
            </p>
          </div>
        </div>
      </div>

      <div className="card-footer">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={onView}
            className="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <Eye className="h-4 w-4" />
            <span>View Details</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onEdit}
              className="flex items-center space-x-1 text-sm text-primary-600 hover:text-primary-500 dark:text-primary-400"
            >
              <Edit className="h-4 w-4" />
              <span>Edit</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
