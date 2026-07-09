'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface BankContextType {
    selectedBank: string;
    setSelectedBank: (bank: string) => void;
}

const BankContext = createContext<BankContextType | undefined>(undefined);

export const BankProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [selectedBank, setSelectedBank] = useState<string>("");

    // Persistence
    useEffect(() => {
        const saved = localStorage.getItem('selectedBank');
        if (saved) {
            setSelectedBank(!["undefined",undefined,null].includes(saved) ? saved : "");
        }
    }, []);

    const handleSetBank = (bank: string) => {
        setSelectedBank(bank);
        localStorage.setItem('selectedBank', bank);
    };

    return (
        <BankContext.Provider value={{ selectedBank, setSelectedBank: handleSetBank }}>
            {children}
        </BankContext.Provider>
    );
};

export const useBank = () => {
    const context = useContext(BankContext);
    if (!context) {
        throw new Error('useBank must be used within a BankProvider');
    }
    return context;
};
