"use client";
import {
  Card,
  Form,
  Input,
  Table,
  Button,
  Avatar,
  message,
  Dropdown,
  Select,
  Segmented,
  ConfigProvider,
  Modal,
} from "antd";
import React, { useCallback, useEffect, useState } from "react";
import { FaPlus } from "react-icons/fa";
import {
  IoIosArrowRoundBack,
  IoIosSearch,
  IoMdArrowRoundBack,
} from "react-icons/io";
import { BsBank } from "react-icons/bs";
import { MoreOutlined } from "@ant-design/icons";
import CreateTemplateModel from "./CreateTemplateModel";
import type { ColumnsType } from "antd/es/table";
import Link from "next/link";
import { BankApi } from "@/src/services/BankApi";
import dynamic from "next/dynamic";

const CreateNotice = dynamic(() => import("./CreateNotice"), { ssr: false });
interface TemplateData {
  id?: number;
  key: string;
  bank_name: string;
  bank_id: string;
  branch_id: string;
  template_code: string;
  template_name: string;
  file_path: string;
  template?: string;
  client_code?: string;
  client_name?: string;
  template_type?: string;
  html_path?: string;
  batch_code?: string | null;
  header_image_name?: string;
  footer_image_name?: string;
  html_presigned_url?: string;
}

interface BankData {
  bank_name: string;
  bank_id: string;
  branch_id: string;
  template_code: string;
  template_name: string;
  file_path: string;
}

interface BankListItem {
  code?: string;
  name: string;
  branches: any;
}

