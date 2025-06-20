/**
 * Savings Calculator Component
 * 
 * Interactive calculator that demonstrates ROI and cost savings
 * to drive conversion through value demonstration.
 */

import React, { useState, useEffect } from 'react';
import { 
  Calculator, 
  DollarSign, 
  TrendingUp, 
  Clock, 
  Target,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { analyticsService } from '../../services';
import { cn } from '../../lib/utils';

interface CalculatorInputs {
  hourlyRate: number;
  hoursPerWeek: number;
  automationTasks: number;
  timePerTask: number;
}

interface SavingsResults {
  weeklyTimeSaved: number;
  monthlyTimeSaved: number;
  annualTimeSaved: number;
  weeklyValueSaved: number;
  monthlyValueSaved: number;
  annualValueSaved: number;
  subscriptionCost: number;
  netMonthlySavings: number;
  netAnnualSavings: number;
  roiPercentage: number;
  paybackPeriod: number;
}

interface InputFieldProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  prefix?: string;
  suffix?: string;
  description?: string;
}

const InputField: React.FC<InputFieldProps> = ({
  label,
  value,
  onChange,
  min = 0,
  max = 1000,
  step = 1,
  prefix,
  suffix,
  description
}) => (
  <div className="space-y-2">
    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
      {label}
    </label>
    <div className="relative">
      {prefix && (
        <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400">
          {prefix}
        </span>
      )}
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        className={cn(
          "w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg",
          "bg-white dark:bg-gray-800 text-gray-900 dark:text-white",
          "focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
          prefix && "pl-8",
          suffix && "pr-12"
        )}
      />
      {suffix && (
        <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400">
          {suffix}
        </span>
      )}
    </div>
    {description && (
      <p className="text-xs text-gray-600 dark:text-gray-400">{description}</p>
    )}
  </div>
);

interface ResultCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'purple' | 'yellow';
  highlight?: boolean;
}

const ResultCard: React.FC<ResultCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color,
  highlight
}) => {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500',
    yellow: 'bg-yellow-500'
  };

  const bgClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    green: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
    purple: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
  };

  return (
    <div className={cn(
      "card border-2",
      highlight ? bgClasses[color] : "border-gray-200 dark:border-gray-700"
    )}>
      <div className="card-body">
        <div className="flex items-center space-x-3 mb-2">
          <div className={cn('p-2 rounded-lg', colorClasses[color])}>
            <div className="text-white">{icon}</div>
          </div>
          <h3 className="font-medium text-gray-900 dark:text-white">{title}</h3>
        </div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
          {value}
        </p>
        {subtitle && (
          <p className="text-sm text-gray-600 dark:text-gray-400">{subtitle}</p>
        )}
      </div>
    </div>
  );
};

