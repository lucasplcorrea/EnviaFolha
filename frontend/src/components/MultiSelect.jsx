import React, { useState, Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { ChevronDownIcon, CheckIcon, XMarkIcon } from '@heroicons/react/20/solid';

/**
 * Componente de Multi-Select com busca
 * @param {Array} options - Array de opções { value, label }
 * @param {Array} selected - Array de valores selecionados
 * @param {Function} onChange - Callback quando seleção muda
 * @param {String} placeholder - Texto quando nada selecionado
 * @param {Boolean} searchable - Habilitar busca
 * @param {String} label - Label do campo
 */
const MultiSelect = ({ 
  options = [], 
  selected = [], 
  onChange, 
  placeholder = 'Selecione...', 
  searchable = false,
  label = ''
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  // Filtrar opções baseado na busca
  const filteredOptions = searchable && searchQuery
    ? options.filter(option => 
        option.label.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : options;

  // Toggle seleção de um item
  const toggleSelection = (value) => {
    if (selected.includes(value)) {
      onChange(selected.filter(v => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  // Remover um item selecionado
  const removeItem = (e, value) => {
    e.stopPropagation();
    onChange(selected.filter(v => v !== value));
  };

  // Limpar tudo
  const clearAll = (e) => {
    e.stopPropagation();
    onChange([]);
    setSearchQuery('');
  };

  // Pegar labels dos selecionados
  const selectedLabels = selected.map(val => {
    const option = options.find(opt => opt.value === val);
    return option ? option.label : val;
  });

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      
      <Listbox value={selected} onChange={() => {}}>
        {({ open }) => (
          <div className="relative">
            <Listbox.Button className="relative w-full cursor-pointer rounded-lg bg-white dark:bg-gray-800 py-2 pl-3 pr-10 text-left border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
              <span className="block truncate">
                {selected.length === 0 ? (
                  <span className="text-gray-500 dark:text-gray-400">{placeholder}</span>
                ) : (
                  <span className="text-gray-900 dark:text-gray-100">
                    {selected.length} {selected.length === 1 ? 'item selecionado' : 'itens selecionados'}
                  </span>
                )}
              </span>
              <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                {selected.length > 0 ? (
                  <XMarkIcon
                    className="h-5 w-5 text-gray-400 hover:text-gray-600 cursor-pointer pointer-events-auto"
                    onClick={clearAll}
                  />
                ) : (
                  <ChevronDownIcon className="h-5 w-5 text-gray-400" />
                )}
              </span>
            </Listbox.Button>

            <Transition
              show={open}
              as={Fragment}
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Listbox.Options className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white dark:bg-gray-800 py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                {/* Campo de busca */}
                {searchable && (
                  <div className="sticky top-0 bg-white dark:bg-gray-800 px-2 py-2 border-b border-gray-200 dark:border-gray-700">
                    <input
                      type="text"
                      className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Buscar..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                )}

                {/* Opções */}
                {filteredOptions.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                    Nenhuma opção encontrada
                  </div>
                ) : (
                  filteredOptions.map((option) => {
                    const isSelected = selected.includes(option.value);
                    return (
                      <Listbox.Option
                        key={option.value}
                        value={option.value}
                        onClick={() => toggleSelection(option.value)}
                        className={({ active }) =>
                          `relative cursor-pointer select-none py-2 pl-10 pr-4 ${
                            active
                              ? 'bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100'
                              : 'text-gray-900 dark:text-gray-100'
                          }`
                        }
                      >
                        <span className={`block truncate ${isSelected ? 'font-medium' : 'font-normal'}`}>
                          {option.label}
                        </span>
                        {isSelected && (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600 dark:text-blue-400">
                            <CheckIcon className="h-5 w-5" />
                          </span>
                        )}
                      </Listbox.Option>
                    );
                  })
                )}
              </Listbox.Options>
            </Transition>
          </div>
        )}
      </Listbox>
    </div>
  );
};

export default MultiSelect;
