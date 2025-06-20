/**
 * Login Form Component
 * 
 * Secure login form with MFA support, device fingerprinting,
 * and Zero Trust integration for WebAgent enterprise platform.
 */

import React, { useState } from 'react';
import { Eye, EyeOff, Shield, Lock, Mail, AlertCircle, CheckCircle } from 'lucide-react';
import { apiService, type LoginCredentials } from '../../services';
import { cn, isValidEmail } from '../../lib/utils';
import { DemoLoginPanel } from './DemoLoginPanel';

interface LoginFormProps {
  onSuccess: () => void;
  onError: (error: string) => void;
  className?: string;
}

interface FormData {
  email: string;
  password: string;
  mfa_code: string;
  remember_me: boolean;
}

interface FormErrors {
  email?: string;
  password?: string;
  mfa_code?: string;
  general?: string;
}

export function LoginForm({ onSuccess, onError, className }: LoginFormProps) {
  const [formData, setFormData] = useState<FormData>({
    email: '',
    password: '',
    mfa_code: '',
    remember_me: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [requiresMFA, setRequiresMFA] = useState(false);
  const [trustAssessment, setTrustAssessment] = useState<any>(null);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!isValidEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    if (requiresMFA && !formData.mfa_code) {
      newErrors.mfa_code = 'MFA code is required';
    } else if (requiresMFA && formData.mfa_code.length !== 6) {
      newErrors.mfa_code = 'MFA code must be 6 digits';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleDemoLogin = async (email: string, password: string) => {
    setFormData(prev => ({ ...prev, email, password }));
    setIsLoading(true);
    setErrors({});

    try {
      const credentials: LoginCredentials = { email, password };
      const response = await apiService.login(credentials);

      // Get Zero Trust assessment after successful login
      try {
        const assessment = await apiService.getTrustAssessment();
        setTrustAssessment(assessment);
      } catch (assessmentError) {
        console.warn('Trust assessment failed:', assessmentError);
      }

      onSuccess();
    } catch (error: any) {
      console.error('Demo login failed:', error);
      setErrors({ general: error.message || 'Demo login failed' });
      onError(error.message || 'Demo login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});

    try {
      const credentials: LoginCredentials = {
        email: formData.email,
        password: formData.password,
      };

      if (requiresMFA && formData.mfa_code) {
        credentials.mfa_code = formData.mfa_code;
      }

      const response = await apiService.login(credentials);
      
      // Get Zero Trust assessment after successful login
      try {
        const assessment = await apiService.getTrustAssessment();
        setTrustAssessment(assessment);
        
        // Check if additional verification is required
        if (assessment.required_actions?.length > 0) {
          // Handle required actions (e.g., device verification, location confirmation)
          console.log('Required actions:', assessment.required_actions);
        }
      } catch (assessmentError) {
        console.warn('Trust assessment failed:', assessmentError);
      }

      onSuccess();
    } catch (error: any) {
      console.error('Login failed:', error);
      
      if (error.code === 'MFA_REQUIRED') {
        setRequiresMFA(true);
        setErrors({ general: 'Please enter your MFA code to continue' });
      } else if (error.code === 'INVALID_MFA') {
        setErrors({ mfa_code: 'Invalid MFA code. Please try again.' });
      } else if (error.code === 'ACCOUNT_LOCKED') {
        setErrors({ general: 'Account temporarily locked due to security concerns. Please contact support.' });
      } else {
        setErrors({ general: error.message || 'Login failed. Please check your credentials.' });
      }
      
      onError(error.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: keyof FormData) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear field-specific errors when user starts typing
    if (errors[field as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  return (
    <div className={cn('w-full max-w-md mx-auto', className)}>
      <div className="card">
        <div className="card-header text-center">
          <div className="flex items-center justify-center mb-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-8 w-8 text-primary-600" />
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                WebAgent
              </span>
            </div>
          </div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            Sign in to your account
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Secure access with Zero Trust verification
          </p>
        </div>

        <div className="card-body">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Email address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={formData.email}
                  onChange={handleInputChange('email')}
                  className={cn(
                    'block w-full pl-10 pr-3 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.email
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="Enter your email"
                  disabled={isLoading}
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={formData.password}
                  onChange={handleInputChange('password')}
                  className={cn(
                    'block w-full pl-10 pr-10 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.password
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="Enter your password"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.password}
                </p>
              )}
            </div>

            {/* MFA Code Field (shown when required) */}
            {requiresMFA && (
              <div>
                <label htmlFor="mfa_code" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  MFA Code
                </label>
                <input
                  id="mfa_code"
                  type="text"
                  maxLength={6}
                  value={formData.mfa_code}
                  onChange={handleInputChange('mfa_code')}
                  className={cn(
                    'block w-full px-3 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-center text-lg tracking-widest',
                    errors.mfa_code
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="000000"
                  disabled={isLoading}
                />
                {errors.mfa_code && (
                  <p className="mt-1 text-sm text-red-600 flex items-center">
                    <AlertCircle className="h-4 w-4 mr-1" />
                    {errors.mfa_code}
                  </p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  Enter the 6-digit code from your authenticator app
                </p>
              </div>
            )}

            {/* Remember Me */}
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  id="remember_me"
                  type="checkbox"
                  checked={formData.remember_me}
                  onChange={handleInputChange('remember_me')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  disabled={isLoading}
                />
                <label htmlFor="remember_me" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  Remember me
                </label>
              </div>
              <a
                href="/forgot-password"
                className="text-sm text-primary-600 hover:text-primary-500 dark:text-primary-400"
              >
                Forgot password?
              </a>
            </div>

            {/* General Error */}
            {errors.general && (
              <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-4">
                <div className="flex">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                  <div className="ml-3">
                    <p className="text-sm text-red-800 dark:text-red-400">
                      {errors.general}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Trust Assessment Display */}
            {trustAssessment && (
              <div className="rounded-md bg-blue-50 dark:bg-blue-900/20 p-4">
                <div className="flex">
                  <CheckCircle className="h-5 w-5 text-blue-400" />
                  <div className="ml-3">
                    <p className="text-sm text-blue-800 dark:text-blue-400">
                      Trust Score: {Math.round(trustAssessment.trust_score * 100)}% 
                      ({trustAssessment.trust_level.replace('_', ' ')})
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className={cn(
                'w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white',
                'bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-colors duration-200'
              )}
            >
              {isLoading ? (
                <div className="flex items-center">
                  <div className="loading-spinner mr-2" />
                  Signing in...
                </div>
              ) : (
                'Sign in'
              )}
            </button>
          </form>
        </div>

        <div className="card-footer text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Don't have an account?{' '}
            <a href="/register" className="text-primary-600 hover:text-primary-500 dark:text-primary-400 font-medium">
              Sign up
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
