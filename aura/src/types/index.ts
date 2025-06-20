/**
 * Type Definitions for WebAgent Aura
 * 
 * Comprehensive type definitions for the WebAgent frontend application.
 */

// User and Authentication Types
export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  tenant_id?: string;
  security_role: SecurityRole;
  trust_score: number;
  mfa_enabled: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export enum SecurityRole {
  SYSTEM_ADMIN = 'SYSTEM_ADMIN',
  TENANT_ADMIN = 'TENANT_ADMIN',
  AUTOMATION_MANAGER = 'AUTOMATION_MANAGER',
  ANALYST = 'ANALYST',
  AUDITOR = 'AUDITOR',
  END_USER = 'END_USER',
}

export enum ThreatLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export enum TrustLevel {
  VERY_LOW = 'very_low',
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  VERY_HIGH = 'very_high',
}

// Zero Trust Types
export interface TrustAssessment {
  assessment_id: string;
  user_id: number;
  timestamp: string;
  trust_score: number;
  trust_level: TrustLevel;
  risk_score: number;
  confidence_score: number;
  trust_factors: TrustFactors;
  risk_factors: string[];
  required_actions: string[];
  session_restrictions: Record<string, any>;
  next_verification_in: number;
}

export interface TrustFactors {
  authentication_strength: number;
  device_trust_score: number;
  location_trust_score: number;
  behavioral_trust_score: number;
  network_trust_score: number;
}

export interface DeviceInfo {
  device_id: string;
  device_type: string;
  os_name: string;
  os_version: string;
  browser_name: string;
  browser_version: string;
  is_managed: boolean;
  is_encrypted: boolean;
  device_fingerprint: string;
}

// Enterprise and Tenant Types
export interface Tenant {
  id: number;
  tenant_id: string;
  name: string;
  display_name: string;
  domain: string;
  is_active: boolean;
  is_enterprise: boolean;
  compliance_level: ComplianceLevel;
  subscription_tier: string;
  max_users: number;
  max_concurrent_sessions: number;
  api_rate_limit: number;
  enforce_sso: boolean;
  require_mfa: boolean;
  session_timeout_minutes: number;
  data_region: string;
  encryption_required: boolean;
  audit_retention_days: number;
  admin_email: string;
  created_at: string;
  updated_at: string;
}

export enum ComplianceLevel {
  INTERNAL = 'internal',
  CONFIDENTIAL = 'confidential',
  RESTRICTED = 'restricted',
  TOP_SECRET = 'top_secret',
}

// Security Event Types
export interface SecurityEvent {
  event_id: string;
  event_type: string;
  severity: ThreatLevel;
  user_id?: number;
  source_ip: string;
  user_agent: string;
  description: string;
  threat_indicators: string[];
  mitigated: boolean;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface IncidentResponse {
  incident_id: string;
  incident_type: string;
  severity: ThreatLevel;
  affected_users: number[];
  affected_resources: string[];
  detected_at: string;
  response_initiated_at?: string;
  contained_at?: string;
  resolved_at?: string;
  root_cause?: string;
  lessons_learned?: string;
  notification_sent: boolean;
  customer_impact: boolean;
  regulatory_reporting_required: boolean;
}

// Task and Execution Types
export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  user_id: number;
  tenant_id?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  metadata?: Record<string, any>;
}

export enum TaskStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum TaskPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface ExecutionPlan {
  id: number;
  name: string;
  description: string;
  steps: ExecutionStep[];
  status: ExecutionStatus;
  user_id: number;
  tenant_id?: string;
  created_at: string;
  updated_at: string;
  executed_at?: string;
  completed_at?: string;
}

export interface ExecutionStep {
  id: string;
  name: string;
  type: StepType;
  parameters: Record<string, any>;
  order: number;
  status: StepStatus;
  result?: any;
  error?: string;
  duration_ms?: number;
}

export enum ExecutionStatus {
  DRAFT = 'draft',
  READY = 'ready',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum StepType {
  NAVIGATE = 'navigate',
  CLICK = 'click',
  TYPE = 'type',
  WAIT = 'wait',
  SCROLL = 'scroll',
  EXTRACT = 'extract',
  VALIDATE = 'validate',
}

export enum StepStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

// UI and Component Types
export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon?: string;
  badge?: string | number;
  children?: NavigationItem[];
  requiredRole?: SecurityRole;
  requiredPermission?: string;
}

export interface DashboardWidget {
  id: string;
  title: string;
  type: WidgetType;
  size: WidgetSize;
  data: any;
  refreshInterval?: number;
  lastUpdated?: string;
}

export enum WidgetType {
  METRIC = 'metric',
  CHART = 'chart',
  TABLE = 'table',
  LIST = 'list',
  STATUS = 'status',
  SECURITY = 'security',
}

export enum WidgetSize {
  SMALL = 'small',
  MEDIUM = 'medium',
  LARGE = 'large',
  FULL = 'full',
}

// API Response Types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
  timestamp: string;
}

export interface PaginatedResponse<T = any> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
  timestamp: string;
}

// Form and Validation Types
export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  placeholder?: string;
  validation?: ValidationRule[];
  options?: SelectOption[];
  disabled?: boolean;
  description?: string;
}

export enum FieldType {
  TEXT = 'text',
  EMAIL = 'email',
  PASSWORD = 'password',
  NUMBER = 'number',
  SELECT = 'select',
  CHECKBOX = 'checkbox',
  RADIO = 'radio',
  TEXTAREA = 'textarea',
  DATE = 'date',
  FILE = 'file',
}

export interface SelectOption {
  value: string | number;
  label: string;
  disabled?: boolean;
}

export interface ValidationRule {
  type: ValidationType;
  value?: any;
  message: string;
}

export enum ValidationType {
  REQUIRED = 'required',
  MIN_LENGTH = 'minLength',
  MAX_LENGTH = 'maxLength',
  PATTERN = 'pattern',
  EMAIL = 'email',
  CUSTOM = 'custom',
}

// Theme and Preferences Types
export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  notifications: NotificationPreferences;
  dashboard: DashboardPreferences;
  security: SecurityPreferences;
}

export interface NotificationPreferences {
  email: boolean;
  browser: boolean;
  security_alerts: boolean;
  task_updates: boolean;
  system_maintenance: boolean;
}

export interface DashboardPreferences {
  layout: 'grid' | 'list';
  widgets: string[];
  refresh_interval: number;
  show_welcome: boolean;
}

export interface SecurityPreferences {
  session_timeout_warning: boolean;
  require_mfa_for_sensitive: boolean;
  log_security_events: boolean;
  trust_score_notifications: boolean;
}

// Demo Mode
export interface DemoUser {
  id: number;
  email: string;
  full_name: string;
  security_role: string;
  trust_score: number;
  mfa_enabled: boolean;
  tenant_id: string;
}

// Export pricing types
export * from './pricing';
