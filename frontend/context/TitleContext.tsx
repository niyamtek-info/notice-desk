// context/TitleContext.tsx
'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface TitleContextType {
  title: string;
  setTitle: React.Dispatch<React.SetStateAction<string>>;
}

const TitleContext = createContext<TitleContextType | undefined>(undefined);

interface TitleProviderProps {
  children: ReactNode;
}

export const TitleProvider: React.FC<TitleProviderProps> = ({ children }) => {
  const [title, setTitle] = useState<string>('');

  return (
    <TitleContext.Provider value={{ title, setTitle }}>
      {children}
    </TitleContext.Provider>
  );
};

export const useTitle = (): TitleContextType => {
  const context = useContext(TitleContext);
  if (!context) {
    throw new Error('useTitle must be used within a TitleProvider');
  }
  return context;
};
