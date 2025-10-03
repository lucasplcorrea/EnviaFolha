import React from 'react';
import { useTheme, THEMES } from '../contexts/ThemeContext';

const ThemeSelector = () => {
  const { theme, setTheme } = useTheme();

  const themeOptions = [
    { key: THEMES.LIGHT, name: 'Claro', icon: '☀️' },
    { key: THEMES.DARK, name: 'Escuro', icon: '🌙' }
  ];

  return (
    <div className="relative">
      <div className="flex space-x-1 rounded-lg bg-gray-100 dark:bg-gray-800 p-1">
        {themeOptions.map((option) => (
          <button
            key={option.key}
            onClick={() => setTheme(option.key)}
            className={`
              flex items-center space-x-2 px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200
              ${theme === option.key
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white'
              }
            `}
          >
            <span>{option.icon}</span>
            <span className="hidden sm:inline">{option.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ThemeSelector;