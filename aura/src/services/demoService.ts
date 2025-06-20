/**
 * Demo Service for WebAgent Aura
 * 
 * Provides demo authentication and mock data for development and testing.
 * This service simulates the backend API responses for demonstration purposes.
 */

import { cryptoService } from './cryptoService';

// Demo Users Database
export const DEMO_USERS = [
  {
    id: 1,
    email: 'admin@webagent.com',
    password: 'admin123',
    full_name: 'System Administrator',
    security_role: 'SYSTEM_ADMIN',
    trust_score: 0.95,
    mfa_enabled: true,
    tenant_id: 'webagent-corp',
    is_active: true,
    is_verified: true,
    last_login: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
    created_at: '2024-01-01T00:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    email: 'manager@acme.com',
    password: 'manager123',
    full_name: 'John Manager',
    security_role: 'AUTOMATION_MANAGER',
    trust_score: 0.87,
    mfa_enabled: true,
    tenant_id: 'acme-corp',
    is_active: true,
    is_verified: true,
    last_login: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
    created_at: '2024-02-15T00:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 3,
    email: 'analyst@security.com',
    password: 'analyst123',
    full_name: 'Sarah Security',
    security_role: 'ANALYST',
    trust_score: 0.92,
    mfa_enabled: false,
    tenant_id: 'security-corp',
    is_active: true,
    is_verified: true,
    last_login: new Date(Date.now() - 10 * 60 * 1000).toISOString(), // 10 minutes ago
    created_at: '2024-03-01T00:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 4,
    email: 'user@startup.com',
    password: 'user123',
    full_name: 'Mike User',
    security_role: 'END_USER',
    trust_score: 0.78,
    mfa_enabled: false,
    tenant_id: 'startup-inc',
    is_active: true,
    is_verified: true,
    last_login: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
    created_at: '2024-04-10T00:00:00Z',
    updated_at: new Date().toISOString(),
  },
  {
    id: 5,
    email: 'auditor@compliance.com',
    password: 'auditor123',
    full_name: 'Emma Auditor',
    security_role: 'AUDITOR',
    trust_score: 0.89,
    mfa_enabled: true,
    tenant_id: 'compliance-corp',
    is_active: true,
    is_verified: true,
    last_login: new Date(Date.now() - 60 * 60 * 1000).toISOString(), // 1 hour ago
    created_at: '2024-05-01T00:00:00Z',
    updated_at: new Date().toISOString(),
  },
];

// Demo Trust Assessment Data
const generateTrustAssessment = (user: any) => ({
  assessment_id: `demo-${user.id}-${Date.now()}`,
  user_id: user.id,
  timestamp: new Date().toISOString(),
  trust_score: user.trust_score,
  trust_level: user.trust_score >= 0.9 ? 'very_high' : 
               user.trust_score >= 0.8 ? 'high' :
               user.trust_score >= 0.6 ? 'medium' :
               user.trust_score >= 0.4 ? 'low' : 'very_low',
  risk_score: 1 - user.trust_score,
  confidence_score: 0.95,
  trust_factors: {
    authentication_strength: user.mfa_enabled ? 0.95 : 0.75,
    device_trust_score: 0.88,
    location_trust_score: 0.92,
    behavioral_trust_score: user.trust_score,
    network_trust_score: 0.85,
  },
  risk_factors: user.trust_score < 0.8 ? ['unusual_login_time', 'new_device'] : [],
  required_actions: user.trust_score < 0.7 ? ['verify_device', 'enable_mfa'] : [],
  session_restrictions: {
    max_session_duration: user.trust_score >= 0.9 ? 480 : 240, // minutes
    require_reauth_for_sensitive: user.trust_score < 0.8,
    allow_concurrent_sessions: user.trust_score >= 0.8,
  },
  next_verification_in: user.trust_score >= 0.9 ? 3600 : 1800, // seconds
});

class DemoService {
  private currentUser: any = null;
  private isDemo = import.meta.env.VITE_DEV_MODE === 'true';

  // Check if demo mode is enabled
  isDemoMode(): boolean {
    return this.isDemo;
  }

