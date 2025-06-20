/**
 * Registration Form Component
 * 
 * Secure registration form with password strength validation,
 * client-side key generation, and enterprise tenant support.
 */

import React, { useState } from 'react';
import { Eye, EyeOff, Shield, Lock, Mail, User, AlertCircle, CheckCircle, Building } from 'lucide-react';
import { apiService, cryptoService, type RegisterData } from '../../services';
import { cn, isValidEmail, getPasswordStrength } from '../../lib/utils';

interface RegisterFormProps {
  onSuccess: () => void;
  onError: (error: string) => void;
  className?: string;
}

interface FormData {
  email: string;
  password: string;
  confirmPassword: string;
  full_name: string;
  tenant_id: string;
  agree_terms: boolean;
  agree_privacy: boolean;
}

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  full_name?: string;
  tenant_id?: string;
  terms?: string;
  general?: string;
}

export function RegisterForm({ onSuccess, onError, className }: RegisterFormProps) {
  const [formData, setFormData] = useState<FormData>({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    tenant_id: '',
    agree_terms: false,
    agree_privacy: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [keyGenerationProgress, setKeyGenerationProgress] = useState(0);

  const passwordStrength = getPasswordStrength(formData.password);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!formData.full_name.trim()) {
      newErrors.full_name = 'Full name is required';
    } else if (formData.full_name.trim().length < 2) {
      newErrors.full_name = 'Full name must be at least 2 characters';
    }

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!isValidEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (passwordStrength.score < 4) {
      newErrors.password = 'Password is too weak. Please use a stronger password.';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (!formData.agree_terms || !formData.agree_privacy) {
      newErrors.terms = 'You must agree to the terms and privacy policy';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);
    setErrors({});
    setKeyGenerationProgress(0);

    try {
      // Step 1: Generate client-side encryption keys
      setKeyGenerationProgress(25);
      if (!cryptoService.isSupported()) {
        throw new Error('Your browser does not support the required cryptographic features');
      }

      setKeyGenerationProgress(50);
      const keyPair = await cryptoService.generateKeyPair();
      
      setKeyGenerationProgress(75);

      // Step 2: Register with the backend
      const registerData: RegisterData = {
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name.trim(),
        tenant_id: formData.tenant_id || undefined,
        encryption_public_key: keyPair.publicKey,
        signing_public_key: keyPair.signingPublicKey,
      };

      const response = await apiService.register(registerData);
      
      setKeyGenerationProgress(100);

      // Step 3: Store private keys securely
      await cryptoService.storePrivateKeys(keyPair.privateKey, keyPair.signingPrivateKey);

      onSuccess();
    } catch (error: any) {
      console.error('Registration failed:', error);
      
      if (error.code === 'EMAIL_EXISTS') {
        setErrors({ email: 'An account with this email already exists' });
      } else if (error.code === 'WEAK_PASSWORD') {
        setErrors({ password: 'Password does not meet security requirements' });
      } else if (error.code === 'INVALID_TENANT') {
        setErrors({ tenant_id: 'Invalid tenant ID' });
      } else {
        setErrors({ general: error.message || 'Registration failed. Please try again.' });
      }
      
      onError(error.message || 'Registration failed');
    } finally {
      setIsLoading(false);
      setKeyGenerationProgress(0);
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
            Create your account
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            Join the secure automation platform
          </p>
        </div>

        <div className="card-body">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Full Name Field */}
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="full_name"
                  type="text"
                  autoComplete="name"
                  required
                  value={formData.full_name}
                  onChange={handleInputChange('full_name')}
                  className={cn(
                    'block w-full pl-10 pr-3 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.full_name
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="Enter your full name"
                  disabled={isLoading}
                />
              </div>
              {errors.full_name && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.full_name}
                </p>
              )}
            </div>

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

            {/* Tenant ID Field (Optional) */}
            <div>
              <label htmlFor="tenant_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Organization ID <span className="text-gray-500">(Optional)</span>
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Building className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="tenant_id"
                  type="text"
                  value={formData.tenant_id}
                  onChange={handleInputChange('tenant_id')}
                  className={cn(
                    'block w-full pl-10 pr-3 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.tenant_id
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="Enter organization ID"
                  disabled={isLoading}
                />
              </div>
              {errors.tenant_id && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.tenant_id}
                </p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Leave blank to create a personal account
              </p>
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
                  autoComplete="new-password"
                  required
                  value={formData.password}
                  onChange={handleInputChange('password')}
                  className={cn(
                    'block w-full pl-10 pr-10 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.password
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="Create a strong password"
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
              
              {/* Password Strength Indicator */}
              {formData.password && (
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-500">Password strength:</span>
                    <span className={cn(
                      'font-medium',
                      passwordStrength.score <= 2 ? 'text-red-600' :
                      passwordStrength.score <= 4 ? 'text-yellow-600' : 'text-green-600'
                    )}>
                      {passwordStrength.label}
                    </span>
                  </div>
                  <div className="mt-1 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={cn('h-2 rounded-full transition-all duration-300', passwordStrength.color)}
                      style={{ width: `${(passwordStrength.score / 6) * 100}%` }}
                    />
                  </div>
                </div>
              )}
              
              {errors.password && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.password}
                </p>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  value={formData.confirmPassword}
                  onChange={handleInputChange('confirmPassword')}
                  className={cn(
                    'block w-full pl-10 pr-10 py-2 border rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                    errors.confirmPassword
                      ? 'border-red-300 text-red-900 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white'
                  )}
                  placeholder="Confirm your password"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  disabled={isLoading}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                  )}
                </button>
              </div>
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.confirmPassword}
                </p>
              )}
            </div>

            {/* Terms and Privacy */}
            <div className="space-y-3">
              <div className="flex items-start">
                <input
                  id="agree_terms"
                  type="checkbox"
                  checked={formData.agree_terms}
                  onChange={handleInputChange('agree_terms')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded mt-0.5"
                  disabled={isLoading}
                />
                <label htmlFor="agree_terms" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  I agree to the{' '}
                  <a href="/terms" className="text-primary-600 hover:text-primary-500 dark:text-primary-400">
                    Terms of Service
                  </a>
                </label>
              </div>
              <div className="flex items-start">
                <input
                  id="agree_privacy"
                  type="checkbox"
                  checked={formData.agree_privacy}
                  onChange={handleInputChange('agree_privacy')}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded mt-0.5"
                  disabled={isLoading}
                />
                <label htmlFor="agree_privacy" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                  I agree to the{' '}
                  <a href="/privacy" className="text-primary-600 hover:text-primary-500 dark:text-primary-400">
                    Privacy Policy
                  </a>
                </label>
              </div>
              {errors.terms && (
                <p className="text-sm text-red-600 flex items-center">
                  <AlertCircle className="h-4 w-4 mr-1" />
                  {errors.terms}
                </p>
              )}
            </div>

            {/* Key Generation Progress */}
            {keyGenerationProgress > 0 && (
              <div className="rounded-md bg-blue-50 dark:bg-blue-900/20 p-4">
                <div className="flex items-center">
                  <Shield className="h-5 w-5 text-blue-400 mr-2" />
                  <div className="flex-1">
                    <p className="text-sm text-blue-800 dark:text-blue-400 mb-2">
                      Generating encryption keys... {keyGenerationProgress}%
                    </p>
                    <div className="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${keyGenerationProgress}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

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

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !formData.agree_terms || !formData.agree_privacy}
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
                  Creating account...
                </div>
              ) : (
                'Create account'
              )}
            </button>
          </form>
        </div>

        <div className="card-footer text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Already have an account?{' '}
            <a href="/login" className="text-primary-600 hover:text-primary-500 dark:text-primary-400 font-medium">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
