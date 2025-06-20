/**
 * API Service for WebAgent Aura Frontend
 * 
 * Handles JWT authentication, secure API communication, and integration
 * with WebAgent's enterprise security backend.
 */

import axios from 'axios';
import { cryptoService } from './cryptoService';
import { demoService } from './demoService';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const API_TIMEOUT = 30000; // 30 seconds

// Token storage keys
const ACCESS_TOKEN_KEY = 'webagent_access_token';
const REFRESH_TOKEN_KEY = 'webagent_refresh_token';
const USER_DATA_KEY = 'webagent_user_data';

// Types
export interface LoginCredentials {
  email: string;
  password: string;
  mfa_code?: string;
  device_fingerprint?: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  tenant_id?: string;
  encryption_public_key?: string;
  signing_public_key?: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  tenant_id?: string;
  security_role: string;
  trust_score: number;
  mfa_enabled: boolean;
  last_login?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
}

class ApiService {
  private axiosInstance: any;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (error?: any) => void;
  }> = [];

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Version': '1.0.0',
        'X-Client-Platform': 'web',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor - Add auth token and security headers
    this.axiosInstance.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Add security headers
        config.headers['X-Requested-With'] = 'XMLHttpRequest';
        config.headers['X-Client-Timestamp'] = Date.now().toString();
        
        // Add device fingerprint if available
        const deviceFingerprint = this.getDeviceFingerprint();
        if (deviceFingerprint) {
          config.headers['X-Device-Fingerprint'] = deviceFingerprint;
        }

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - Handle token refresh and errors
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.axiosInstance(originalRequest);
            }).catch((err) => {
              return Promise.reject(err);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const newToken = await this.refreshToken();
            this.processQueue(null, newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.axiosInstance(originalRequest);
          } catch (refreshError) {
            this.processQueue(refreshError, null);
            this.logout();
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private processQueue(error: any, token: string | null): void {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  private handleApiError(error: any): ApiError {
    if (error.response) {
      // Server responded with error status
      return {
        message: error.response.data?.detail || error.response.data?.message || 'Server error',
        code: error.response.data?.code,
        details: error.response.data,
      };
    } else if (error.request) {
      // Network error
      return {
        message: 'Network error - please check your connection',
        code: 'NETWORK_ERROR',
      };
    } else {
      // Other error
      return {
        message: error.message || 'An unexpected error occurred',
        code: 'UNKNOWN_ERROR',
      };
    }
  }

  // Authentication Methods
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      // Check if demo mode is enabled
      if (demoService.isDemoMode()) {
        console.log('🎭 Demo Mode: Using demo authentication');
        const authData = await demoService.demoLogin(credentials.email, credentials.password);
        this.setTokens(authData.access_token, authData.refresh_token);
        this.setUserData(authData.user);
        return authData;
      }

      // Production login
      const deviceFingerprint = await this.generateDeviceFingerprint();

      const response = await this.axiosInstance.post<AuthResponse>('/auth/login', {
        ...credentials,
        device_fingerprint: deviceFingerprint,
      });

      const authData = response.data;
      this.setTokens(authData.access_token, authData.refresh_token);
      this.setUserData(authData.user);

      return authData;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      // Check if demo mode is enabled
      if (demoService.isDemoMode()) {
        console.log('🎭 Demo Mode: Using demo registration');
        const authData = await demoService.demoRegister(data);
        this.setTokens(authData.access_token, authData.refresh_token);
        this.setUserData(authData.user);

        // Generate and store demo keys
        const keyPair = await cryptoService.generateKeyPair();
        await cryptoService.storePrivateKeys(keyPair.privateKey, keyPair.signingPrivateKey);

        return authData;
      }

      // Production registration
      const keyPair = await cryptoService.generateKeyPair();

      const response = await this.axiosInstance.post<AuthResponse>('/auth/register', {
        ...data,
        encryption_public_key: keyPair.publicKey,
        signing_public_key: keyPair.signingPublicKey,
      });

      const authData = response.data;
      this.setTokens(authData.access_token, authData.refresh_token);
      this.setUserData(authData.user);

      // Store private keys securely
      await cryptoService.storePrivateKeys(keyPair.privateKey, keyPair.signingPrivateKey);

      return authData;
    } catch (error) {
      throw this.handleApiError(error);
    }
  }

  async refreshToken(): Promise<string> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await this.axiosInstance.post<AuthResponse>('/auth/refresh', {
        refresh_token: refreshToken,
      });

      const authData = response.data;
      this.setTokens(authData.access_token, authData.refresh_token);
      
      return authData.access_token;
    } catch (error) {
      this.logout();
      throw this.handleApiError(error);
    }
  }

  logout(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_DATA_KEY);
    cryptoService.clearKeys();

    // Demo mode cleanup
    if (demoService.isDemoMode()) {
      demoService.demoLogout();
    }
  }

  // Token Management
  private setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }

  private getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  private setUserData(user: User): void {
    localStorage.setItem(USER_DATA_KEY, JSON.stringify(user));
  }

  getUserData(): User | null {
    const userData = localStorage.getItem(USER_DATA_KEY);
    return userData ? JSON.parse(userData) : null;
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  // Device Fingerprinting
  private async generateDeviceFingerprint(): Promise<string> {
    const fingerprint = {
      userAgent: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      screenResolution: `${screen.width}x${screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      timestamp: Date.now(),
    };

    const fingerprintString = JSON.stringify(fingerprint);
    return await cryptoService.hash(fingerprintString);
  }

  private getDeviceFingerprint(): string | null {
    // This would be stored after first generation
    return localStorage.getItem('device_fingerprint');
  }

  // Generic API Methods
  async get<T>(url: string, config?: any): Promise<T> {
    const response = await this.axiosInstance.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.axiosInstance.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: any): Promise<T> {
    const response = await this.axiosInstance.put<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: any): Promise<T> {
    const response = await this.axiosInstance.delete<T>(url, config);
    return response.data;
  }

  // Zero Trust Security Methods
  async getTrustAssessment(): Promise<any> {
    // Check if demo mode is enabled
    if (demoService.isDemoMode()) {
      console.log('🎭 Demo Mode: Using demo trust assessment');
      return await demoService.getDemoTrustAssessment();
    }

    // Production trust assessment
    return this.post('/security/zero-trust/assess', {
      timestamp: new Date().toISOString(),
      source_ip: await this.getClientIP(),
      user_agent: navigator.userAgent,
      device_fingerprint: await this.generateDeviceFingerprint(),
    });
  }

  private async getClientIP(): Promise<string> {
    try {
      const response = await fetch('https://api.ipify.org?format=json');
      const data = await response.json();
      return data.ip;
    } catch {
      return 'unknown';
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
