/**
 * Enhanced Header Bar Component
 * Based on WebAgent Analytics Dashboard Wireframes
 * 
 * Features:
 * - Logo and branding
 * - User avatar and info
 * - Current plan status with upgrade CTA
 * - Notifications bell
 * - Responsive design
 */

import React, { useState } from 'react';
import { Bell, ChevronDown, Crown, Zap, Shield, Star } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { cn } from '../../lib/utils';

interface HeaderBarProps {
  className?: string;
  onUpgradeClick?: () => void;
  onNotificationClick?: () => void;
}

interface Notification {
  id: string;
  type: 'info' | 'warning' | 'success' | 'upgrade';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

// Mock notifications - in real app, these would come from API
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'upgrade',
    title: 'Upgrade Available',
    message: 'Unlock advanced analytics with Complete Platform - Save 40%!',
    timestamp: '2 hours ago',
    read: false,
  },
  {
    id: '2',
    type: 'success',
    title: 'Automation Success',
    message: 'Your workflow completed successfully with 98% accuracy',
    timestamp: '4 hours ago',
    read: false,
  },
  {
    id: '3',
    type: 'warning',
    title: 'Usage Alert',
    message: 'You\'ve used 85% of your monthly parsing quota',
    timestamp: '1 day ago',
    read: true,
  },
];

const planIcons = {
  free: Zap,
  reader_pro: Star,
  planner_pro: Crown,
  actor_pro: Shield,
  complete: Crown,
  enterprise: Shield,
};

const planColors = {
  free: 'text-gray-600 bg-gray-100',
  reader_pro: 'text-blue-600 bg-blue-100',
  planner_pro: 'text-purple-600 bg-purple-100',
  actor_pro: 'text-green-600 bg-green-100',
  complete: 'text-orange-600 bg-orange-100',
  enterprise: 'text-red-600 bg-red-100',
};

export function HeaderBar({ className, onUpgradeClick, onNotificationClick }: HeaderBarProps) {
  const { user } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Mock user plan - in real app, this would come from user context
  const userPlan = user?.subscription_tier || 'free';
  const planName = userPlan.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  const PlanIcon = planIcons[userPlan as keyof typeof planIcons] || Zap;
  const planColorClass = planColors[userPlan as keyof typeof planColors] || planColors.free;

  const unreadCount = mockNotifications.filter(n => !n.read).length;

  const handleNotificationClick = () => {
    setShowNotifications(!showNotifications);
    onNotificationClick?.();
  };

  const handleUpgradeClick = () => {
    setShowNotifications(false);
    setShowUserMenu(false);
    onUpgradeClick?.();
  };

  return (
    <header className={cn(
      'bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700',
      'px-4 py-3 flex items-center justify-between',
      className
    )}>
      {/* Logo and Brand */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">W</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">WebAgent</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Analytics Dashboard</p>
          </div>
        </div>
      </div>

      {/* Right Side: Plan Status, Notifications, User Menu */}
      <div className="flex items-center space-x-4">
        {/* Plan Status */}
        <div className={cn(
          'flex items-center space-x-2 px-3 py-1.5 rounded-full text-sm font-medium',
          planColorClass
        )}>
          <PlanIcon className="h-4 w-4" />
          <span>{planName}</span>
          {userPlan === 'free' && (
            <button
              onClick={handleUpgradeClick}
              className="ml-2 text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full hover:bg-blue-700 transition-colors"
            >
              Upgrade
            </button>
          )}
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={handleNotificationClick}
            className="relative p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-white">Notifications</h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {mockNotifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={cn(
                      'p-4 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700',
                      !notification.read && 'bg-blue-50 dark:bg-blue-900/20'
                    )}
                  >
                    <div className="flex items-start space-x-3">
                      <div className={cn(
                        'w-2 h-2 rounded-full mt-2',
                        notification.type === 'upgrade' && 'bg-orange-500',
                        notification.type === 'success' && 'bg-green-500',
                        notification.type === 'warning' && 'bg-yellow-500',
                        notification.type === 'info' && 'bg-blue-500'
                      )} />
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">
                          {notification.title}
                        </h4>
                        <p className="text-gray-600 dark:text-gray-300 text-sm mt-1">
                          {notification.message}
                        </p>
                        <p className="text-gray-400 text-xs mt-2">
                          {notification.timestamp}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <button className="text-blue-600 hover:text-blue-700 text-sm font-medium">
                  View all notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {user?.full_name?.charAt(0) || 'U'}
              </span>
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {user?.full_name || 'User'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {user?.email}
              </p>
            </div>
            <ChevronDown className="h-4 w-4 text-gray-500" />
          </button>

          {/* User Dropdown */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50">
              <div className="p-2">
                <button
                  onClick={handleUpgradeClick}
                  className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
                >
                  Upgrade Plan
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md">
                  Settings
                </button>
                <button className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md">
                  Support
                </button>
                <hr className="my-2 border-gray-200 dark:border-gray-700" />
                <button className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md">
                  Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
