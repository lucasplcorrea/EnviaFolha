import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme deve ser usado dentro de ThemeProvider');
  }
  return context;
};

export const THEMES = {
  LIGHT: 'light',
  DARK: 'dark'
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('nexo-rh-theme');
    return savedTheme || THEMES.LIGHT;
  });

  useEffect(() => {
    localStorage.setItem('nexo-rh-theme', theme);
    
    // Remove todas as classes de tema
    document.documentElement.classList.remove('dark', 'nexo-theme', 'abecker-theme');
    
    // Adiciona a classe apropriada
    if (theme === THEMES.DARK) {
      document.documentElement.classList.add('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    const themes = Object.values(THEMES);
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  const setSpecificTheme = (newTheme) => {
    if (Object.values(THEMES).includes(newTheme)) {
      setTheme(newTheme);
    }
  };

  const getThemeConfig = () => {
    switch (theme) {
      case THEMES.LIGHT:
        return {
          name: 'Claro',
          icon: '☀️',
          classes: {
            body: 'bg-gray-50 text-gray-900',
            card: 'bg-white border-gray-200',
            sidebar: 'bg-white border-gray-200',
            button: 'bg-blue-600 hover:bg-blue-700 text-white',
            buttonSecondary: 'bg-gray-200 hover:bg-gray-300 text-gray-900',
            text: 'text-gray-900',
            textSecondary: 'text-gray-600',
            border: 'border-gray-200',
            input: 'bg-white border-gray-300 text-gray-900 placeholder-gray-500',
            select: 'bg-white border-gray-300 text-gray-900',
            link: 'text-blue-600 hover:text-blue-800',
            tableHeader: 'bg-gray-50',
            tableRow: 'bg-white hover:bg-gray-50',
            tableRowAlt: 'bg-gray-50 hover:bg-gray-100'
          }
        };
      case THEMES.DARK:
        return {
          name: 'Escuro',
          icon: '🌙',
          classes: {
            body: 'bg-gray-900 text-white',
            card: 'bg-gray-800 border-gray-700',
            sidebar: 'bg-gray-800 border-gray-700',
            button: 'bg-blue-600 hover:bg-blue-700 text-white',
            buttonSecondary: 'bg-gray-700 hover:bg-gray-600 text-white',
            text: 'text-white',
            textSecondary: 'text-gray-300',
            border: 'border-gray-700',
            input: 'bg-gray-700 border-gray-600 text-white placeholder-gray-400',
            select: 'bg-gray-700 border-gray-600 text-white',
            textarea: 'bg-gray-700 border-gray-600 text-white placeholder-gray-400',
            link: 'text-blue-400 hover:text-blue-300',
            tableHeader: 'bg-gray-700',
            tableRow: 'bg-gray-800 hover:bg-gray-700',
            tableRowAlt: 'bg-gray-700 hover:bg-gray-600'
          }
        };
      default:
        return getThemeConfig.call(this, THEMES.LIGHT);
    }
  };

  const value = {
    theme,
    setTheme: setSpecificTheme,
    toggleTheme,
    config: getThemeConfig(),
    themes: THEMES
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};