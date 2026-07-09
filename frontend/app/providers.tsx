"use client";
import { Provider } from "react-redux";
import { store } from "@/store";
import { ConfigProvider } from "antd";
import { AppProvider } from "@/context/GlobalContext";
import { BankProvider } from "@/context/BankContext";


export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      <AppProvider>
      <BankProvider>  
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: "#2563eb",
          },
          components: {
            Button: {
              borderRadius: 8,
              controlHeight: 40,
              fontSize: 14,
              fontWeight: 500,
            },
            Input: {
              controlHeight: 40,
              borderRadius: 8,
            },
            Select: {
              controlHeight: 40,
              borderRadius: 8,
            },
            DatePicker: {
              controlHeight: 40,
              borderRadius: 8,
            },
            InputNumber: {
              controlHeight: 40,
              borderRadius: 8,
            },
          },
        }}
      >
        {children}
      </ConfigProvider>
      </BankProvider>
      </AppProvider>
    </Provider>
  );
}