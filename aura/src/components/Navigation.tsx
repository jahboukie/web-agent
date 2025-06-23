/**
 * Navigation Component
 *
 * Sidebar navigation for WebAgent Aura with role-based access control
 * and enterprise features.
 */

import React from "react";
import { NavLink } from "react-router-dom";
import {
  Home,
  Activity,
  Shield,
  Users,
  Settings,
  FileText,
  BarChart3,
  Lock,
  Eye,
  Server,
  X,
} from "lucide-react";
import { useAuth, usePermissions } from "../contexts/AuthContext";
import { cn } from "../lib/utils";

interface NavigationProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
  requiredPermission?: string;
  children?: NavItem[];
}

export function Navigation({ isOpen, onClose }: NavigationProps) {
  const { user } = useAuth();
  const { isAdmin, canManageUsers, canViewAuditLogs, canManageAutomation } =
    usePermissions();

  const navigationItems: NavItem[] = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: Home,
    },
    {
      name: "Tasks",
      href: "/tasks",
      icon: Activity,
      badge: "3",
    },
    {
      name: "Security",
      href: "/security",
      icon: Shield,
      children: [
        {
          name: "Zero Trust",
          href: "/security/zero-trust",
          icon: Lock,
        },
        {
          name: "Audit Logs",
          href: "/security/audit-logs",
          icon: Eye,
          requiredPermission: "view_audit_logs",
        },
        {
          name: "SIEM Events",
          href: "/security/siem",
          icon: Server,
          requiredPermission: "view_audit_logs",
        },
      ],
    },
    {
      name: "Analytics",
      href: "/analytics",
      icon: BarChart3,
    },
    {
      name: "Users",
      href: "/users",
      icon: Users,
      requiredPermission: "manage_users",
    },
    {
      name: "Reports",
      href: "/reports",
      icon: FileText,
    },
    {
      name: "Settings",
      href: "/settings",
      icon: Settings,
    },
  ];

  const hasPermission = (permission?: string): boolean => {
    if (!permission) return true;

    switch (permission) {
      case "manage_users":
        return canManageUsers();
      case "view_audit_logs":
        return canViewAuditLogs();
      case "manage_automation":
        return canManageAutomation();
      default:
        return true;
    }
  };

  const filteredItems = navigationItems.filter((item) =>
    hasPermission(item.requiredPermission),
  );

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden bg-gray-600 bg-opacity-75"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex flex-col h-full">
          {/* Mobile close button */}
          <div className="flex items-center justify-between p-4 lg:hidden">
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              Navigation
            </span>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
            {filteredItems.map((item) => (
              <NavItem key={item.name} item={item} onItemClick={onClose} />
            ))}
          </nav>

          {/* User info */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 bg-primary-600 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-white">
                  {user?.full_name
                    ?.split(" ")
                    .map((n) => n[0])
                    .join("")
                    .toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {user?.full_name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user?.security_role.replace("_", " ")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// Individual Navigation Item Component
interface NavItemProps {
  item: NavItem;
  onItemClick: () => void;
  depth?: number;
}

function NavItem({ item, onItemClick, depth = 0 }: NavItemProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const hasChildren = item.children && item.children.length > 0;

  const handleClick = () => {
    if (hasChildren) {
      setIsExpanded(!isExpanded);
    } else {
      onItemClick();
    }
  };

  const paddingLeft = depth === 0 ? "pl-3" : "pl-8";

  return (
    <div>
      {hasChildren ? (
        <button
          type="button"
          onClick={handleClick}
          className={cn(
            "w-full flex items-center justify-between py-2 px-3 text-sm font-medium rounded-lg transition-colors",
            "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700",
            paddingLeft,
          )}
        >
          <div className="flex items-center space-x-3">
            <item.icon className="h-5 w-5" />
            <span>{item.name}</span>
          </div>
          <div className="flex items-center space-x-2">
            {item.badge && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200">
                {item.badge}
              </span>
            )}
            <svg
              className={cn(
                "h-4 w-4 transition-transform",
                isExpanded ? "rotate-90" : "rotate-0",
              )}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </button>
      ) : (
        <NavLink
          to={item.href}
          onClick={onItemClick}
          className={({ isActive }) =>
            cn(
              "flex items-center justify-between py-2 px-3 text-sm font-medium rounded-lg transition-colors",
              isActive
                ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-200"
                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700",
              paddingLeft,
            )
          }
        >
          <div className="flex items-center space-x-3">
            <item.icon className="h-5 w-5" />
            <span>{item.name}</span>
          </div>
          {item.badge && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200">
              {item.badge}
            </span>
          )}
        </NavLink>
      )}

      {/* Children */}
      {hasChildren && isExpanded && (
        <div className="mt-1 space-y-1">
          {item.children?.map((child) => (
            <NavItem
              key={child.name}
              item={child}
              onItemClick={onItemClick}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
