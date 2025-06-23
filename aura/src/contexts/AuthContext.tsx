/**
 * Authentication Context
 *
 * Provides authentication state management, user data, and security
 * context throughout the WebAgent Aura application.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { apiService, cryptoService, type User } from "../services";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  trustScore: number | null;
  login: (email: string, password: string, mfaCode?: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateTrustScore: () => Promise<void>;
}

interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  tenant_id?: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [trustScore, setTrustScore] = useState<number | null>(null);

  const isAuthenticated = !!user && apiService.isAuthenticated();

  // Initialize authentication state
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      if (apiService.isAuthenticated()) {
        const userData = apiService.getUserData();
        if (userData) {
          setUser(userData);

          // Load private keys if available
          await cryptoService.loadPrivateKeys();

          // Get initial trust assessment
          await updateTrustScore();
        }
      }
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.warn("Failed to initialize auth:", error);
      }
      // Clear invalid auth state
      apiService.logout();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string, mfaCode?: string) => {
    try {
      const response = await apiService.login({
        email,
        password,
        mfa_code: mfaCode,
      });

      setUser(response.user);

      // Load private keys
      await cryptoService.loadPrivateKeys();

      // Get trust assessment
      await updateTrustScore();
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.warn("Login failed:", error);
      }
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    try {
      const response = await apiService.register(data);
      setUser(response.user);

      // Keys are already stored during registration
      await updateTrustScore();
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.warn("Registration failed:", error);
      }
      throw error;
    }
  };

  const logout = () => {
    apiService.logout();
    setUser(null);
    setTrustScore(null);
  };

  const refreshUser = async () => {
    try {
      if (!isAuthenticated) return;

      // Fetch updated user data
      const userData = await apiService.get<User>("/users/me");
      setUser(userData);
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.warn("Failed to refresh user:", error);
      }
      // If refresh fails due to auth, logout
      if (error.code === "UNAUTHORIZED") {
        logout();
      }
    }
  };

  const updateTrustScore = async () => {
    try {
      if (!isAuthenticated) return;

      const assessment = await apiService.getTrustAssessment();
      setTrustScore(assessment.trust_score);

      // Update user's trust score if it's different
      if (user && user.trust_score !== assessment.trust_score) {
        setUser((prev) =>
          prev ? { ...prev, trust_score: assessment.trust_score } : null,
        );
      }
    } catch (error) {
      if (process.env.NODE_ENV === "development") {
        console.warn("Failed to update trust score:", error);
      }
    }
  };

  // Periodic trust score updates
  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(
      () => {
        updateTrustScore();
      },
      5 * 60 * 1000,
    ); // Update every 5 minutes

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    trustScore,
    login,
    register,
    logout,
    refreshUser,
    updateTrustScore,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Higher-order component for protected routes
export function withAuth<P extends object>(Component: React.ComponentType<P>) {
  return function AuthenticatedComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth();

    if (isLoading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="loading-spinner mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Loading...</p>
          </div>
        </div>
      );
    }

    if (!isAuthenticated) {
      // Redirect to login or show login form
      window.location.href = "/login";
      return null;
    }

    return <Component {...props} />;
  };
}

// Hook for role-based access control
export function usePermissions() {
  const { user } = useAuth();

  const hasRole = (role: string): boolean => {
    return user?.security_role === role;
  };

  const hasAnyRole = (roles: string[]): boolean => {
    return roles.some((role) => hasRole(role));
  };

  const isAdmin = (): boolean => {
    return hasAnyRole(["SYSTEM_ADMIN", "TENANT_ADMIN"]);
  };

  const canManageUsers = (): boolean => {
    return hasAnyRole(["SYSTEM_ADMIN", "TENANT_ADMIN"]);
  };

  const canViewAuditLogs = (): boolean => {
    return hasAnyRole(["SYSTEM_ADMIN", "TENANT_ADMIN", "AUDITOR"]);
  };

  const canManageAutomation = (): boolean => {
    return hasAnyRole(["SYSTEM_ADMIN", "TENANT_ADMIN", "AUTOMATION_MANAGER"]);
  };

  return {
    user,
    hasRole,
    hasAnyRole,
    isAdmin,
    canManageUsers,
    canViewAuditLogs,
    canManageAutomation,
  };
}
