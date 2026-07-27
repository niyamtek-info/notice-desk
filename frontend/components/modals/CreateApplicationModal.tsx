import React, { useState } from "react";
import {
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  message,
  Tabs,
  Upload,
} from "antd";
import { RiUploadCloud2Line } from "react-icons/ri";
import { FaRegCheckCircle } from "react-icons/fa";
import { ApplicationApi } from "@/src/services/ApplicationApi";
import dayjs from "dayjs";
import { ReportApi } from "@/src/services/ReportApi";

const { Dragger } = Upload;
const { TabPane } = Tabs;
const { Option } = Select;

interface CreateApplicationModalProps {
  open: boolean;
  onCancel: () => void;
  onSuccess?: () => void;
  isEdit?: boolean;
  initialData?: any;
  banks: any;
  createType: string;
}

const CreateApplicationModal: React.FC<CreateApplicationModalProps> = ({
  open,
  onCancel,
  onSuccess,
  isEdit = false,
  initialData,
  banks,
  createType
}) => {
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Fill form fields when initialData changes or modal opens

  React.useEffect(() => {
    if (open) {
      if (isEdit && initialData) {
        form.setFieldsValue({
          loanAccountNumber: initialData.loan_account_number,
          borrowerName: initialData.borrower_name,
          state: initialData.state,
          clientName: initialData.client_name,
          typeofwork: initialData.type_of_work,
          batchcode: initialData.batch_code,
          dateOfAssign: initialData.assigned_date
            ? dayjs(initialData.assigned_date)
            : null,
          processStatus: initialData.process_status,
        });
      } else {
        form.resetFields();
      }
    }
  }, [open, isEdit, initialData, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // Map form values to backend expected nested structure
      const payload = {

        data: {
          ASSIGNED_AT: values.dateOfAssign?.format("YYYY-MM-DD"),
          TYPE_OF_WORK: values.typeofwork?.trimEnd() || "",
          CLIENT_NAME: values.clientName?.trimEnd(),
          LOAN_ACCOUNT_NUMBER: values.loanAccountNumber?.trimEnd()?.toUpperCase(),
          LOAN_REQUESTER_NAME: values.borrowerName?.trimEnd(),
          STATE: values.state?.trimEnd(),
          BATCH_CODE: values.batchcode?.trimEnd(),
        },
      };

      if (isEdit && initialData?.record_id) {
        let response: any = await ApplicationApi.update(
          initialData.record_id,
          payload,
        );
        messageApi.success(
          `Application ${response?.data?.application_no} updated successfully!`,
        );
      } else {
        console.log(payload, 'payload23423')

        let response: any = await ApplicationApi.create(payload);
        messageApi.success(
          `Application ${response?.data?.application_no} created successfully!`,
        );
      }

      form.resetFields();
      if (onSuccess) onSuccess();
      onCancel();
    } catch (error: any) {
      console.error("Operation failed:", error);
      let errorMessage = `Failed to ${isEdit ? "update" : "create"} application`;

      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === "string") {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // Handle validation errors array
          errorMessage = detail
            .map((err: any) =>
              typeof err === "string"
                ? err
                : `${err.loc?.join(".")}: ${err.msg}`,
            )
            .join("; ");
        } else if (typeof detail === "object") {
          // Handle object error details
          errorMessage = JSON.stringify(detail);
        }
      }

      messageApi.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkUpload = async () => {
    if (!uploadedFile) {
      messageApi.error("Please select a file first");
      return;
    }
    try {
      setLoading(true);
      const blob: Blob = await ApplicationApi.upload(uploadedFile);
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = "Reports.xlsx";
      document.body.appendChild(link);
      link.click();

      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      messageApi.success(
        "Bulk documents processed and downloaded successfully.",
      );
      setUploadedFile(null);
      if (onSuccess) onSuccess();
      onCancel();
    } catch (error: any) {
      console.error("Bulk upload failed:", error);
      let errorMessage = "Failed to process bulk upload";

      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (typeof detail === "string") {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          // Handle validation errors array
          errorMessage = detail
            .map((err: any) =>
              typeof err === "string"
                ? err
                : `${err.loc?.join(".")}: ${err.msg}`,
            )
            .join("; ");
        } else if (typeof detail === "object") {
          // Handle object error details
          errorMessage = JSON.stringify(detail);
        }
      }

      messageApi.error("Unable to insert record");
      onCancel();
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setUploadedFile(null);
    onCancel();
  };

  const locations = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
  ];
  const statuses = ["In Progress", "Completed", "Rejected", "On Hold"];

  const ManualEntryForm = () => (
    <Form
      form={form}
      layout="vertical"
      className="mt-4"
      requiredMark={true}
      onFinish={handleSubmit}
    >
      <div
        className={`grid grid-cols-1 md:grid-cols-2 gap-x-8 ${isEdit ? "mt-0" : "mt-7"}`}
      >
        <Form.Item
          name="loanAccountNumber"
          label="Loan Account No"
          rules={[{ required: true, message: "Please enter Loan Account No" }]}
          getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
        >
          <Input
            placeholder="Enter Account No"
            className="h-[40px] rounded-md placeholder:capitalize uppercase"
          />
        </Form.Item>

        <Form.Item
          name="borrowerName"
          label="Borrower Name"
          rules={[{ required: true, message: "Please enter Borrower Name" }]}
          getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
        >
          <Input placeholder="Enter Name" className="h-[40px] rounded-md" />
        </Form.Item>

        <Form.Item
          name="state"
          label="State"
          rules={[{ required: true, message: "Please select a State" }]}
        >
          <Select
            placeholder="Select State"
            className="h-[40px] custom-select-height"
            showSearch
            filterOption={(input, option) =>
              (option?.children as unknown as string)
                .toLowerCase()
                .includes(input.toLowerCase())
            }
          >
            {locations.map((loc) => (
              <Option key={loc} value={loc}>
                {loc}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="clientName"
          label="Client Name"
          rules={[{ required: true, message: "Please select a Client" }]}
        >
          <Select
            placeholder="Select Client"
            className="h-[40px] custom-select-height"
            showSearch
            allowClear
          >
            {banks?.filter((res: any) => res?.client_code !== "all").map((client: any, index: number) => (
              <Option key={client?.client_code} value={client?.client_name}>
                <div className="flex items-center gap-2">
                  <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                    {client.client_code}
                  </span>
                  <span>{client.client_name}</span>
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>


        <Form.Item
          name="dateOfAssign"
          label="Date of Assign"
          rules={[{ required: false, message: "Please select Date" }]}
        >
          <DatePicker className="w-full h-10 rounded-md" format="DD-MM-YYYY" />
        </Form.Item>

        <Form.Item
          name="typeofwork"
          label="Type of Service"
          rules={[{ required: false, message: "Please enter Type of Service" }]}
          getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
        >
          <Input
            placeholder="Enter Type of Service"
            className="h-10 rounded-md"
          />
        </Form.Item>

        <Form.Item
          name="batchcode"
          label="Batch Code"
          rules={[{ required: false, message: "Please enter Batch Code" }]}
          getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
        >
          <Input placeholder="Enter Batch Code" className="h-10 rounded-md" />
        </Form.Item>

        {isEdit && (
          <Form.Item
            name="processStatus"
            label="Process Status"
            rules={[{ required: true, message: "Please select Status" }]}
          >
            <Select
              placeholder="Select Status"
              className="h-[40px] custom-select-height"
              showSearch
              filterOption={(input, option) =>
                (option?.children as unknown as string)
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
            >
              {statuses.map((status) => (
                <Option key={status} value={status}>
                  {status}
                </Option>
              ))}
            </Select>
          </Form.Item>
        )}
      </div>

      <div className="flex justify-end gap-3 mt-2">
        <Button onClick={handleCancel} className="h-[40px] px-6 rounded-md">
          Cancel
        </Button>

        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          className="bg-primary-500 hover:bg-blue-600 h-[40px] px-6 rounded-md font-medium text-white"
        >
          {isEdit ? "Save Changes" : "Create Application"}
        </Button>
      </div>
    </Form>
  );

  const handleDownloadTemplate = async (): Promise<void> => {
    try {
      const blob: Blob = await ReportApi.downloadTemplate();

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = "Template.xlsx";
      document.body.appendChild(link);
      link.click();

      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
    }
  };

  return (
    <Modal
      title={
        <div className="text-[19px] font-bold mb-4 text-gray-900">
          {isEdit ? "Edit Application" : "Create New Application"}
        </div>
      }
      open={open}
      onCancel={handleCancel}
      footer={null}
      centered
      width={750}
      className="rounded-lg"
      styles={{
        body: { paddingBottom: 8, paddingTop: 0 },
      }}
    >
      {contextHolder}

      {isEdit ? (
        <div className="pb-4 pt-2">
          <ManualEntryForm />
        </div>
      ) : (
        <>
          {createType == "manual" &&
            <ManualEntryForm />}
          {createType == "bulk" &&
            <div className="pb-0 pt-6">
              <div className="mb-2">
                <h3 className="text-md font-medium text-gray-700 mb-2">
                  Upload File
                </h3>
              </div>

              <Dragger
                name="file"
                accept=".xlsx, .xls, .csv"
                multiple={false}
                action={undefined}
                beforeUpload={(file) => {
                  const isExcelOrCsv =
                    file.type ===
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
                    file.type === "text/csv" ||
                    file.name.endsWith(".xlsx") ||
                    file.name.endsWith(".csv");
                  if (!isExcelOrCsv) {
                    messageApi.error("You can only upload Excel or CSV files!");
                    return Upload.LIST_IGNORE;
                  }
                  setUploadedFile(file);
                  return false; // Don't auto upload
                }}
                onRemove={() => setUploadedFile(null)}
                showUploadList={false}
                className="bg-gray-50 border-gray-200 rounded-xl hover:border-primary-500 transition-colors"
              >
                <div className="py-10">
                  {uploadedFile ? (
                    <>
                      <p className="mb-4 flex justify-center">
                        <FaRegCheckCircle className="text-green-500 text-[60px]" />
                      </p>
                      <p className="text-lg font-medium text-gray-700 mb-1">
                        {uploadedFile.name}
                      </p>
                      <p className="text-sm text-green-600">
                        File selected and ready to process
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="mb-4 flex justify-center">
                        <RiUploadCloud2Line className="text-primary-800 text-[60px]" />
                      </p>
                      <p className="text-[17px] font-medium text-gray-700 mb-1">
                        Click or drag file to this area to upload
                      </p>
                      <p className="text-[15px] text-gray-400">
                        Support for specialized Excel or CSV templates only.
                      </p>
                    </>
                  )}
                </div>
              </Dragger>

              <div className="flex justify-end gap-3 mt-5 pt-2">
                <Button
                  onClick={handleCancel}
                  className="h-[40px] px-6 rounded-md"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleDownloadTemplate}
                  className="h-[40px] px-6 rounded-md"
                >
                  Download Template
                </Button>
                <Button
                  type="primary"
                  onClick={handleBulkUpload}
                  loading={loading}
                  className="bg-primary-500 hover:bg-blue-600 h-[40px] px-6 rounded-md font-medium text-white"
                >
                  Process & Create
                </Button>
              </div>
            </div>
          }
        </>
      )}
      <style jsx global>{`
        .custom-select-height .ant-select-selector {
          height: 40px !important;
          display: flex;
          align-items: center;
        }
        .custom-tabs .ant-tabs-nav {
          margin-bottom: 0 !important;
        }
        .custom-tabs .ant-tabs-tab {
          margin-right: 10px !important;
          padding: 10px 0 !important;
        }
        .custom-tabs .ant-tabs-tab-btn {
          font-size: 15px !important;
          font-weight: 500 !important;
        }
      `}</style>
    </Modal>
  );
};

export default CreateApplicationModal;
