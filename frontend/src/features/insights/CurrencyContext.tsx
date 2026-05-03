import { createContext, useContext, useState } from "react";

const STORAGE_KEY = "display_currency";

interface CurrencyContextValue {
  currency: string;
  setCurrency: (c: string) => void;
}

const CurrencyContext = createContext<CurrencyContextValue>({
  currency: "JPY",
  setCurrency: () => {},
});

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [currency, setCurrencyState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? "JPY",
  );

  function setCurrency(c: string) {
    localStorage.setItem(STORAGE_KEY, c);
    setCurrencyState(c);
  }

  return (
    <CurrencyContext.Provider value={{ currency, setCurrency }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency(): CurrencyContextValue {
  return useContext(CurrencyContext);
}
