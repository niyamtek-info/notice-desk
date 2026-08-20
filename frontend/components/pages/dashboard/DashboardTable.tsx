"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  Table,
  Dropdown,
  Modal,
  Button,
  Badge,
  message,
  Card,
  Space,
  Tag,
  Typography,
  Avatar,
  Tooltip,
  Input,
  Select,
} from "antd";
import {
  MoreOutlined,
  SearchOutlined,
  FilterOutlined,
  EyeOutlined,
  EditOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { FaExpand } from "react-icons/fa6";
import { PiDownloadSimpleThin } from "react-icons/pi";
import { useRouter } from "next/navigation";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { setApplications } from "@/store/slices/applicationsSlice";
import { useAppNoContext } from "@/context/AppNoContext";
import { ApplicationApi } from "@/src/services/ApplicationApi";
import { apiClient } from "@/src/services/apiClient";
import CreateApplicationModal from "@/components/modals/CreateApplicationModal";
import Document1 from "../information-gathering/document1/Document1";
import { BiCollapse } from "react-icons/bi";
import { PiListMagnifyingGlassBold } from "react-icons/pi";
import DashboardFilter from "./DashboardFilter";
import type { TableRowSelection } from "antd/es/table/interface";
import { useBank } from "@/context/BankContext";
import { ReportApi } from "@/src/services/ReportApi";
import { RxCross1 } from "react-icons/rx";
import GenerateReportModel from "@/components/modals/GenerateReportModel";
import NoticeReportModel from "@/components/modals/NoticeReportModel";
import { BankApi } from "@/src/services/BankApi";

type StatusType = "New" | "In Progress" | "Completed" | "On Hold" | "Rejected";

type ReportStatus = "Available" | "Not_Available";

interface DataType {
  key: string;
  record_id: string;
  appNo: string;
  cusName: string;
  state: string;
  loanAccNo: string;
  loanAmount: number;
  bankName: string;
  status: StatusType;
  report_status: ReportStatus;
  submittedAt: string;
  type_of_work?: string;
  batch_code?: string;
  assigned_date?: string | null;
  process_status?: string | null;
  borrower_name?: string | null;
  bank_name?: string | null;
  loan_account_number?: string | null;
}

const statusColorMap: Record<string, string> = {
  New: "bg-blue-500 text-white",
  "In Progress": "bg-yellow-500 text-white",
  Completed: "bg-green-500 text-white",
  "On Hold": "bg-orange-500 text-white",
  Rejected: "bg-red-500 text-white",
  Available: "bg-green-500 text-white",
  Not_Available: "bg-orange-500 text-white",
};

const statusColorMapAntd: Record<string, any> = {
  New: "blue",
  "In Progress": "gold",
  Completed: "green",
  "On Hold": "orange",
  Rejected: "red",
  Available: "green",
  Not_Available: "orange",
};

interface DashboardTableProps {
  filters?: any;
  refreshKey?: number;
  banks: any;
  searchAppNo?: string;
  searchBorrowerName?: string;
  searchLocation?: string;
  selectedStatus?: string;
  selectedSearchField?: string;
  onSearchChange?: (value: string) => void;
  onStatusChange?: (value: string) => void;
  onSearchFieldChange?: (value: string) => void;
}

interface FilterDataItem {
  name: string;
  label?: string;
  value: string | undefined;
}

const DashboardTable: React.FC<DashboardTableProps> = ({
  filters: externalFilters,
  refreshKey: externalRefreshKey,
  banks,
  searchAppNo,
  searchBorrowerName,
  searchLocation,
  selectedStatus,
  selectedSearchField,
  onSearchChange,
  onSearchFieldChange,
}) => {
  const [openResponsive, setOpenResponsive] = useState(false);
  const [openDocModal, setOpenDocModal] = useState(false);
  const [openFilterModal, setOpenFilterModal] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [localFilters, setLocalFilters] = useState<any>({});
  const [internalRefreshKey, setInternalRefreshKey] = useState(0);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectedAppNo, setSelectedAppNo] = useState<React.Key[]>([]);
  const [filterData, setFilterData] = useState<FilterDataItem[]>([]);
  const [isMobile, setIsMobile] = useState(false);
  const [confirmVisible, setConfirmVisible] = useState<boolean>(false);
  const [recordId, setRecordId] = useState<string>("");
  const [trigger, setTrigger] = useState<number>(0);

  const router = useRouter();
  const dispatch = useAppDispatch();
  const applications = useAppSelector((state) => state.applications.list);
  const { setApplicationNumber } = useAppNoContext();
  const { selectedBank } = useBank();
  const [messageApi, contextHolder] = message.useMessage();
  const [token, setToken] = useState<string>("");
  const [docModel, setDocModel] = useState<boolean>(false);
  const [modelType, setModelType] = useState<string>("");
  const [docData, setDocData] = useState<any>([]);
  const [createType, setCreateType] = useState<string>("");
  const [templatesType, setTemplatesType] = useState<any>([]);

  // Handle responsive behavior
  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkScreenSize();
    window.addEventListener("resize", checkScreenSize);

    return () => window.removeEventListener("resize", checkScreenSize);
  }, []);

  const handleFetchTemplate = async () => {
    try {
      const bankObj = banks.find((b: any) => b.client_code === selectedBank || b.client_name === selectedBank || b.client === selectedBank);
      const codeToFetch = bankObj?.client_code || selectedBank;
      let response: any = await BankApi.getSingleClientTemplate(codeToFetch);
      const templates = response?.templates ? response.templates : (Array.isArray(response) ? response : []);
      setTemplatesType(templates);
    } catch (error) {}
  };

  useEffect(() => {
    handleFetchTemplate();
  }, [selectedBank, banks]);

  useEffect(() => {
    const tokenData = localStorage.getItem("token");
    if (tokenData) {
      setToken(tokenData);
    } else {
      setToken("");
    }
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (localFilters.appNo) count++;
    if (localFilters.borrowerName) count++;
    if (localFilters.state) count++;
    if (localFilters.status) count++;
    if (localFilters.dateRange && localFilters.dateRange.length === 2) count++;
    return count;
  }, [localFilters]);

  // Utility to remove undefined/null/empty strings from request
  const sanitizeParams = (params: any) => {
    const clean: any = {};
    Object.keys(params).forEach((key) => {
      const val = params[key];
      if (val !== undefined && val !== null && val !== "") {
        clean[key] = val;
      }
    });
    return clean;
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      dispatch(setApplications([])); // clear stale data immediately so loader covers a clean table
      // Prioritize global selectedBank, then fallback to external filters
      const bankToFilter =
        selectedBank || externalFilters?.bank_name || externalFilters?.bankName;

      const params: any = {
        client_name: bankToFilter,
        loan_account_number: searchAppNo || localFilters.appNo,
        borrower_name: searchAppNo || localFilters.borrowerName,
        location: searchAppNo || localFilters.state,
        process_status:
          selectedStatus !== "All"
            ? selectedStatus
            : localFilters.status || undefined,
        ...externalFilters,
      };

      // Remove duplicates and ensure bank_name is passed
      if (bankToFilter) params.client_name = bankToFilter;

      if (localFilters.dateRange && localFilters.dateRange.length === 2) {
        params.assigned_date = localFilters.dateRange[0].format("YYYY-MM-DD");
      }

      const data: any = await ApplicationApi.getAll(
        !["all", "All Client"].includes(bankToFilter) && sanitizeParams(params),
      );
      const items = data.data || [];
      dispatch(setApplications(items));
    } catch (err) {
      console.error("Error fetching applications:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [
    dispatch,
    externalFilters,
    localFilters,
    selectedBank,
    internalRefreshKey,
    externalRefreshKey,
    trigger,
  ]);

  const tableData: DataType[] = useMemo(() => {
    let filteredApplications = applications;

    // Frontend filtering based on selected status
    if (selectedStatus && selectedStatus !== "All") {
      filteredApplications = applications.filter((app) => {
        if (selectedStatus === "Available") {
          return app.report_status === "Available";
        } else if (selectedStatus === "Not_Available") {
          return app.report_status === "Not_Available";
        }
        return true;
      });
    }

    // Frontend filtering based on search input
    if (searchAppNo && selectedSearchField && selectedSearchField !== "All") {
      const searchLower = searchAppNo.toLowerCase();
      filteredApplications = filteredApplications.filter((app) => {
        // Filter by the specific field selected in dropdown
        switch (selectedSearchField) {
          case "Application No":
            return app.application_no.toLowerCase().includes(searchLower);
          case "Loan Account No":
            return (
              app.loan_account_number?.toLowerCase().includes(searchLower) ||
              false
            );
          case "Borrower Name":
            return (
              app.borrower_name?.toLowerCase().includes(searchLower) || false
            );
          case "State":
            return (
              (app.location ?? app.state)
                ?.toLowerCase()
                .includes(searchLower) || false
            );
          case "Type of Service":
            return (
              app.type_of_work?.toLowerCase().includes(searchLower) || false
            );
          case "Batch Code":
            return app.batch_code?.toLowerCase().includes(searchLower) || false;
          default:
            return true;
        }
      });
    } else if (searchAppNo && selectedSearchField === "All") {
      // If "All" is selected, search across all fields
      const searchLower = searchAppNo.toLowerCase();
      filteredApplications = filteredApplications.filter(
        (app) =>
          app.application_no.toLowerCase().includes(searchLower) ||
          (app.borrower_name &&
            app.borrower_name.toLowerCase().includes(searchLower)) ||
          ((app.location ?? app.state) &&
            (app.location ?? app.state)!.toLowerCase().includes(searchLower)) ||
          (app.loan_account_number &&
            app.loan_account_number.toLowerCase().includes(searchLower)) ||
          (app.type_of_work &&
            app.type_of_work.toLowerCase().includes(searchLower)) ||
          (app.batch_code &&
            app.batch_code.toLowerCase().includes(searchLower)),
      );
    }

    return filteredApplications.map((app) => {
      return {
        key: app.record_id,
        record_id: app.record_id,
        appNo: app.application_no,
        cusName: app.borrower_name ?? "-",
        loanAccNo: app.loan_account_number ?? "-",
        loanAmount: app.loan_amount ?? 0,
        state: app.location ?? app.state ?? "-",
        bankName: app.bank_name ?? "-",
        status: (app.process_status as StatusType) ?? "New",
        report_status: (app.report_status as ReportStatus) ?? "Not_Available",
        submittedAt:
          app.assigned_date ?? app.created_at ?? new Date().toISOString(),
        // Raw data for edit modal
        type_of_work: app.type_of_work ?? "-",
        batch_code: app.batch_code ?? "-",
        assigned_date: app.assigned_date,
        process_status: app.process_status,
        borrower_name: app.borrower_name,
        bank_name: app.bank_name,
        loan_account_number: app.loan_account_number,
      };
    });
  }, [applications, selectedStatus, selectedSearchField, searchAppNo]);

  const handleFilter = (newFilters: any) => {
    setLocalFilters(newFilters);
    setOpenFilterModal(false);
  };

  const handleClear = () => {
    setLocalFilters({});
    // setOpenFilterModal(false);
  };

  const rowSelection: TableRowSelection<DataType> = {
    getCheckboxProps: (record: any) => ({
      disabled: record.report_status === "Not_Available",
    }),
    selectedRowKeys,
    onChange: (newSelectedRowKeys) => {
      let filterData = applications
        ?.filter((res) => newSelectedRowKeys.includes(res?.record_id))
        .map((res) => {
          return res?.application_no;
        });
      setSelectedAppNo(filterData);
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  const columns: ColumnsType<DataType> = [
    {
      title: "Application No",
      dataIndex: "appNo",
      sorter: (a, b) => a.appNo.localeCompare(b.appNo),
      fixed: "left",
    },
    {
      title: "Loan Account No",
      dataIndex: "loanAccNo",
      render: (loanAccNo: number, record: DataType) => (
        <span
          className="text-blue-700 cursor-pointer hover:underline"
          onClick={() => {
            setApplicationNumber(record.appNo.toString());
            localStorage.setItem("applicationNumber", record.appNo);
            router.push(
              `/application-details/${record.appNo}/${record.record_id}`,
            );
          }}
        >
          {loanAccNo}
        </span>
      ),
    },
    { title: "Borrower Name", dataIndex: "cusName" },
    { title: "State", dataIndex: "state" },

    {
      title: "Report Availability ",
      dataIndex: "report_status",
      render: (reportStatus: ReportStatus) => (
        <span
          className={`px-2 py-1 rounded-full text-[11px] font-semibold capitalize whitespace-nowrap ${statusColorMap[reportStatus]}`}
        >
          {reportStatus.replaceAll("_", " ")}
        </span>
      ),
    },
    { title: "Type of Service", dataIndex: "type_of_work" },
    { title: "Batch Code", dataIndex: "batch_code" },
    {
      title: "Date of Assign",
      dataIndex: "submittedAt",
      sorter: (a, b) =>
        new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime(),
      render: (date: string) => new Date(date).toLocaleDateString("en-GB"),
    },
    {
      title: "Action",
      width: 80,
      fixed: "right",
      render: (_, record) => (
        <Dropdown
          menu={{
            items: [
              {
                key: "0",
                label: (
                  <button
                    onClick={() => {
                      setApplicationNumber(record.appNo.toString());
                      localStorage.setItem("applicationNumber", record.appNo);
                      router.push(
                        `/application-details/${record.appNo}/${record.record_id}`,
                      );
                    }}
                    className="cursor-pointer font-semibold"
                  >
                    View Loan Details
                  </button>
                ),
              },

              {
                key: "1",
                label: (
                  <button
                    onClick={() => {
                      (setConfirmVisible(true), setRecordId(record.record_id));
                    }}
                    className="cursor-pointer font-semibold text-red-500"
                  >
                    Delete Application
                  </button>
                ),
              },
            ],
          }}
          trigger={["click"]}
        >
          <MoreOutlined style={{ cursor: "pointer", fontSize: 18 }} />
        </Dropdown>
      ),
    },
  ];

  const handleDownloadApi = async (setLoader: any): Promise<void> => {
    setLoader(true);
    try {
      let payload = {
        application_numbers: selectedAppNo,
      };
      const blob: Blob = await ReportApi.create(payload);

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = "Reports.xlsx";
      document.body.appendChild(link);
      link.click();

      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setSelectedAppNo([]);
      setSelectedRowKeys([]);
      handleDocCancel();
    } catch (error) {
      console.error("Download failed:", error);
      messageApi.error(String(error));
    } finally {
      setLoader(false);
    }
  };

  const handleNoticeGenerate = async (values: any, setLoader: any) => {
    setLoader(true);
    try {
      let payload = {
        template_id: values?.reportType,
        ao_code: values?.aoCode,
        application_numbers: selectedAppNo,
      };
      const blob: Blob = await ReportApi.bulkNoticeGenerate(payload);

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "bulk_notice_download.zip";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      message.success("Notice generated successfully!");
      handleDocCancel();
      setSelectedAppNo([]);
      setSelectedRowKeys([]);
    } catch (error) {
      messageApi.error(String(error));
    } finally {
      setLoader(false);
    }
  };

  const handleOpenReportModel = (type: any) => {
    if (type == "Report") {
      setDocModel(true);
      setModelType(type);
    } else if (type == "Notice") {
      setDocModel(true);
      setModelType(type);
    }
  };

  const handleDocCancel = () => {
    setDocModel(false);
    setModelType("");
  };

  const handleClearFilter = (res: any) => {
    let filterValue = filterData.filter((val) => val?.name != res?.name);
    setFilterData(filterValue);
    let editValue = {
      ...localFilters,
      appNo: localFilters.appNo === res?.value ? undefined : localFilters.appNo,
      borrowerName:
        localFilters.borrowerName === res?.value
          ? undefined
          : localFilters.borrowerName,
      state: localFilters.state === res?.value ? undefined : localFilters.state,
      status:
        localFilters.status === res?.value ? undefined : localFilters.status,
    };
    setLocalFilters(editValue);
  };

  const handleConfirmOk = async () => {
    try {
      const result: any = await ApplicationApi.deleteApplicationApi(recordId);
      if (result?.message == "Record deleted successfully") {
        setTrigger((pre: number) => pre + 1);
      }
    } catch (error) {
    } finally {
      setConfirmVisible(false);
    }
  };

  const statusOptions = [
    { label: "All", value: "All" },
    { label: "Application No", value: "Application No" },
    { label: "Loan Account No", value: "Loan Account No" },
    { label: "Borrower Name", value: "Borrower Name" },
    { label: "State", value: "State" },
    { label: "Type of Service", value: "Type of Service" },
    { label: "Batch Code", value: "Batch Code" },
  ];

  // Row selection is reset whenever the active bank or status tab changes
  useEffect(() => {
    setSelectedRowKeys([]);
    setSelectedAppNo([]);
  }, [selectedBank, selectedStatus]);

  return (
    <>
      {contextHolder}
      {/* <div className="shadow-md rounded-lg bg-white pt-2"> */}
      <div className="flex justify-between items-center px-1 pt-3 mb-2">
        <h2 className="text-lg font-semibold mb-0">
          Loan Applications {selectedBank && `for`}{" "}
          <span className="text-primary-500 font-bold">
            {selectedBank
              ? `${selectedBank == "all" ? "All Clients" : selectedBank}`
              : ""}
          </span>
        </h2>

        <div className="flex gap-3">
          <Badge count={selectedAppNo?.length} offset={[-2, 2]} size="default">
            <button
              disabled={selectedAppNo?.length == 0}
              className={`${selectedAppNo?.length == 0 ? "cursor-not-allowed opacity-30" : "cursor-pointer"} w-full h-full flex items-center text-gray-600 py-1.5 px-3 border border-blue-100 hover:bg-blue-50 rounded-md transition hover:border-blue-300`}
              onClick={() => handleOpenReportModel("Notice")}
            >
              <PiDownloadSimpleThin className="mr-1.5 text-xl" />
              Generate Notice
            </button>
          </Badge>

          <Badge count={selectedAppNo?.length} offset={[-2, 2]} size="default">
            <button
              disabled={selectedAppNo?.length == 0}
              className={`${selectedAppNo?.length == 0 ? "cursor-not-allowed opacity-30" : "cursor-pointer"} w-full h-full flex items-center text-gray-600 py-1.5 px-3 border border-blue-100 hover:bg-blue-50 rounded-md transition hover:border-blue-300`}
              onClick={() => handleOpenReportModel("Report")}
            >
              <PiDownloadSimpleThin className="mr-1.5 text-xl" />
              Download Report
            </button>
          </Badge>
        </div>
      </div>

      <div className="flex gap-2 mb-2">
        <Input
          placeholder={`Search by ${selectedSearchField == "All" ? "Application No, Loan Account No, Borrower Name, State, Type of Service or Batch Code" : selectedSearchField || ""}`}
          allowClear
          prefix={<SearchOutlined />}
          style={{ width: "100%" }}
          value={searchAppNo || ""}
          onChange={(e) => {
            onSearchChange?.(e.target.value);
          }}
        />

        <Select
          placeholder="Select Search Field"
          style={{ width: "20%" }}
          value={selectedSearchField || undefined}
          onChange={(value) => {
            onSearchFieldChange?.(value);
          }}
        >
          {statusOptions.map((item) => (
            <Select.Option key={item.value} value={item.value}>
              {item.label}
            </Select.Option>
          ))}
        </Select>
      </div>

      {/* Main Table */}
      <div className="border-gray-100 rounded-md bg-white mx-auto pt-2">
        <div className="px-1 pb-5">
          <Table<DataType>
            columns={columns}
            dataSource={tableData}
            pagination={{ defaultPageSize: 10, showSizeChanger: true, pageSizeOptions: ['10', '20', '50', '100'] }}
            bordered
            loading={loading}
            rowKey="key"
            rowSelection={rowSelection}
            scroll={{ x: "max-content" }}
          />
        </div>
      </div>
      {/* </div> */}

      {/* Filter Modal */}
      <Modal
        title="Filter Applications"
        centered
        open={openFilterModal}
        onCancel={() => setOpenFilterModal(false)}
        footer={null}
        width={700}
      >
        <DashboardFilter
          initialValues={localFilters}
          onFilter={handleFilter}
          onClear={handleClear}
          setFilterData={setFilterData}
        />
      </Modal>

      {/* Expanded Modal */}
      <Modal
        title="Loan Application List"
        centered
        open={openResponsive}
        onCancel={() => setOpenResponsive(false)}
        footer={null}
        width="80%"
      >
        <Table<DataType>
          columns={columns}
          dataSource={tableData}
          pagination={{ defaultPageSize: 10, showSizeChanger: true, pageSizeOptions: ['10', '20', '50', '100'] }}
          bordered
          rowKey="key"
          loading={loading}
        />
      </Modal>

      {/* Edit Application Modal */}
      <CreateApplicationModal
        open={editModalOpen}
        onCancel={() => {
          setEditModalOpen(false);
          setEditingRecord(null);
        }}
        isEdit={true}
        initialData={editingRecord}
        onSuccess={() => setInternalRefreshKey((prev) => prev + 1)}
        banks={banks}
        createType={createType}
      />

      {/* Documents Modal */}
      <Modal
        open={openDocModal}
        closable={false}
        footer={null}
        width="100%"
        centered
        className="!my-4 rounded-lg bg-gray-100"
        style={{ top: 20 }}
        classNames={{
          content: "!p-0 !bg-transparent !shadow-none",
        }}
      >
        <div className="sticky top-0 z-10 bg-gray-50 pb-8 pt-3 flex justify-between px-4 rounded-t-lg">
          <h2 className="text-[22px] font-bold mb-0">Documents</h2>
          <button
            onClick={() => setOpenDocModal(false)}
            className="cursor-pointer"
          >
            <BiCollapse className="bg-gray-20 text-gray-700 p-1.5 text-[28px] rounded-lg hover:ring transition ease-out duration-300" />
          </button>
        </div>
        <div className="bg-white px-2 pb-4 rounded-b-lg max-h-[85vh] overflow-y-auto">
          <Document1
            token={token}
            setDocData={setDocData}
            setTriggerReport={() => {}}
          />
        </div>
      </Modal>

      {/* Confirmation Modal */}
      <Modal
        open={confirmVisible}
        onOk={() => {
          handleConfirmOk();
        }}
        onCancel={() => setConfirmVisible(false)}
        okText="Delete"
        okType="danger"
        okButtonProps={{
          className: " hover:!text-white hover:!bg-[#ff4d4f] border-red-600",
        }}
        cancelText="Cancel"
        title="Are you sure?"
        zIndex={1100}
      >
        <p>Are you sure you want to delete this application?</p>
      </Modal>

      {modelType === "Report" && (
        <GenerateReportModel
          visible={docModel}
          onSuccess={handleDownloadApi}
          onCancel={handleDocCancel}
          type={"multiple"}
        />
      )}

      {modelType === "Notice" && (
        <NoticeReportModel
          visible={docModel}
          onSuccess={handleNoticeGenerate}
          onCancel={handleDocCancel}
          templatesType={templatesType}
          banks={banks}
          selectedBank={selectedBank}
        />
      )}
    </>
  );
};

export default DashboardTable;