  // Demo login
  async demoLogin(email: string, password: string): Promise<any> {
    if (!this.isDemo) {
      throw new Error('Demo mode is not enabled');
    }

    // Find user by email
    const user = DEMO_USERS.find(u => u.email === email);
    if (!user) {
      throw new Error('Invalid email or password');
    }

    // Check password
    if (user.password !== password) {
      throw new Error('Invalid email or password');
    }

    // Generate demo tokens
    const accessToken = await this.generateDemoToken(user);
    const refreshToken = await this.generateDemoToken(user, 'refresh');

    // Update last login
    user.last_login = new Date().toISOString();
    this.currentUser = user;

    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'Bearer',
      expires_in: 3600,
      user: {
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        is_active: user.is_active,
        is_verified: user.is_verified,
        tenant_id: user.tenant_id,
        security_role: user.security_role,
        trust_score: user.trust_score,
        mfa_enabled: user.mfa_enabled,
        last_login: user.last_login,
      },
    };
  }

  // Demo registration
  async demoRegister(data: any): Promise<any> {
    if (!this.isDemo) {
      throw new Error('Demo mode is not enabled');
    }

    // Check if email already exists
    const existingUser = DEMO_USERS.find(u => u.email === data.email);
    if (existingUser) {
      throw new Error('Email already exists');
    }

    // Create new demo user
    const newUser = {
      id: DEMO_USERS.length + 1,
      email: data.email,
      password: data.password,
      full_name: data.full_name,
      security_role: 'END_USER',
      trust_score: 0.75,
      mfa_enabled: false,
      tenant_id: data.tenant_id || 'demo-tenant',
      is_active: true,
      is_verified: false,
      last_login: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Add to demo users (in memory only)
    DEMO_USERS.push(newUser);

    // Generate demo tokens
    const accessToken = await this.generateDemoToken(newUser);
    const refreshToken = await this.generateDemoToken(newUser, 'refresh');

    this.currentUser = newUser;

    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'Bearer',
      expires_in: 3600,
      user: {
        id: newUser.id,
        email: newUser.email,
        full_name: newUser.full_name,
        is_active: newUser.is_active,
        is_verified: newUser.is_verified,
        tenant_id: newUser.tenant_id,
        security_role: newUser.security_role,
        trust_score: newUser.trust_score,
        mfa_enabled: newUser.mfa_enabled,
        last_login: newUser.last_login,
      },
    };
  }

  // Demo trust assessment
  async getDemoTrustAssessment(): Promise<any> {
    if (!this.isDemo || !this.currentUser) {
      throw new Error('Demo mode not enabled or user not logged in');
    }

    return generateTrustAssessment(this.currentUser);
  }

  // Generate demo JWT token
  private async generateDemoToken(user: any, type: string = 'access'): Promise<string> {
    const header = {
      alg: 'HS256',
      typ: 'JWT',
    };

    const payload = {
      sub: user.id.toString(),
      email: user.email,
      role: user.security_role,
      tenant_id: user.tenant_id,
      type: type,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + (type === 'refresh' ? 7 * 24 * 3600 : 3600),
    };

    // Simple base64 encoding for demo purposes (not secure for production)
    const encodedHeader = btoa(JSON.stringify(header));
    const encodedPayload = btoa(JSON.stringify(payload));
    const signature = await cryptoService.hash(`${encodedHeader}.${encodedPayload}.demo-secret`);

    return `${encodedHeader}.${encodedPayload}.${signature.substring(0, 32)}`;
  }

  // Get current demo user
  getCurrentUser(): any {
    return this.currentUser;
  }

  // Demo logout
  demoLogout(): void {
    this.currentUser = null;
  }

  // Get all demo users (for admin)
  getDemoUsers(): any[] {
    return DEMO_USERS.map(user => ({
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      security_role: user.security_role,
      trust_score: user.trust_score,
      mfa_enabled: user.mfa_enabled,
      tenant_id: user.tenant_id,
      is_active: user.is_active,
      is_verified: user.is_verified,
      last_login: user.last_login,
      created_at: user.created_at,
      updated_at: user.updated_at,
    }));
  }
}

// Export singleton instance
export const demoService = new DemoService();
export default demoService;
