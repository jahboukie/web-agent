/**
 * Metrics Visualization Component
 * 
 * Comprehensive charts and metrics displays for Reader, Planner, and Actor
 * components with enterprise analytics and performance dashboards.
 */

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Eye, 
  Brain, 
  Zap, 
  Clock, 
  Target,
  Activity,
  AlertCircle,
  CheckCircle,
  ArrowUp,
  ArrowDown
} from 'lucide-react';
import { analyticsService } from '../../services';
import { cn } from '../../lib/utils';

interface MetricData {
  label: string;
  value: number;
  change: number;
  trend: 'up' | 'down' | 'stable';
  color: string;
}

interface ChartData {
  date: string;
  value: number;
  label?: string;
}

interface ComponentMetrics {
  component: string;
  total_requests: number;
  successful_requests: number;
  success_rate: number;
  avg_response_time_ms: number;
  performance_trend: ChartData[];
  usage_trend: ChartData[];
}

interface MetricCardProps {
  title: string;
  value: string;
  change: number;
  trend: 'up' | 'down' | 'stable';
  icon: React.ReactNode;
  color: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ 
  title, 
  value, 
  change, 
  trend, 
  icon, 
  color 
}) => {
  const getTrendIcon = () => {
    if (trend === 'up') return <ArrowUp className="h-4 w-4 text-green-500" />;
    if (trend === 'down') return <ArrowDown className="h-4 w-4 text-red-500" />;
    return <div className="h-4 w-4" />;
  };

  const getTrendColor = () => {
    if (trend === 'up') return 'text-green-600 dark:text-green-400';
    if (trend === 'down') return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <div className={cn('p-3 rounded-lg', `bg-${color}-500`)}>
            <div className="text-white">{icon}</div>
          </div>
          <div className="flex items-center space-x-1">
            {getTrendIcon()}
            <span className={cn('text-sm font-medium', getTrendColor())}>
              {change > 0 ? '+' : ''}{change.toFixed(1)}%
            </span>
          </div>
        </div>
        
        <div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {value}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {title}
          </p>
        </div>
      </div>
    </div>
  );
};

interface SimpleChartProps {
  data: ChartData[];
  color: string;
  height?: number;
}

const SimpleChart: React.FC<SimpleChartProps> = ({ data, color, height = 100 }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-gray-400">
        <BarChart3 className="h-8 w-8" />
      </div>
    );
  }

  const maxValue = Math.max(...data.map(d => d.value));
  const minValue = Math.min(...data.map(d => d.value));
  const range = maxValue - minValue || 1;

  return (
    <div className="relative" style={{ height }}>
      <svg width="100%" height="100%" className="overflow-visible">
        {data.map((point, index) => {
          const x = (index / (data.length - 1)) * 100;
          const y = ((maxValue - point.value) / range) * 80 + 10;
          
          return (
            <g key={index}>
              {index > 0 && (
                <line
                  x1={`${((index - 1) / (data.length - 1)) * 100}%`}
                  y1={`${((maxValue - data[index - 1].value) / range) * 80 + 10}%`}
                  x2={`${x}%`}
                  y2={`${y}%`}
                  stroke={`rgb(${color})`}
                  strokeWidth="2"
                  fill="none"
                />
              )}
              <circle
                cx={`${x}%`}
                cy={`${y}%`}
                r="3"
                fill={`rgb(${color})`}
                className="hover:r-4 transition-all"
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
};

interface ComponentDashboardProps {
  component: ComponentMetrics;
  color: string;
}

const ComponentDashboard: React.FC<ComponentDashboardProps> = ({ component, color }) => {
  const getComponentIcon = () => {
    switch (component.component) {
      case 'reader':
        return <Eye className="h-6 w-6" />;
      case 'planner':
        return <Brain className="h-6 w-6" />;
      case 'actor':
        return <Zap className="h-6 w-6" />;
      default:
        return <Activity className="h-6 w-6" />;
    }
  };

  const getStatusIcon = () => {
    if (component.success_rate >= 95) return <CheckCircle className="h-5 w-5 text-green-500" />;
    if (component.success_rate >= 85) return <AlertCircle className="h-5 w-5 text-yellow-500" />;
    return <AlertCircle className="h-5 w-5 text-red-500" />;
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center space-x-3">
          <div className={cn('p-2 rounded-lg', `bg-${color}-500`)}>
            <div className="text-white">{getComponentIcon()}</div>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
              {component.component} Analytics
            </h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon()}
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {component.success_rate.toFixed(1)}% success rate
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="card-body">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {component.total_requests.toLocaleString()}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Total Requests</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {component.successful_requests.toLocaleString()}
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Successful</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {component.avg_response_time_ms.toFixed(0)}ms
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Avg Response</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {component.success_rate.toFixed(1)}%
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Success Rate</p>
          </div>
        </div>

        {/* Performance Trend */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
            Performance Trend (Last 7 Days)
          </h4>
          <SimpleChart 
            data={component.performance_trend} 
            color={color === 'blue' ? '59, 130, 246' : color === 'purple' ? '147, 51, 234' : '34, 197, 94'} 
          />
        </div>

        {/* Usage Trend */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
            Usage Trend (Last 7 Days)
          </h4>
          <SimpleChart 
            data={component.usage_trend} 
            color={color === 'blue' ? '59, 130, 246' : color === 'purple' ? '147, 51, 234' : '34, 197, 94'} 
          />
        </div>
      </div>
    </div>
  );
};

export const MetricsVisualization: React.FC = () => {
  const [readerMetrics, setReaderMetrics] = useState<ComponentMetrics | null>(null);
  const [plannerMetrics, setPlannerMetrics] = useState<ComponentMetrics | null>(null);
  const [actorMetrics, setActorMetrics] = useState<ComponentMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      
      const [reader, planner, actor] = await Promise.all([
        analyticsService.getComponentMetrics('reader'),
        analyticsService.getComponentMetrics('planner'),
        analyticsService.getComponentMetrics('actor')
      ]);

      setReaderMetrics(reader);
      setPlannerMetrics(planner);
      setActorMetrics(actor);
      setError(null);
    } catch (err) {
      console.error('Failed to load metrics:', err);
      setError('Failed to load metrics data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-96 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
            ))}
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
        <button 
          onClick={loadMetrics}
          className="btn btn-primary"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Performance Analytics
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Comprehensive metrics across all AI components
          </p>
        </div>
        <button 
          onClick={loadMetrics}
          className="btn btn-secondary flex items-center space-x-2"
        >
          <Activity className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Component Dashboards */}
      <div className="space-y-6">
        {readerMetrics && (
          <ComponentDashboard component={readerMetrics} color="blue" />
        )}
        
        {plannerMetrics && (
          <ComponentDashboard component={plannerMetrics} color="purple" />
        )}
        
        {actorMetrics && (
          <ComponentDashboard component={actorMetrics} color="green" />
        )}
      </div>

      {/* Summary Metrics */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Platform Summary
          </h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <MetricCard
              title="Overall Success Rate"
              value="92.3%"
              change={2.1}
              trend="up"
              icon={<Target className="h-6 w-6" />}
              color="green"
            />
            <MetricCard
              title="Avg Response Time"
              value="1.2s"
              change={-5.3}
              trend="up"
              icon={<Clock className="h-6 w-6" />}
              color="blue"
            />
            <MetricCard
              title="Total Requests"
              value="12.4K"
              change={15.7}
              trend="up"
              icon={<TrendingUp className="h-6 w-6" />}
              color="purple"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
