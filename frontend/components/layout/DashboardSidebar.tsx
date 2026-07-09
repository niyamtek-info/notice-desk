'use client';

import React, { useState, useEffect } from 'react';
import { FaPlus } from "react-icons/fa";
import { BiSolidBarChartAlt2 } from "react-icons/bi";
import { MdOutlineHealthAndSafety } from "react-icons/md";
import { BsSend } from "react-icons/bs";
import { Input, Spin } from 'antd';
import { useRouter } from 'next/navigation';
import { PiWarningCircle } from 'react-icons/pi';

const { TextArea } = Input;

interface CommunicationLog {
  timestamp: string;
  channel: string;
  recipient: string;
  message: string;
  status: string;
  application_id?: number;
}

const DashboardSidebar: React.FC = () => {
  const router = useRouter();
  const [message, setMessage] = useState(
    "Hello! I'm your AI legal assistant. How can I help you with legal knowledge today?"
  );

  const [logs, setLogs] = useState<CommunicationLog[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // ✅ Fetch ALL communication logs
  const fetchCommunicationLogs = async () => {
    try {
      setLoading(true);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/communication/communication-logs`
      );
      if (!res.ok) throw new Error("Failed to fetch communication logs");
      const data = await res.json();

      setLogs(data.logs || []);
    } catch (error) {
      console.error("❌ Error fetching communication logs:", error);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommunicationLogs();
  }, []);

  const handleSend = async () => {
    if (!message.trim()) return;
    await router.push(`/knowledge-base/ai-chatbot?message=${encodeURIComponent(message)}`);
  };

  return (
    <div>
      {/*Actions */}
      <div className="border-gray-100 shadow-md rounded-lg p-4 bg-white">
        <p className="text-gray-700 mb-2 font-semibold">Actions</p>
        <button className="w-full text-[13px] text-gray-500 hover:text-gray-600 px-3 py-2 rounded-lg flex items-center">
          <FaPlus className="mr-3" /> Schedule New Job
        </button>

        <button className="w-full text-[13px] text-gray-500 hover:text-gray-600 px-3 py-2 rounded-lg flex items-center my-1">
          <BiSolidBarChartAlt2 className="mr-3" /> View Reports
        </button>

        <button className="w-full text-[13px] text-gray-500 hover:text-gray-600 px-3 py-2 rounded-lg flex items-center">
          <MdOutlineHealthAndSafety className="mr-2 text-[18px]" /> System Health
        </button>
      </div>

      {/* Knowledge Base */}
      <div className="my-5 border-gray-100 shadow-md rounded-lg p-4 bg-white">
        <p className="text-gray-700 mb-2 font-semibold">Knowledge Base</p>
        <TextArea
          rows={4}
          className="!text-[13px] !text-gray-700"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button
          className="mt-2 w-full bg-primary-500 hover:bg-primary-700 text-white text-[13px] font-medium py-1.5 px-4 rounded-lg flex items-center justify-center"
          onClick={handleSend}
        >
          Send <BsSend className="ml-1" />
        </button>
      </div>

      {/* Recent Communication */}
      <div className="border-gray-100 shadow-md rounded-lg p-4 bg-white">
        <p className="text-gray-700 mb-2 font-semibold">Recent Communication</p>

        {loading ? (
          <div className="flex justify-center py-4">
            <Spin size="small" />
          </div>
        ) : logs.length === 0 ? (
          <p className="text-[13px] text-gray-500">No recent communication found.</p>
        ) : (
          logs.slice(0, 3).map((log, index) => (
            <div
              key={index}
              className="w-full text-gray-700 font-normal rounded-lg text-sm py-2.5 flex items-start"
            >
              {log.status === "error" ? (
                <PiWarningCircle className="mr-3 mt-1 text-[17px] text-red-500" />
              ) : (
                <BsSend className="mr-3 mt-1 text-[17px] text-primary-500" />
              )}
              <div>
                <p className="text-[13px] pb-1">{log.message} {log.recipient}</p>
                <p className="text-[12px] text-gray-500">
                  {new Date(log.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default DashboardSidebar;