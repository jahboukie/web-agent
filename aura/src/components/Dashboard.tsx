/**
 * Dashboard Component
 * 
 * Main dashboard for WebAgent Aura with security monitoring,
 * task management, and enterprise features.
 */

import React, { useState, useEffect } from 'react';
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
  Eye
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { TrustScoreIndicator } from './security/TrustScoreIndicator';
import { apiService } from '../services';
import { cn, formatNumber, formatRelativeTime } from '../lib/utils';

interface DashboardStats {
  total_tasks: number;
  active_sessions: number;
  security_events: number;
  trust_score_avg: number;
  recent_activities: Activity[];
}

interface Activity {
  id: string;
  type: string;
  description: string;
  timestamp: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  user?: string;
}

export function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setIsLoading(true);
      // In a real implementation, this would fetch from the API
      // For now, we'll use mock data
      const mockStats: DashboardStats = {
        total_tasks: 42,
        active_sessions: 8,
        security_events: 3,
        trust_score_avg: 0.87,
        recent_activities: [
          {
            id: '1',
            type: 'authentication',
            description: 'User logged in from new device',
            timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
            severity: 'medium',
            user: 'john.doe@company.com'
          },
          {
            id: '2',
            type: 'task_completed',
            description: 'Automation task completed successfully',
            timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
            severity: 'low'
          },
          {
            id: '3',
            type: 'security_scan',
            description: 'Zero Trust assessment completed',
            timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
            severity: 'low'
          }
        ]
      };
      
      setStats(mockStats);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
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
              <div key={i} className="h-32 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Welcome back, {user?.full_name?.split(' ')[0]}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Here's what's happening with your WebAgent platform
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <TrustScoreIndicator showDetails size="lg" />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Tasks"
          value={formatNumber(stats?.total_tasks || 0)}
          icon={<Activity className="h-6 w-6" />}
          color="blue"
          trend="+12%"
        />
        
        <StatCard
          title="Active Sessions"
          value={formatNumber(stats?.active_sessions || 0)}
          icon={<Users className="h-6 w-6" />}
          color="green"
          trend="+5%"
        />
        
        <StatCard
          title="Security Events"
          value={formatNumber(stats?.security_events || 0)}
          icon={<Shield className="h-6 w-6" />}
          color="orange"
          trend="-8%"
        />
        
        <StatCard
          title="Avg Trust Score"
          value={`${Math.round((stats?.trust_score_avg || 0) * 100)}%`}
          icon={<Lock className="h-6 w-6" />}
          color="purple"
          trend="+3%"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activities */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Recent Activities
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              {stats?.recent_activities.map((activity) => (
                <ActivityItem key={activity.id} activity={activity} />
              ))}
            </div>
          </div>
        </div>

        {/* Security Overview */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Security Overview
            </h3>
          </div>
          <div className="card-body">
            <div className="space-y-4">
              <SecurityMetric
                label="Zero Trust Status"
                value="Active"
                status="success"
                icon={<Shield className="h-5 w-5" />}
              />
              <SecurityMetric
                label="Encryption Status"
                value="AES-256 Enabled"
                status="success"
                icon={<Lock className="h-5 w-5" />}
              />
              <SecurityMetric
                label="SIEM Integration"
                value="Connected"
                status="success"
                icon={<Server className="h-5 w-5" />}
              />
              <SecurityMetric
                label="Audit Logging"
                value="Active"
                status="success"
                icon={<Eye className="h-5 w-5" />}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Quick Actions
          </h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <QuickActionButton
              title="Create New Task"
              description="Start a new automation task"
              icon={<Activity className="h-6 w-6" />}
              onClick={() => console.log('Create task')}
            />
            <QuickActionButton
              title="Security Scan"
              description="Run Zero Trust assessment"
              icon={<Shield className="h-6 w-6" />}
              onClick={() => console.log('Security scan')}
            />
            <QuickActionButton
              title="View Audit Logs"
              description="Review security events"
              icon={<Eye className="h-6 w-6" />}
              onClick={() => console.log('View logs')}
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
  color: 'blue' | 'green' | 'orange' | 'purple';
  trend?: string;
}

function StatCard({ title, value, icon, color, trend }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    orange: 'bg-orange-500',
    purple: 'bg-purple-500',
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
            {trend && (
              <div className="flex items-center mt-1">
                <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                <span className="text-sm text-green-600 dark:text-green-400">{trend}</span>
              </div>
            )}
          </div>
          <div className={cn('p-3 rounded-lg', colorClasses[color])}>
            <div className="text-white">{icon}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Activity Item Component
interface ActivityItemProps {
  activity: Activity;
}

function ActivityItem({ activity }: ActivityItemProps) {
  const severityColors = {
    low: 'text-green-600 dark:text-green-400',
    medium: 'text-yellow-600 dark:text-yellow-400',
    high: 'text-orange-600 dark:text-orange-400',
    critical: 'text-red-600 dark:text-red-400',
  };

  return (
    <div className="flex items-start space-x-3">
      <div className="flex-shrink-0">
        <div className={cn('w-2 h-2 rounded-full mt-2', {
          'bg-green-500': activity.severity === 'low',
          'bg-yellow-500': activity.severity === 'medium',
          'bg-orange-500': activity.severity === 'high',
          'bg-red-500': activity.severity === 'critical',
        })} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 dark:text-white">
          {activity.description}
        </p>
        <div className="flex items-center space-x-2 mt-1">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {formatRelativeTime(activity.timestamp)}
          </span>
          {activity.user && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              • {activity.user}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// Security Metric Component
interface SecurityMetricProps {
  label: string;
  value: string;
  status: 'success' | 'warning' | 'error';
  icon: React.ReactNode;
}

function SecurityMetric({ label, value, status, icon }: SecurityMetricProps) {
  const statusColors = {
    success: 'text-green-600 dark:text-green-400',
    warning: 'text-yellow-600 dark:text-yellow-400',
    error: 'text-red-600 dark:text-red-400',
  };

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className={cn(statusColors[status])}>{icon}</div>
        <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
      </div>
      <span className={cn('text-sm font-medium', statusColors[status])}>
        {value}
      </span>
    </div>
  );
}

// Quick Action Button Component
interface QuickActionButtonProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
}

function QuickActionButton({ title, description, icon, onClick }: QuickActionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="p-4 text-left border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
    >
      <div className="flex items-center space-x-3">
        <div className="text-primary-600">{icon}</div>
        <div>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            {title}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </p>
        </div>
      </div>
    </button>
  );
}
