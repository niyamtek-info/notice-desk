"use client";

import DashboardSidebar from "@/components/layout/DashboardSidebar";

import DashboardTable from "@/components/pages/dashboard/DashboardTable";
import Stats from "@/components/pages/dashboard/Stats";
import React, { useEffect, useState } from "react";
import { Button, Input, Select, DatePicker } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import usePageTitle from "@/hooks/usePageTitle";
import Link from "next/link";
import CreateApplicationModal from "@/components/modals/CreateApplicationModal";
import { HiOutlineBuildingOffice2 } from "react-icons/hi2";

import { BsBank } from "react-icons/bs";
import { FaPlus } from "react-icons/fa";
import { IoIosSearch } from "react-icons/io";
import { FiFilter } from "react-icons/fi";

const { Option } = Select;

import { useBank } from "@/context/BankContext";
import { BankApi } from "@/src/services/BankApi";

export default function DashboardPage() {
  usePageTitle("Dashboard");

  const [createModalOpen, setCreateModalOpen] = React.useState(false);
  const [refreshTrigger, setRefreshTrigger] = React.useState(0);
  const { selectedBank, setSelectedBank } = useBank();
  const [banks, setBanks] = useState<any>([{client_code:"all", client_name:"All Client", client: "all"}]);
  const [createType,setCreateType] = useState<string>("")

  // Search state
  const [searchAppNo, setSearchAppNo] = useState<string>("");
  const [searchBorrowerName, setSearchBorrowerName] = useState<string>("");
  const [searchLocation, setSearchLocation] = useState<string>("");
  const [selectedStatus, setSelectedStatus] = useState<string>("All");
  const [selectedSearchField, setSelectedSearchField] = useState<string>("All");
  const [clientSelectLoading, setClientSelectLoading] = useState<boolean>(false);

  useEffect(() => {
    // Restore last selected bank
    const savedBank = localStorage.getItem('selectedBank');
    if (!savedBank || savedBank === "undefined" || savedBank === "null" || savedBank === "") {
      setSelectedBank("all");
    }

    // Fetch client list once on mount — data is always needed as a primary filter
    const fetchBanks = async () => {
      try {
        setClientSelectLoading(true);
        const response: any = await BankApi.getBankList();
        setBanks([{ client_code: "all", client_name: "All Client", client: "all" }, ...response]);
      } catch (error) {
        // keep the default "All Client" entry on error
      } finally {
        setClientSelectLoading(false);
      }
    };

    fetchBanks();
  }, []);


  return (
    <div className="space-y-6">
      {/* Top Header Section */}
      <div className="flex justify-between items-center mt-4">
        <div>
          <h1 className="text-[26px] font-bold mb-1">Loan Application List</h1>
          <p className="text-sm text-gray-500">
            Manage and track all loan applications
          </p>
        </div>
        <div className="flex gap-4">
          <button
            className="flex items-center bg-gradient-to-r from-blue-600 via-blue-700 to-blue-800 hover:from-blue-700 hover:via-blue-800 hover:to-blue-900 text-white font-medium rounded-lg text-[16px] px-4 py-2 cursor-pointer transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
            onClick={() => {setCreateModalOpen(true),setCreateType("bulk")}}
          >
            <FaPlus className="mr-2" />
            Create Bulk Application
          </button>

           <button
            className="flex items-center bg-gradient-to-r from-blue-600 via-blue-700 to-blue-800 hover:from-blue-700 hover:via-blue-800 hover:to-blue-900 text-white font-medium rounded-lg text-[16px] px-4 py-2 cursor-pointer transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
            onClick={() => {setCreateModalOpen(true),setCreateType("manual")}}
          >
            <FaPlus className="mr-2" />
            Create Manual Application
          </button>
        </div>
      </div>

      {/* fgdfgd */}

      <div className="bg-white rounded-2xl p-6 shadow-md">
        {/* Top Section */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          {/* Left - Bank Select */}
          <div className="flex items-center gap-3 w-full">
            <div className="flex flex-col w-full">
              <div className="flex items-center gap-2 mb-1">
                <BsBank size={16} className="text-gray-600 text-xl mb-1.5" />
                <span className="text-md text-gray-600 font-semibold pb-1">
                  Select Client
                </span>
              </div>
 
              <Select
                placeholder="Choose Client"
                className="dashboard-select"
                style={{ borderRadius: "4px" }}
                loading={clientSelectLoading}
                onChange={(val) => {
                  setSelectedBank(val);
                  setSelectedStatus("All");
                  setSelectedSearchField("All");
                  setSearchAppNo("");
                }}
                value={selectedBank || undefined}
                showSearch
                allowClear
              >
                {banks.map((bank: any) => (
                  <Option key={bank.client_code} value={bank.client}>
                   {/* { `${bank?.bank_code} - ${bank?.bank_name}`} */}
                   <div className="flex items-center gap-2">
                    {bank?.client_code !== "all" &&
                    <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                      {bank.client_code}
                    </span>}
                    <span>{bank.client_name}</span>
                  </div>
                  </Option>
                ))}
              </Select>
            </div>
          </div>

          {/* Right - Single Search Input */}
          {/* <div className="flex items-center mt-5 gap-3">

      <Input
        placeholder="Search by Application No, Borrower Name, or Location..."
        prefix={<IoIosSearch size={20} className="text-gray-700" />}
        className="!w-[450px] h-[40px] !rounded-md shadow-md !bg-[#f1f5fe] placeholder:!text-gray-800 transition-colors duration-200"
        value={searchAppNo}
        onChange={(e) => setSearchAppNo(e.target.value)}
      />

    </div> */}
        </div>

        {/* Status Tabs */}
        <div className="flex items-center gap-3 mt-6">
          <button
            className={`px-4 py-1.5 text-sm rounded-full ${
              selectedStatus === "All"
                ? "bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 text-white"
                : "bg-gray-20 text-gray-600 hover:bg-blue-50 cursor-pointer"
            }`}
            onClick={() => {
              setSelectedStatus("All");
              setSelectedSearchField("All");
              setSearchAppNo("");
            }}
          >
            All
          </button>

          <button
            className={`px-4 py-1.5 text-sm rounded-full ${
              selectedStatus === "Available"
                ? "bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 text-white"
                : "bg-gray-20 text-gray-600 hover:bg-blue-50 cursor-pointer"
            }`}
            onClick={() => {
              setSelectedStatus("Available");
              setSelectedSearchField("All");
              setSearchAppNo("");
            }}
          >
            Available
          </button>

          <button
            className={`px-4 py-1.5 text-sm rounded-full ${
              selectedStatus === "Not_Available"
                ? "bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 text-white"
                : "bg-gray-20 text-gray-600 hover:bg-blue-50 cursor-pointer"
            }`}
            onClick={() => {
              setSelectedStatus("Not_Available");
              setSelectedSearchField("All");
              setSearchAppNo("");
            }}
          >
            Not Available
          </button>
        </div>
      </div>

      {/* Stats Section */}
      {selectedBank && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-6">
          <Stats />
        </div>
      )}

      {/* fsd */}

      {/* Data Table Section */}
      <div className="bg-white rounded-xl shadow-md p-6">
        {selectedBank ? (
          <div className="dasboard__table">
            <DashboardTable
              refreshKey={refreshTrigger}
              banks={banks}
              searchAppNo={searchAppNo}
              searchBorrowerName={searchBorrowerName}
              searchLocation={searchLocation}
              selectedStatus={selectedStatus}
              selectedSearchField={selectedSearchField}
              onSearchChange={setSearchAppNo}
              onStatusChange={setSelectedStatus}
              onSearchFieldChange={setSelectedSearchField}
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <BsBank className="text-gray-400 text-xl" />
            </div>
            <p className="text-gray-500 text-lg font-medium text-center">
              Please select a bank from above to view application data.
            </p>
          </div>
        )}
      </div>

      {/* Create Application Modal */}
      <CreateApplicationModal
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onSuccess={() => setRefreshTrigger((prev) => prev + 1)}
        banks={banks}
        createType={createType}
      />
    </div>
  );
}
