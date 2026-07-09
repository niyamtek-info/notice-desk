import { ApplicationApi } from "@/src/services/ApplicationApi";
import {
  Card,
  ConfigProvider,
  Form,
  Input,
  message,
  Segmented,
  Typography,
  Select,
  DatePicker,
  Button,
} from "antd";
import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import { BankApi } from "@/src/services/BankApi";

const { Option } = Select;

interface LoanApplicationProps {
  applicationId: string;
  recordId: string;
  setUpdate: any;
  initialData: any;
}

export default function LoanApplication({
  applicationId,
  recordId,
  setUpdate,
  initialData,
}: LoanApplicationProps) {
  const [messageApi, contextHolder] = message.useMessage();
  const [mode, setMode] = React.useState<"Read Only" | "Editable">("Read Only");
  const [isChanged, setIsChanged] = React.useState(false);
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  // const [initialData, setInitialData] = useState<any>(null);
  const [banks, setBanks] = useState<any[]>([]);
  const [locations] = useState([
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
  ]);
  const [statuses] = useState([
    "In Progress",
    "Completed",
    "Rejected",
    "On Hold",
  ]);
  const [trigger, setTrigger] = useState<number>(0);
  const isEdit = !!applicationId;

  const { Text } = Typography;

  const fetchData = async () => {
    try {
      if (recordId && initialData) {
        // const result: any = await ApplicationApi.getById(recordId);
        // setInitialData(result?.data);

        form.setFieldsValue({
          loanAccountNumber: initialData.loan_account_number,
          borrowerName: initialData.borrower_name,
          location: initialData.location,
          clientName: initialData.client_name,
          typeofwork: initialData.type_of_work,
          dateOfAssign: initialData.assigned_date
            ? dayjs(initialData.assigned_date)
            : null,
          processStatus: initialData.process_status,
        });
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    }
  };

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

  useEffect(() => {
    fetchData();
  }, [recordId, trigger, mode === "Editable", initialData]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // Map form values to backend expected nested structure
      const payload = {
        data: {
          APPLICATION: {
            ASSIGNED_AT: values.dateOfAssign?.format("YYYY-MM-DD"),
            // PROCESS_STATUS: values.processStatus || "New",
            TYPE_OF_WORK: values.typeofwork || "",
          },
          LOAN_INFO: {
            CLIENT_NAME: values.clientName,
            LOAN_ACCOUNT_NUMBER: values.loanAccountNumber,
            LOAN_REQUESTER_NAME: values.borrowerName,
          },
          PROPERTY_INFO: {
            STATE: values.location,
          },
          BATCH_CODE: values.batchcode,
        },
      };

      if (initialData?.record_id) {
        try {
          let response: any = await ApplicationApi.update(
            initialData.record_id,
            payload,
          );
          messageApi.success(
            `Application ${response?.data?.application_no} updated successfully!`,
          );
          setTrigger((pre) => pre + 1);
          setUpdate((pre: any) => pre + 1);
          setMode("Read Only");
        } catch (error) {
          messageApi.success(String(error));
        }
      }

      form.resetFields();
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

  const handleCancel = () => {
    form.resetFields();
    if (isEdit) {
      fetchData(); // Reload original data
    }
    setMode("Read Only");
  };


  return (
    <div className="bg-transparent h-full">
      {contextHolder}
      <Card
        className="shadow-sm border-gray-100 h-full"
        styles={{
          header: {
            position: "sticky",
            zIndex: 10,
            background: "white",
            top: 95,
          },
        }}
        title={
          <div className="flex justify-between items-center py-4 sticky top-0 md:top-[95px] z-10 bg-white">
            <span className="text-[20px] font-bold text-stone-800 mb-0">
              Loan Application Details
            </span>
            <div className="flex items-center gap-3">
              <ConfigProvider
                theme={{
                  components: {
                    Segmented: {
                      itemSelectedBg: "#2563EB", // Blue-600
                      itemSelectedColor: "#ffffff",
                      trackBg: "#F3F4F6", // Gray-100
                      itemColor: "#4B5563", // Gray-600
                      trackPadding: 2,
                      borderRadius: 20,
                    },
                  },
                }}
              >
                <Segmented
                  options={["Read Only", "Editable"]}
                  size="middle"
                  value={mode}
                  onChange={(value) => {
                    setMode(value as "Read Only" | "Editable");
                    // form.resetFields();
                  }}
                  className="font-medium !text-[14px]"
                />
              </ConfigProvider>
            </div>
          </div>
        }
      >
        <ConfigProvider theme={{ token: { colorTextDisabled: "#4B5563" } }}>
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              loanAccountNo: applicationId,
            }}
            disabled={mode === "Read Only"}
            onValuesChange={() => {
              if (!isChanged) setIsChanged(true);
            }}
          >
            {/* Loan Information Section */}
            <div className="mb-6 border border-gray-100 !rounded-lg">
              <Text
                strong
                className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
              >
                Loan Information
              </Text>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                <Form.Item label="Application No" name="loanAccountNo">
                  <Input
                    placeholder="Enter Loan Account No"
                    readOnly
                    className="!bg-gray-20"
                  />
                </Form.Item>
                <Form.Item
                  name="loanAccountNumber"
                  label="Loan Account No"
                  rules={
                    mode === "Editable"
                      ? [
                          {
                            required: true,
                            message: "Please enter Loan Account No",
                          },
                        ]
                      : []
                  }
                >
                  <Input
                    placeholder="Enter Account No"
                    className="h-[40px] rounded-md placeholder:capitalize uppercase"
                  />
                </Form.Item>

                <Form.Item
                  name="borrowerName"
                  label="Borrower Name"
                  rules={
                    mode === "Editable"
                      ? [
                          {
                            required: true,
                            message: "Please enter Borrower Name",
                          },
                        ]
                      : []
                  }
                >
                  <Input
                    placeholder="Enter Name"
                    className="h-[40px] rounded-md"
                  />
                </Form.Item>

                <Form.Item
                  name="location"
                  label="Location"
                  rules={
                    mode === "Editable"
                      ? [
                          {
                            required: true,
                            message: "Please select a Location",
                          },
                        ]
                      : []
                  }
                >
                  <Select
                    placeholder="Select Location"
                    className="h-[40px] custom-select-height"
                    showSearch
                    allowClear
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
                  rules={
                    mode === "Editable"
                      ? [{ required: true, message: "Please select a Client" }]
                      : [{ required: false, message: "" }]
                  }
                >
                  <Select
                    placeholder="Select Client"
                    className="h-[40px] custom-select-height"
                    showSearch
                    allowClear
                  >
                    {banks.map((client: any, index: number) => (
                      <Option
                        key={client?.client_code}
                        value={client?.client_name}
                      >
                        <div className="flex items-center gap-2">
                          <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                            {client.client_code}
                          </span>
                          <span>{client.client_name}</span>
                        </div>
                        {/* {bank?.bank_name} - {bank?.bank_code} */}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  name="dateOfAssign"
                  label="Date of Assign"
                  rules={
                    mode === "Editable"
                      ? [{ required: true, message: "Please select Date" }]
                      : []
                  }
                >
                  <DatePicker
                    className="w-full h-[40px] rounded-md"
                    format="DD-MM-YYYY"
                  />
                </Form.Item>

                <Form.Item
                  name="typeofwork"
                  label="Type of Service"
                  rules={
                    mode === "Editable"
                      ? [
                          {
                            required: false,
                            message: "Please enter Type of Service",
                          },
                        ]
                      : []
                  }
                >
                  <Input
                    placeholder="Enter Type of Service"
                    className="h-[40px] rounded-md"
                  />
                </Form.Item>

                <Form.Item
                  name="batchcode"
                  label="Batch Code"
                  rules={
                    mode === "Editable"
                      ? [
                          {
                            required: false,
                            message: "Please enter Batch Code",
                          },
                        ]
                      : []
                  }
                >
                  <Input
                    placeholder="Enter Batch Code"
                    className="h-[40px] rounded-md"
                  />
                </Form.Item>

              </div>
            </div>

            <div className="flex justify-end gap-3 mt-2">
          
              <Button
                type="primary"
                onClick={() => handleSubmit()}
                // htmlType="submit"
                loading={loading}
                disabled={mode == "Read Only"}
                className={`${mode == "Read Only" ? "opacity-75 !text-white " : ""}bg-primary-500 hover:bg-blue-600 h-[40px] px-6 rounded-md font-medium text-white`}
              >
                Save Changes
              </Button>
            </div>
          </Form>
        </ConfigProvider>
      </Card>
    </div>
  );
}
