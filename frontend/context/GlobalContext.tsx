"use client";

import { createContext, useContext, useState } from "react";

interface ContextType {
  progressId: string | null;
  setProgressId: (progressId: string | null) => void;
  docProgressId: string | null;
  setDocProgressId: (progressId: string | null) => void;
  docFileId: string[];
  setDocFileId: (docFileId: string[]) => void;
}

const GlobalContext = createContext<ContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [progressId, setProgressId] = useState<string | null>(null);
  const [docProgressId, setDocProgressId] = useState<string | null>(null);
  const [docFileId, setDocFileId] = useState<string[]>([]);

  return (
    <GlobalContext.Provider
      value={{ progressId, setProgressId, docProgressId, setDocProgressId, docFileId, setDocFileId }}
    >
      {children}
    </GlobalContext.Provider>
  );
}

export const useAppContext = () => {
  const context = useContext(GlobalContext);
  if (!context) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
};
