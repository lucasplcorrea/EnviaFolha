/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1', // Indigo tech principal
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
        },
        // Cores ABecker corporativas
        abecker: {
          50:  '#F0F9FF',  // Azul muito claro
          100: '#E0F2FE',  // Azul claro
          200: '#BAE6FD',  // Azul suave
          300: '#7DD3FC',  // Azul médio
          400: '#38BDF8',  // Azul vibrante
          500: '#0EA5E9',  // Azul principal ABecker
          600: '#0284C7',  // Azul escuro
          700: '#0369A1',  // Azul corporativo
          800: '#075985',  // Azul muito escuro
          900: '#0C4A6E',  // Azul profundo
        },
        // Cores de apoio ABecker
        abeckerAccent: {
          orange: '#F97316',   // Laranja corporativo
          gray: '#64748B',     // Cinza neutro
          green: '#059669',    // Verde aprovação
          red: '#DC2626',      // Vermelho alerta
        },
        accent: {
          green: '#10B981',   // Sucesso/positivo
          red: '#EF4444',     // Alerta/erros
          yellow: '#F59E0B',  // Atenção
          cyan: '#06B6D4',    // Destaque secundário
        },
        // Classes específicas para uso direto
        'accent-green': '#10B981',
        'accent-red': '#EF4444',
        'accent-yellow': '#F59E0B',
        'accent-cyan': '#06B6D4',
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
        success: {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
        },
        warning: {
          50: '#fffbeb',
          500: '#f59e0b',
          600: '#d97706',
        },
        error: {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
        }
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
