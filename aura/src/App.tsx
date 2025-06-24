/**
 * WebAgent Aura - Main Application Component
 *
 * Secure frontend application for WebAgent enterprise automation platform.
 * Features Zero Trust security, enterprise authentication, and comprehensive
 * security monitoring.
 */

// React imports handled by JSX transform
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LoginForm } from "./components/auth/LoginForm";
import { RegisterForm } from "./components/auth/RegisterForm";
import { UnifiedDashboard } from "./components/UnifiedDashboard";
import { Shield } from "lucide-react";

// Main App Layout Component
function AppLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="flex items-center justify-center mb-4">
            <Shield className="h-12 w-12 text-primary-600 animate-pulse" />
          </div>
          <div className="loading-spinner mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            Loading WebAgent...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    );
  }

  // Use the UnifiedDashboard which has its own complete layout
  return (
    <Routes>
      <Route path="*" element={<UnifiedDashboard />} />
    </Routes>
  );
}

// Login Page Component
function LoginPage() {
  const handleSuccess = () => {
    // Navigation will be handled by the auth context
    window.location.href = "/dashboard";
  };

  const handleError = (error: string) => {
    console.error("Login error:", error);
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <LoginForm onSuccess={handleSuccess} onError={handleError} />
    </div>
  );
}

// Register Page Component
function RegisterPage() {
  const handleSuccess = () => {
    // Navigation will be handled by the auth context
    window.location.href = "/dashboard";
  };

  const handleError = (error: string) => {
    console.error("Registration error:", error);
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <RegisterForm onSuccess={handleSuccess} onError={handleError} />
    </div>
  );
}

// Main App Component with Providers
function App() {
  return (
    <Router>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </Router>
  );
}

export default App;
