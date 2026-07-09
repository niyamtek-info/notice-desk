"use client";

import React from "react";
import { TitleProvider } from "@/context/TitleContext";
import { LoanProvider } from "@/context/AppNoContext";
import { App as AntdApp, ConfigProvider } from "antd";
import AuthSessionManager from "@/components/auth/AuthSessionManager";

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <ConfigProvider>
      <AntdApp>
        <AuthSessionManager />
        <TitleProvider>
          <LoanProvider>
            {children}
          </LoanProvider>
        </TitleProvider>
      </AntdApp>
    </ConfigProvider>
  );
}
