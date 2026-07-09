"use client";

import React, { Suspense } from "react";
import { Layout } from "antd";
import HeaderSection from "@/components/layout/HeaderSection";

const { Header, Content } = Layout;

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { BankProvider } from "@/context/BankContext";

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/sign-in");
    }
  }, [router]);

  return (
    <BankProvider>
      <Layout style={{ minHeight: "100vh", position: "relative" }}>
        <Layout
          style={{
            minHeight: "100vh",
          }}
        >
          <Header
            className="!bg-white flex items-center"
            style={{
              position: "sticky",
              top: 0,
              zIndex: 99,
              width: "100%",
              height: 64,
              display: "flex",
              alignItems: "center",
              background: "#fff",
              boxShadow: "0 2px 8px #f0f1f2",
            }}
          >
            <div className="max-w-[1440px] mx-auto w-full px-[20px] flex items-center h-full">
              <Suspense fallback={<div>Loading Header...</div>}>
                <HeaderSection
                  collapsed={false}
                  collapsedWidth={0}
                  toggleCollapsed={() => { }}
                />
              </Suspense>
            </div>
          </Header>

          <Content
            className="bg-[#eceff5]"
            style={{ minHeight: "calc(100vh - 64px)" }}
          >
            <div className="max-w-[1440px] mx-auto mb-6 px-8 pt-1 pb-8">
              {children}
            </div>
          </Content>
        </Layout>
      </Layout>
    </BankProvider>
  );
}