export default function Template() {
  const [form] = Form.useForm();
  const [open, setOpen] = useState(false);
  const [templates, setTemplates] = useState<TemplateData[]>([]);
  const [originalTemplates, setOriginalTemplates] = useState<TemplateData[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [bankListDrop, setBankListDrop] = useState<BankListItem[]>([]);
  const [bankListDropOrinal, setBankListDropOrinal] = useState<BankListItem[]>(
    [],
  );
  const [trigger, setTrigger] = useState<number>(0);
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(
    null,
  );
  const [editTempalteData, setEditTempalteData] = useState<any>("");
  const [activeTab, setActiveTab] = useState<string>("Notice details");
  const [confirmVisible, setConfirmVisible] = useState<boolean>(false);
  const [deleteData, setDeleteData] = useState<any>();

  const normalizeTemplateList = (response: any): TemplateData[] => {
    const rawList =
      (Array.isArray(response) && response) ||
      (Array.isArray(response?.templates) && response.templates) ||
      (Array.isArray(response?.data?.templates) && response.data.templates) ||
      (Array.isArray(response?.data) && response.data) ||
      [];

    return rawList.map((item: any) => ({
      id: item?.id,
      key: String(item?.id ?? item?.template_code ?? `${Date.now()}`),
      bank_name: item?.client_name ?? item?.bank_name ?? "",
      bank_id: item?.client_code ?? item?.bank_id ?? "",
      branch_id: item?.batch_code ?? item?.branch_id ?? "",
      template_code: item?.template_code ?? "",
      template_name:
        item?.template_name ??
        item?.template_type ??
        item?.subject ??
        "",
      file_path: item?.file_path ?? "",
      template: item?.template_type ?? item?.template ?? "",
      client_code: item?.client_code ?? item?.bank_id ?? "",
      client_name: item?.client_name ?? item?.bank_name ?? "",
      template_type: item?.template_type ?? item?.template ?? item?.template_name ?? "",
      html_path: item?.html_path ?? "",
      batch_code: item?.batch_code ?? null,
      header_image_name: item?.header_image_name ?? "",
      footer_image_name: item?.footer_image_name ?? "",
      html_presigned_url: item?.html_presigned_url ?? "",
    }));
  };

  const handleSubmit = () => { };

  const fetchTemplateList = async () => {
    try {
      let response: any = await BankApi.getTemplateList();
      const templateList = normalizeTemplateList(response);
      setTemplates(templateList);
      setOriginalTemplates(templateList);
    } catch (error) {
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplateList();
  }, [trigger]);

  const handleFetchBank = async () => {
    try {
      let response: any = await BankApi.getBankList();
      let filterBankList = response?.map((res: any) => {
        return {
          code: res.client_code,
          name: res.client_name,
          branches: res.branches,
        };
      });
      setBankListDrop(filterBankList);
      setBankListDropOrinal(filterBankList);
    } catch (error) {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleFetchBank();
  }, []);

  const handleOnchangeBank = async (value: any) => {
    const selectedBank: any = bankListDrop.find((bank) => bank.name === value);
    setLoading(true);
    if (selectedBank) {
      try {
        // const response: any = await BankApi.getBankCodeList(selectedBank?.code);
        const response = originalTemplates.filter((res: any) => (res.client_name == selectedBank.name || res.client_code == selectedBank.code))
        setTemplates(response)
        // setOriginalTemplates(normalizeTemplateList(response));
      } catch (error) {
      } finally {
        setLoading(false);
      }
    } else {
      setTrigger((pre) => pre + 1);
    }
  };

  const handleSearchFilter = useCallback(
    (value: string) => {
      // Clear existing timeout
      if (searchTimeout) {
        clearTimeout(searchTimeout);
      }

      // Set new timeout for debouncing (300ms delay)
      const timeout = setTimeout(() => {
        if (value !== "") {
          const filterList = originalTemplates.filter(
            (res) =>
              res?.bank_id.toLowerCase().includes(value.toLowerCase()) ||
              res?.bank_id.toLowerCase().includes(value.toLowerCase()),
          );
          setTemplates(filterList);
        } else {
          // Reset to original banks when search is cleared
          setTemplates(originalTemplates);
        }
      }, 300);

      setSearchTimeout(timeout);
    },
    [originalTemplates, searchTimeout],
  );


  const handleDeleteTemplate = async (record: any) => {
    const templateId = record?.id ?? record?.key;
    if (!templateId) {
      message.error("Template ID missing");
      return;
    }
    setLoading(true);
    try {
      const response = await BankApi.deleteTemplate(templateId);
      setConfirmVisible(false)
      setTrigger((pre) => pre + 1);
    } catch (error) {
      console.error("Delete failed:", error);
    } finally {
      setLoading(false);
    }
  };

  // Edit Template

  async function extractBodyContent(htmlString: any) {
    if (!htmlString?.html_presigned_url) return "";
    // Always fetch via proxy — never fetch GCS URLs directly from the browser.
    // A direct fetch of a private-bucket URL returns XML AccessDeniedException content.
    const proxyUrl = `/api/proxy?url=${encodeURIComponent(htmlString.html_presigned_url)}`;
    const response = await fetch(proxyUrl);
    if (!response.ok) {
      console.error("Failed to fetch HTML template via proxy:", response.status);
      return "";
    }
    let htmlData = await response.text();
    // Fix escaped characters
    let cleaned = htmlData
      ?.replace(/\\r\\n/g, "")
      ?.replace(/\\"/g, '"');

    // Extract ONLY body content
    const match = cleaned.match(/<body[^>]*>([\s\S]*?)<\/body>/i);

    if (match && match[1]) {
      localStorage.setItem("notice_editor_draft", match[1]);
    }

    return "";
  }

  const handleEditTemplate = async (record: any) => {
    let filterTemplateData = templates?.find((res: any) => res?.id === record?.id);
    localStorage.removeItem("notice_editor_draft");
    try {
      await extractBodyContent(filterTemplateData);
    } catch (error) {
      console.error("Failed to extract body content in handleEditTemplate:", error);
    }
    setEditTempalteData(filterTemplateData)
    setActiveTab("Create Notice")
  }

  // Filter templates based on search
  const filteredTemplates = (Array.isArray(templates) ? templates : []).filter((template) => {
    const searchTerm = form?.getFieldValue("searchbank")?.toLowerCase() || "";
    return (
      template?.template_name?.toLowerCase().includes(searchTerm) ||
      template?.bank_name?.toLowerCase().includes(searchTerm) ||
      template?.bank_id?.toLowerCase().includes(searchTerm) ||
      template?.template_code?.toLowerCase().includes(searchTerm)
    );
  });

  const columns: ColumnsType<TemplateData> = [
    {
      title: "Template Code",
      dataIndex: "template_code",
      key: "templateCode",
      align: "center",
    },
    {
      title: "Template Name",
      dataIndex: "template_name",
      key: "templateName",
      align: "center",
    },
    {
      title: "Client Code",
      dataIndex: "bank_id",
      key: "bankCode",
      align: "center",
    },
    {
      title: "Client Name",
      dataIndex: "bank_name",
      key: "bankName",
      align: "center",
      // sorter: (a, b) => a.bankName.localeCompare(b.bankName),
    },
    // {
    //   title: "Client Branch",
    //   dataIndex: "branch_id",
    //   key: "bankBranch",
    //   align: "center",
    // },

    {
      title: "Actions",
      key: "actions",
      align: "center",
      render: (_, record) => (
        <Dropdown
          menu={{
            items: [
              {
                key: "0",
                label: (
                  <button
                    onClick={() => handleEditTemplate(record)}
                    className="cursor-pointer font-semibold"
                  >
                    Edit Template
                  </button>
                ),
              },
              {
                key: "1",
                label: (
                  <button
                    onClick={() => { setConfirmVisible(true), setDeleteData(record) }}
                    className="cursor-pointer font-semibold text-red-600"
                  >
                    Delete Template
                  </button>
                ),
              },
            ],
          }}
          trigger={["click"]}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            className="text-gray-600 hover:!bg-blue-50 hover:text-gray-900"
          ></Button>
        </Dropdown>
      ),
    },
  ];

  const handleTabChange = () => {
    if (editTempalteData) {
      setEditTempalteData("")
      localStorage.removeItem("notice_editor_draft");
    }
  }


  return (
    <>
      {activeTab == "Notice details" ? (
        <div className="grid grid-cols-12 grid-rows-1 gap-4 py-4">
          <div className="col-span-12 ">
            <div className="pb-4">
              <div className="flex justify-between items-center py-4">
                <div>
                  <h1 className="text-[26px] font-bold mb-1"> Notice List</h1>
                  <p className="text-sm text-gray-500">
                    Manage and track all template applications
                  </p>
                </div>
                <Button
                  type="primary"
                  icon={<FaPlus />}
                  onClick={() => {
                    setActiveTab("Create Notice");
                    handleTabChange();
                  }}
                  className="bg-blue-600 hover:bg-blue-700 font-semibold flex items-center gap-1"
                >
                  Create Notice
                </Button>
              </div>
            </div>

            {/* Search Card */}
            <Card
              className="shadow-md rounded-lg mb-5 border-none"
              styles={{ body: { padding: "20px" } }}
            >
              <div className="flex items-start gap-4">
                {/* Search Section (70% width) */}
                <Form form={form} layout="inline" className="flex-[0.7]">
                  <Form.Item name="searchbank" className="w-full mb-0">
                    <Input
                      placeholder="Search by client name, Code..."
                      prefix={
                        <IoIosSearch size={18} className="text-primary-400" />
                      }
                      className="h-[40px] rounded-md"
                      onChange={(e) => handleSearchFilter(e.target.value)}
                    />
                  </Form.Item>
                </Form>

                {/* Bank Filter Section (30% width) */}
                <div className="flex-[0.3]">
                  <Select
                    placeholder={
                      <div className="flex items-center">
                        <BsBank className="mr-2 text-primary-500" />
                        Filter by Client
                      </div>
                    }
                    style={{ width: "100%", height: "40px" }}
                    showSearch
                    onChange={(value) => handleOnchangeBank(value)}
                    filterOption={false}
                    onSearch={(value) => {
                      if (value) {
                        // Filter the client list based on search input
                        const filtered = bankListDrop.filter((item) =>
                          item.name.toLowerCase().includes(value.toLowerCase()),
                        );
                        setBankListDrop(filtered);
                      } else {
                        setBankListDrop(bankListDropOrinal);
                      }
                    }}
                    allowClear
                  >
                    {bankListDrop.map((client) => (
                      <Select.Option key={client.code} value={client.name}>
                        <div className="flex items-center gap-2">
                          <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                            {client.code}
                          </span>
                          <span>{client.name}</span>
                        </div>
                      </Select.Option>
                    ))}
                  </Select>
                </div>
              </div>
            </Card>
          </div>

          <div className="col-span-12">
            <Card
              className="shadow-md rounded-lg border-none"
              styles={{ body: { padding: "0" } }}
            >
              <Table
                columns={columns}
                dataSource={filteredTemplates}
                pagination={{ pageSize: 10 }}
                loading={loading}
                locale={{
                  emptyText:
                    'No templates created yet. Click "Add Template" to add one.',
                }}
                className="template-table"
                bordered
              />
            </Card>
          </div>
        </div>
      ) : (
        <CreateNotice setActiveTab={setActiveTab} setTrigger={setTrigger} trigger={trigger} editTempalteData={editTempalteData} setEditTempalteData={setEditTempalteData} />
      )}

      {/* Confirmation Modal */}
      <Modal
        open={confirmVisible}
        onOk={() => handleDeleteTemplate(deleteData)}
        onCancel={() => setConfirmVisible(false)}
        okText="Yes, Delete"
        cancelText="Cancel"
        title="Are you sure?"
        okType="danger"
        okButtonProps={{
          className: " hover:!text-white hover:!bg-[#ff4d4f] border-red-600",
        }}
      >
        <p>Are you sure you want to delete this Template?</p>
      </Modal>
    </>
  );
}