export const SavingsCalculator: React.FC = () => {
  const [inputs, setInputs] = useState<CalculatorInputs>({
    hourlyRate: 75,
    hoursPerWeek: 40,
    automationTasks: 10,
    timePerTask: 30
  });

  const [results, setResults] = useState<SavingsResults | null>(null);
  const [selectedTier, setSelectedTier] = useState<'complete' | 'enterprise'>('complete');

  useEffect(() => {
    calculateSavings();
  }, [inputs, selectedTier]);

  const calculateSavings = () => {
    const { hourlyRate, hoursPerWeek, automationTasks, timePerTask } = inputs;
    
    // Calculate time savings
    const weeklyTimeSaved = (automationTasks * timePerTask) / 60; // Convert minutes to hours
    const monthlyTimeSaved = weeklyTimeSaved * 4.33; // Average weeks per month
    const annualTimeSaved = weeklyTimeSaved * 52;
    
    // Calculate value savings
    const weeklyValueSaved = weeklyTimeSaved * hourlyRate;
    const monthlyValueSaved = monthlyTimeSaved * hourlyRate;
    const annualValueSaved = annualTimeSaved * hourlyRate;
    
    // Subscription costs
    const subscriptionCost = selectedTier === 'complete' ? 399 : 1499;
    
    // Net savings
    const netMonthlySavings = monthlyValueSaved - subscriptionCost;
    const netAnnualSavings = annualValueSaved - (subscriptionCost * 12);
    
    // ROI calculation
    const roiPercentage = (netAnnualSavings / (subscriptionCost * 12)) * 100;
    
    // Payback period (months)
    const paybackPeriod = subscriptionCost / Math.max(monthlyValueSaved, 1);
    
    setResults({
      weeklyTimeSaved,
      monthlyTimeSaved,
      annualTimeSaved,
      weeklyValueSaved,
      monthlyValueSaved,
      annualValueSaved,
      subscriptionCost,
      netMonthlySavings,
      netAnnualSavings,
      roiPercentage,
      paybackPeriod
    });
  };

  const updateInput = (field: keyof CalculatorInputs, value: number) => {
    setInputs(prev => ({ ...prev, [field]: value }));
  };

  const handleUpgrade = async () => {
    await analyticsService.trackEvent('savings_calculator_upgrade', {
      inputs,
      results,
      selected_tier: selectedTier
    });
    
    window.location.href = `/billing/upgrade?tier=${selectedTier}_platform&calculator=true`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <Calculator className="h-12 w-12 text-blue-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          ROI Savings Calculator
        </h2>
        <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Calculate your potential savings with WebAgent's AI-powered automation. 
          See how much time and money you could save with our Complete Platform.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Section */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Your Current Situation
            </h3>
          </div>
          <div className="card-body space-y-4">
            <InputField
              label="Your Hourly Rate"
              value={inputs.hourlyRate}
              onChange={(value) => updateInput('hourlyRate', value)}
              min={10}
              max={500}
              step={5}
              prefix="$"
              description="What do you charge per hour or your salary equivalent?"
            />
            
            <InputField
              label="Hours Worked Per Week"
              value={inputs.hoursPerWeek}
              onChange={(value) => updateInput('hoursPerWeek', value)}
              min={1}
              max={80}
              suffix="hrs"
              description="How many hours do you work per week?"
            />
            
            <InputField
              label="Automation Tasks Per Week"
              value={inputs.automationTasks}
              onChange={(value) => updateInput('automationTasks', value)}
              min={1}
              max={100}
              suffix="tasks"
              description="How many repetitive tasks could be automated?"
            />
            
            <InputField
              label="Time Per Task"
              value={inputs.timePerTask}
              onChange={(value) => updateInput('timePerTask', value)}
              min={1}
              max={240}
              suffix="min"
              description="Average time spent on each task"
            />

            {/* Tier Selection */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                WebAgent Plan
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setSelectedTier('complete')}
                  className={cn(
                    "p-3 rounded-lg border text-sm font-medium transition-all",
                    selectedTier === 'complete'
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                      : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                  )}
                >
                  Complete Platform
                  <div className="text-xs text-gray-500">$399/mo</div>
                </button>
                <button
                  onClick={() => setSelectedTier('enterprise')}
                  className={cn(
                    "p-3 rounded-lg border text-sm font-medium transition-all",
                    selectedTier === 'enterprise'
                      ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300"
                      : "border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300"
                  )}
                >
                  Enterprise Platform
                  <div className="text-xs text-gray-500">$1,499/mo</div>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Results Section */}
        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Your Potential Savings
              </h3>
            </div>
            <div className="card-body">
              {results && (
                <div className="grid grid-cols-1 gap-4">
                  <ResultCard
                    title="Time Saved Monthly"
                    value={`${results.monthlyTimeSaved.toFixed(1)} hours`}
                    subtitle="More time for strategic work"
                    icon={<Clock className="h-5 w-5" />}
                    color="blue"
                  />
                  
                  <ResultCard
                    title="Value Generated Monthly"
                    value={`$${results.monthlyValueSaved.toLocaleString()}`}
                    subtitle="Based on your hourly rate"
                    icon={<DollarSign className="h-5 w-5" />}
                    color="green"
                  />
                  
                  <ResultCard
                    title="Net Monthly Savings"
                    value={`$${results.netMonthlySavings.toLocaleString()}`}
                    subtitle="After subscription cost"
                    icon={<TrendingUp className="h-5 w-5" />}
                    color="purple"
                    highlight={results.netMonthlySavings > 0}
                  />
                  
                  <ResultCard
                    title="Annual ROI"
                    value={`${results.roiPercentage.toFixed(0)}%`}
                    subtitle={`Payback in ${results.paybackPeriod.toFixed(1)} months`}
                    icon={<Target className="h-5 w-5" />}
                    color="yellow"
                    highlight={results.roiPercentage > 100}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Call to Action */}
          {results && results.netMonthlySavings > 0 && (
            <div className="card border-green-200 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 dark:border-green-800">
              <div className="card-body text-center">
                <Sparkles className="h-8 w-8 text-green-500 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Great ROI Potential!
                </h3>
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  You could save <strong>${results.netAnnualSavings.toLocaleString()}</strong> annually 
                  with a {results.roiPercentage.toFixed(0)}% ROI. Start your automation journey today!
                </p>
                <button 
                  onClick={handleUpgrade}
                  className="btn btn-primary flex items-center justify-center space-x-2 mx-auto"
                >
                  <span>Start Saving with {selectedTier === 'complete' ? 'Complete' : 'Enterprise'} Platform</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
