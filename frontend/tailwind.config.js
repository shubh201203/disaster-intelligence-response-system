/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Obsidian & Dark Operational Palette
        obsidian: {
          950: '#07090e', // Level 0: Main workspace background
          900: '#0d1117', // Level 1: Workspace panels & sidebars
          850: '#121722', // Level 2: Surface cards & modals
          800: '#182030', // Level 3: Focused/interactive surfaces
          700: '#222d42', // Elevated borders & dividers
          600: '#2e3d5a', // Highlight borders
          500: '#425375',
          400: '#64748b',
          300: '#94a3b8',
          200: '#cbd5e1',
          100: '#f1f5f9',
        },
        // Emergency Operational Amber (Primary Brand Accent)
        amber: {
          ops: '#f59e0b',
          bright: '#fbbf24',
          dark: '#d97706',
          muted: '#78350f',
        },
        // Electric Restrained Cyan (Secondary Accent & Telemetry)
        cyan: {
          ops: '#06b6d4',
          bright: '#22d3ee',
          dark: '#0891b2',
          muted: '#164e63',
        },
        // Semantic Status Palette
        status: {
          critical: '#ef4444',
          high: '#f97316',
          medium: '#f59e0b',
          low: '#10b981',
          info: '#06b6d4',
          success: '#10b981',
          warning: '#f59e0b',
        },
        // Backward compatibility for existing color classes
        brand: {
          50: '#fef3c7',
          100: '#fde68a',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          900: '#78350f',
        },
        emergency: {
          critical: '#ef4444',
          high: '#f97316',
          medium: '#f59e0b',
          low: '#10b981',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'radar': 'radar 3s linear infinite',
        'pulse-subtle': 'pulseSubtle 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-pulse': 'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        radar: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 10px rgba(245, 158, 11, 0.2)' },
          '50%': { boxShadow: '0 0 20px rgba(245, 158, 11, 0.45)' },
        }
      }
    },
  },
  plugins: [],
}
