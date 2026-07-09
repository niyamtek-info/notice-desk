import React, { createContext, useContext, useState, useEffect } from "react";

interface LoanContextType {
  applicationNumber: string;
  setApplicationNumber: (num: string) => void;
}

const LoanContext = createContext<LoanContextType | undefined>(undefined);

export const LoanProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [applicationNumber, setApplicationNumber] = useState("");

// Load from localStorage on mount
useEffect(() => {
  const stored = localStorage.getItem("applicationNumber");
  if (stored) setApplicationNumber(stored);
}, []);

// Save to localStorage when applicationNumber changes
useEffect(() => {
  if (applicationNumber) {
    localStorage.setItem("applicationNumber", applicationNumber);
  }
}, [applicationNumber]);


  return (
    <LoanContext.Provider value={{ applicationNumber, setApplicationNumber }}>
      {children}
    </LoanContext.Provider>
  );
};

export const useAppNoContext = () => {
  const ctx = useContext(LoanContext);
  if (!ctx) throw new Error("useLoanContext must be used within LoanProvider");
  return ctx;
};
