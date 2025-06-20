/**
 * Demo Login Panel Component
 * 
 * Provides quick access to demo test users for development and testing.
 * Only shown when VITE_DEV_MODE is enabled.
 */

import React from 'react';
import { User, Shield, Crown, Eye, Settings, Users } from 'lucide-react';
import { DEMO_USERS } from '../../services/demoService';
import { cn } from '../../lib/utils';

interface DemoLoginPanelProps {
  onDemoLogin: (email: string, password: string) => void;
  isLoading?: boolean;
  className?: string;
}

const roleIcons = {
  SYSTEM_ADMIN: Crown,
  TENANT_ADMIN: Settings,
  AUTOMATION_MANAGER: Users,
  ANALYST: Eye,
  AUDITOR: Shield,
  END_USER: User,
};

const roleColors = {
  SYSTEM_ADMIN: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
  TENANT_ADMIN: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
  AUTOMATION_MANAGER: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
  ANALYST: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400',
  AUDITOR: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
  END_USER: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400',
};

export function DemoLoginPanel({ onDemoLogin, isLoading = false, className }: DemoLoginPanelProps) {
  // Only show in development mode
  if (import.meta.env.VITE_DEV_MODE !== 'true') {
    return null;
  }

  const handleDemoLogin = (user: any) => {
    if (isLoading) return;
    onDemoLogin(user.email, user.password);
  };

  return (
    <div className={cn('w-full max-w-md mx-auto mt-8', className)}>
      <div className="card">
        <div className="card-header text-center">
          <div className="flex items-center justify-center mb-2">
            <div className="flex items-center space-x-2">
              <div className="h-6 w-6 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                <span className="text-xs font-bold text-white">D</span>
              </div>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">
                Demo Mode
              </span>
            </div>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Quick login with test users
          </p>
        </div>

        <div className="card-body">
          <div className="space-y-3">
            {DEMO_USERS.map((user) => {
              const IconComponent = roleIcons[user.security_role as keyof typeof roleIcons];
              const roleColor = roleColors[user.security_role as keyof typeof roleColors];

              return (
                <button
                  key={user.id}
                  type="button"
                  onClick={() => handleDemoLogin(user)}
                  disabled={isLoading}
                  className={cn(
                    'w-full p-3 text-left border border-gray-200 dark:border-gray-700 rounded-lg transition-all duration-200',
                    'hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-600',
                    'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    isLoading && 'cursor-not-allowed'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="h-10 w-10 bg-primary-600 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-white">
                          {user.full_name.split(' ').map(n => n[0]).join('').toUpperCase()}
                        </span>
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {user.full_name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                          {user.email}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {/* Trust Score */}
                      <div className="text-right">
                        <div className="flex items-center space-x-1">
                          <div className={cn(
                            'w-2 h-2 rounded-full',
                            user.trust_score >= 0.9 ? 'bg-green-500' :
                            user.trust_score >= 0.8 ? 'bg-lime-500' :
                            user.trust_score >= 0.6 ? 'bg-yellow-500' :
                            user.trust_score >= 0.4 ? 'bg-orange-500' : 'bg-red-500'
                          )} />
                          <span className="text-xs text-gray-600 dark:text-gray-400">
                            {Math.round(user.trust_score * 100)}%
                          </span>
                        </div>
                        
                        {/* Role Badge */}
                        <div className="mt-1">
                          <span className={cn(
                            'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
                            roleColor
                          )}>
                            <IconComponent className="h-3 w-3 mr-1" />
                            {user.security_role.replace('_', ' ')}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Additional Info */}
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <div className="flex items-center space-x-3">
                      <span>Tenant: {user.tenant_id}</span>
                      {user.mfa_enabled && (
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                          MFA
                        </span>
                      )}
                    </div>
                    <span>
                      Last: {user.last_login ? new Date(user.last_login).toLocaleTimeString() : 'Never'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="card-footer">
          <div className="text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              💡 Click any user to login instantly
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Or use the form above with any email/password
            </p>
          </div>
        </div>
      </div>

      {/* Demo Info Panel */}
      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <div className="flex items-start space-x-2">
          <div className="flex-shrink-0">
            <div className="h-5 w-5 bg-blue-500 rounded-full flex items-center justify-center">
              <span className="text-xs font-bold text-white">i</span>
            </div>
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100">
              Demo Mode Active
            </h4>
            <div className="mt-1 text-xs text-blue-800 dark:text-blue-200 space-y-1">
              <p>• All data is simulated and stored in memory only</p>
              <p>• Zero Trust assessments use mock calculations</p>
              <p>• Encryption keys are generated but not persisted</p>
              <p>• Perfect for testing UI and user flows</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
