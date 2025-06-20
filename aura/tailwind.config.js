/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // WebAgent Brand Colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        // Security Status Colors
        security: {
          critical: '#dc2626',
          high: '#ea580c',
          medium: '#d97706',
          low: '#65a30d',
          info: '#0891b2',
        },
        // Trust Score Colors
        trust: {
          very_low: '#dc2626',
          low: '#ea580c',
          medium: '#d97706',
          high: '#65a30d',
          very_high: '#16a34a',
        },
        // Enterprise Theme
        enterprise: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'security-scan': 'securityScan 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        securityScan: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.05)', opacity: '0.8' },
        },
      },
      boxShadow: {
        'security': '0 4px 14px 0 rgba(59, 130, 246, 0.15)',
        'enterprise': '0 8px 32px 0 rgba(15, 23, 42, 0.1)',
        'trust-high': '0 4px 14px 0 rgba(34, 197, 94, 0.2)',
        'trust-low': '0 4px 14px 0 rgba(220, 38, 38, 0.2)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [
    // Add form plugin for better form styling
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
  ],
  // Dark mode configuration
  darkMode: 'class',
}
