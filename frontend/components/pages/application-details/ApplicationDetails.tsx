"use client";

import React, { useEffect, useMemo, useState } from "react";
import Sidebar from "./Sidebar";
import ReportsContent from "@/components/pages/application-details/ReportsContent"; // Placeholder
import { useRouter } from "next/navigation";
import { BiArrowBack } from "react-icons/bi";
import { ApplicationApi } from "@/src/services/ApplicationApi";
import Actionsidebar from "./Actionsidebar";
import { BankApi } from "@/src/services/BankApi";

interface ApplicationDetailsProps {
  applicationId: string;
  recordId: string;
}

const ApplicationDetails: React.FC<ApplicationDetailsProps> = ({
  applicationId,
  recordId,
}) => {
  const [activeItem, setActiveItem] = useState("Loan Application");
  const [token, setToken] = useState<string>("");
  const router = useRouter();
  const [initialData, setInitialData] = useState<any>();
  const [update, setUpdate] = useState<number>(0)
  const [headerText, setHeaderText] = useState<any>({
    borrowerName: false,
    account: false,
    appId: false
  })
  const [banks, setBanks] = useState<any[]>([]);
  const [triggerReport, setTriggerReport] = useState<any>(0);


  const fetchBanks = async () => {
    try {
      // Fetch banks data - replace with actual API call
      const bankData: any = await BankApi.getBankList(); // Using existing method
      setBanks(bankData || []);
    } catch (error) {
      console.error("Failed to fetch banks:", error);
      setBanks([]); // Fallback to empty array
    }
  };

  useEffect(() => {
    fetchBanks();
  }, []);

  const fetchData = async () => {
    try {
      if (recordId) {
        const result: any = await ApplicationApi.getById(recordId);
        setInitialData(result?.data);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    }
  }

  useEffect(() => {
    fetchData()
  }, [update])


  const bankCode = useMemo(() => {
    if (!banks || !initialData?.client_name) return "";

    const found = banks.find(
      (res: any) => res.client_name.trim().toLowerCase() === initialData.client_name.trim().toLowerCase()
    );

    return found?.client_code || "";
  }, [banks, initialData?.client_name]);



  useEffect(() => {
    const tokenData = localStorage.getItem("token");
    if (tokenData) {
      setToken(tokenData);
    } else {
      setToken("");
    }
  }, []);

  const renderContent = () => {
    switch (activeItem) {
      case "Loan Details":
        return (
          <div className="bg-white rounded-lg shadow-md border border-gray-100 min-h-[80vh] p-4">
            <ReportsContent applicationId={applicationId} recordId={recordId} setUpdate={setUpdate} initialData={initialData} activeItem={activeItem} triggerReport={triggerReport} />
          </div>
        );
      default:
        return (
          <div>
            <ReportsContent applicationId={applicationId} recordId={recordId} setUpdate={setUpdate} initialData={initialData} activeItem={activeItem} triggerReport={triggerReport} />
          </div>
        );
    }
  };

  const handleHover = (type: string) => {
    setHeaderText((pre: any) => ({ ...pre, [type]: true }))
  }

  const handleHoverEnd = (type: string) => {
    setHeaderText((pre: any) => ({ ...pre, [type]: false }))
  }

  return (
    <div className="min-h-screen flex flex-col !bg-[#f5f5f5]">
      {/* Header */}

      <div className="fixed top-0 left-0 right-0 z-30 bg-white border-b border-gray-200 shadow-sm">
        <div className="px-3 sm:px-4 md:px-5 py-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 sm:gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="flex items-center gap-2 text-gray-600 hover:text-blue-600 font-medium transition-all duration-200 cursor-pointer px-3 py-2 rounded-lg hover:bg-blue-50 group"
          >
            <BiArrowBack className="text-lg group-hover:-translate-x-1 transition-transform duration-200" />
            <span className="hidden sm:inline">Back to Dashboard</span>
            <span className="sm:hidden">Back</span>
          </button>
          <div className="flex flex-wrap gap-2 sm:gap-3 justify-center sm:justify-start">
            <div onMouseEnter={() => handleHover("borrowerName")} onMouseLeave={() => handleHoverEnd("borrowerName")} className="flex items-center gap-1.5 bg-gradient-to-r from-blue-50 to-blue-100/50 px-3 py-1.5 rounded-lg border border-blue-200 w-fit">
              <span className="text-gray-600 text-xs sm:text-sm font-medium flex-shrink-0">Borrower:</span>
              <span className={`font-semibold text-primary-600 text-xs sm:text-sm truncate whitespace-nowrap`}>
                {initialData?.borrower_name ? initialData?.borrower_name : "—"}
              </span>
            </div>
            <div onMouseEnter={() => handleHover("account")} onMouseLeave={() => handleHoverEnd("account")} className="flex items-center gap-1.5 bg-gradient-to-r from-green-50 to-green-100/50 px-3 py-1.5 rounded-lg border border-green-200 w-fit">
              <span className="text-gray-600 text-xs sm:text-sm font-medium flex-shrink-0">Account:</span>
              <span className={`font-semibold text-green-700 text-xs sm:text-sm truncate whitespace-nowrap`}>
                {initialData?.loan_account_number ? initialData?.loan_account_number : "—"}
              </span>
            </div>
            <div onMouseEnter={() => handleHover("appId")} onMouseLeave={() => handleHoverEnd("appId")} className="flex items-center gap-1.5 bg-gradient-to-r from-purple-50 to-purple-100/50 px-3 py-1.5 rounded-lg border border-purple-200 w-fit">
              <span className="text-gray-600 text-xs sm:text-sm font-medium flex-shrink-0">App ID:</span>
              <span className={`font-semibold text-purple-700 text-xs sm:text-sm truncate whitespace-nowrap`}>
                {applicationId ? applicationId : "—"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-20 gap-2 items-start flex-1 pt-[75px] sm:pt-[80px] md:pt-[85px] lg:pt-[85px] px-2 sm:px-3 md:px-4">
        <div className="col-span-4 sticky top-[75px] sm:top-[80px] md:top-[85px] self-start h-[calc(100vh-75px)] sm:h-[calc(100vh-80px)] md:h-[calc(100vh-85px)]">
          <Sidebar activeItem={activeItem} onSelect={setActiveItem} />
        </div>
        <div className="col-span-13 w-full">{renderContent()}</div>
        <div className="col-span-3 sticky top-[75px] sm:top-[80px] md:top-[85px] self-start h-[calc(100vh-75px)] sm:h-[calc(100vh-80px)] md:h-[calc(100vh-85px)]">
          <Actionsidebar applicationId={applicationId} token={token} bankCode={bankCode} banks={banks} setTriggerReport={setTriggerReport} initialData={initialData} />
        </div>
      </div>

    </div>
  );
};

export default ApplicationDetails;
