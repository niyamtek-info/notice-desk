"use client";

import React, { useEffect, useState, useRef } from "react";
import { message } from "antd";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

export default function NetworkChecker() {
  const isOnline = useOnlineStatus();
  const [messageApi, contextHolder] = message.useMessage();
  const [showOfflineError, setShowOfflineError] = useState(false);

  const hasShownConnected = useRef(false);
  const isFirstLoad = useRef(true); // 👈 track first render

  useEffect(() => {
    if (!isOnline) {
      setShowOfflineError(true);

      messageApi.open({
        key: "network-error",
        type: "error",
        content: "Please check your internet connection",
        duration: 0,
      });

      hasShownConnected.current = false;
    } else {
      setShowOfflineError(false);
      messageApi.destroy();

      // ✅ Skip showing "connected" message on initial load
      if (!hasShownConnected.current && !isFirstLoad.current) {
        messageApi.success("Internet connected", 2.5);
        hasShownConnected.current = true;
      }
    }

    // After first effect run, mark as not first load
    isFirstLoad.current = false;
  }, [isOnline, messageApi]);

  return <>{contextHolder}</>;
}
