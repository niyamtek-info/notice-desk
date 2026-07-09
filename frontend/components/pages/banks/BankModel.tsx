import { Modal, Form, Input, Upload, Button, message, Tooltip } from "antd";
import React, { useEffect, useState } from "react";
import { UploadOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { RiDeleteBinLine } from "react-icons/ri";
import type { UploadProps } from "antd";
import { FiUpload } from "react-icons/fi";
import { FaRegCircleCheck } from "react-icons/fa6";
import { FaPlus, FaRegEdit } from "react-icons/fa";
import { BsBank } from "react-icons/bs";

interface BankModelProps {
  open: boolean;
  handleCancel: (resetFormOrEvent?: (() => void) | any) => void;
  onSuccess?: (values: any) => void;
  editBankData?: any;
  btnLoader: boolean;
}

interface BranchData {
  ao_name: string;
  ao_code: string;
  ao_email: string;
  signature_path: any;
  file_name: string | undefined;
}

export default function BankModel({
  open,
  handleCancel,
  onSuccess,
  editBankData,
  btnLoader,
}: BankModelProps) {
  const [form] = Form.useForm();
  const [addedBranches, setAddedBranches] = useState<BranchData[]>([]);
  const [currentBranchName, setCurrentBranchName] = useState("");
  const [currentBranchCode, setCurrentBranchCode] = useState("");
  const [currentSignature, setCurrentSignature] = useState<any>(null);
  const [bankLogoFile, setBankLogoFile] = useState<any>(null);
  const [logoFileName, setLogoFileName] = useState<string>("");
  const [deleteLogo, setDeleteLogo] = useState<boolean>(false);

  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    if (editBankData) {
      // Set form values for editing
      form.setFieldsValue({
        client_id: editBankData?.client_code.replace("NYT-", ""),
        client_name: editBankData?.client_name,
        client_type: editBankData?.client_type,
        client_description: editBankData?.description,
        client_logo: editBankData?.logo_path
          ? [{ name: "Client Logo", url: editBankData?.logo }]
          : [],
      });

      // Set bank logo file if exists
      if (editBankData.logo_path) {
        setBankLogoFile({
          name: editBankData?.file_name,
          //  url: editBankData.logo_path,
          size: "", // Assuming the logo is already a base64 string
        });
      }
    } else {
      // Reset form when not editing
      resetForm();
    }
  }, [editBankData, form]);

  const convertFileToBase64 = (
    file: any,
    callback: (base64: string) => void,
  ) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      callback(base64);
    };
    reader.readAsDataURL(file.originFileObj || file);
  };

  const handleSubmit = async (values: any) => {
    const formData = {
      ...values,
      client_id: values?.client_id?.trimEnd(),
      client_name: values?.client_name?.trimEnd(),
      client_type: values?.client_type?.trimEnd(),
      client_description: values?.client_description?.trimEnd(),
      client_logo: bankLogoFile?.base64 ? bankLogoFile?.base64 : (deleteLogo ? "" : editBankData?.logo_path),
      logo_file_name: logoFileName || undefined,
    };
    if (onSuccess) {
      onSuccess(formData);
    }
    handleCancel(resetForm);
  };

  const handleBankLogoChange = (info: any) => {
    if (info.fileList && info.fileList.length > 0) {
      const file = info.fileList[0];
      const fileName = file.name;

      const allowedTypes = ["image/jpeg", "image/jpg", "image/png"];

      if (!allowedTypes.includes(file.type)) {
        messageApi.error("Only JPG, JPEG, and PNG files are allowed");
        return;
      }
      setLogoFileName(fileName);
      convertFileToBase64(file, (base64: string) => {
        setBankLogoFile({
          ...file,
          base64: base64,
          name: fileName,
        });
      });
    } else {
      setBankLogoFile(null);
      setLogoFileName("");
    }
  };

  const handleDeleteBankLogo = () => {
    setBankLogoFile(null);
    setLogoFileName("");
    form.setFieldsValue({ client_logo: [] });
    setDeleteLogo(true)
  };

  const resetForm = () => {
    form.resetFields();
    setCurrentBranchName("");
    setCurrentBranchCode("");
    setCurrentSignature(null);
    setBankLogoFile(null);
    setLogoFileName("");
  };

  const onCancelClick = () => {
    handleCancel(resetForm);
  };

  const uploadProps: UploadProps = {
    name: "file",
    listType: "picture",
    accept: "image/*",
    maxCount: 1,
    beforeUpload: (file) => {
      const isImage = file.type.startsWith("image/");
      if (!isImage) {
        message.error("You can only upload image files!");
      }
      return false;
    },
  };


  return (
    <>
      {contextHolder}
      <Modal
        title={
          <>
            <div className="flex items-center gap-3">
              <div>
                <h2 className="text-[19px] font-bold text-gray-900">
                  {editBankData ? "Edit Client" : "Create Client"}
                </h2>
              </div>
            </div>
            {/* <div className='bg-gray-200 w-full h-[1.3px]'/> */}
          </>
        }
        open={open}
        onCancel={() => handleCancel(resetForm)}
        footer={null}
        centered
        width="45%"
        // style={{ maxWidth: 1000 }}
        className="professional-modal"
        style={{ top: 20, padding: "20px_40px_0_40px" }}
        classNames={{
          content: "!pb-[0] !shadow-none",
        }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          className="mt-4"
        >
          {/* Main Layout - Bank Details Left, Branch Section Right */}
          <div className="grid grid-cols-1 lg:grid-cols-1 gap-10 relative border border-gray-200 p-[10px_20px] rounded-[12px] mb-3">
            {/* Left Side - Bank Details */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <div>
                  <h3 className="text-[16px] font-semibold text-gray-900">
                    Client Information
                  </h3>
                </div>
              </div>

              <div className="grid grid-cols-1">

                <div className="grid grid-cols-2 gap-3">
                  <Form.Item
                    name="client_id"
                    label={
                      <span className="text-sm font-medium">Client Code</span>
                    }
                    rules={[
                      { required: true, message: "Please enter client code" },
                    ]}
                    className="mb-1"
                  >
                    <Input
                      placeholder="Enter client code"
                      className={`${editBankData?.client_code ? "!text-gray-900" : ""} placeholder:capitalize uppercase h-[40px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors`}
                      // style={{
                      //   background: 'linear-gradient(90deg, #e0f2fe 0%, #ffffff 30%)',
                      // }}
                      disabled={editBankData?.client_code}
                      prefix={
                        <span className="text-blue-500 font-semibold">NYT-</span>
                      }
                      onChange={(e) => {
                        const value = e.target.value
                          .toUpperCase()
                          .replace(/[^A-Z0-9\-/ ]/g, "")
                          .replace(/^\s+/, "");
                        form.setFieldValue("client_id", value);
                      }}
                    />
                  </Form.Item>

                  <Form.Item
                    name="client_name"
                    label={
                      <span className="text-sm font-medium">Client Name</span>
                    }
                    rules={[
                      { required: true, message: "Please enter client name" },
                    ]}
                    className="mb-1"
                  >
                    <Input
                      placeholder="Enter client name"
                      className="h-[40px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors"
                      onChange={(e) => {
                        const value = e.target.value.replace(/^\s+/, "");
                        form.setFieldValue("client_name", value);
                      }}
                    />
                  </Form.Item>
                </div>

                <Form.Item
                  name="client_type"
                  label={
                    <span className="text-sm font-medium">Client Type</span>
                  }
                  rules={[
                    { required: true, message: "Please enter client type" },
                  ]}
                  className="mb-1"
                >
                  <Input
                    placeholder="Enter client type"
                    className="h-[40px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors"
                    onChange={(e) => {
                      const value = e.target.value.replace(/^\s+/, "");
                      form.setFieldValue("client_type", value);
                    }}
                  />
                </Form.Item>

                <Form.Item
                  name="client_description"
                  label={
                    <span className="text-sm font-medium">
                      Client Description
                    </span>
                  }
                  getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
                  rules={[
                    {
                      required: false,
                      message: "Please enter client description",
                    },
                  ]}
                  className="mb-1"
                >
                  <Input.TextArea
                    placeholder="Enter client description"
                    rows={3}
                    className="rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors"
                  />
                </Form.Item>

                <Form.Item
                  name="client_logo"
                  label={
                    <span className="text-sm font-medium">Client Logo</span>
                  }
                  valuePropName="fileList"
                  getValueFromEvent={(e) =>
                    Array.isArray(e) ? e : e?.fileList
                  }
                  rules={[
                    { required: false, message: "Please upload bank logo" },
                  ]}
                  className="!mb-0 bank-logo"
                >
                  {bankLogoFile ? (
                    <div className="border-2 border-gray-200 rounded-lg p-4 bg-gray-50 w-full">
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <FaRegCircleCheck
                            color="#22c55e"
                            className="text-green-500 text-xl flex-shrink-0"
                          />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 truncate">
                              {bankLogoFile.name}
                            </p>
                            {/* <p className="text-sm text-gray-600">{(bankLogoFile.size / 1024).toFixed(2)} KB</p> */}
                          </div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">

                          <Button
                            icon={<RiDeleteBinLine size={15} />}
                            onClick={handleDeleteBankLogo}
                            className="border-2 border-dashed !bg-red-500 !text-white whitespace-nowrap"
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                      {bankLogoFile.url && (
                        <div className="mt-3">
                          <img
                            src={bankLogoFile.url}
                            alt="Bank Logo"
                            className="max-h-32 rounded-lg w-full object-contain"
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    <Upload
                      {...uploadProps}
                      showUploadList={false}
                      onChange={handleBankLogoChange}
                      className="w-full"
                    >
                      <div className="flex items-center justify-between p-3 border-2 border-dashed border-gray-300 rounded-lg w-full">
                        <div className="flex items-center gap-3 cursor-pointer">
                          <FiUpload className="text-gray-900 text-xl" />
                          <div>
                            <span className="font-medium text-gray-700">
                              Upload or Drag & Drop Bank Logo
                            </span>
                            <p className="text-sm text-gray-500">
                              PNG, JPG, or SVG
                            </p>
                          </div>
                        </div>
                        <Button
                          icon={<FiUpload />}
                          className="border-2 border-dashed !bg-primary-500 !text-white"
                        >
                          Upload
                        </Button>
                      </div>
                    </Upload>
                  )}
                </Form.Item>
              </div>
              {/* </div> */}
            </div>
            {/* Right Side - Branch Section */}
          </div>

          {/* Form Actions */}
          <Form.Item className="mb-0 mt-8">
            <div className="flex justify-end items-center pb-[20px]">
              <div className="flex gap-3">
                <Button
                  onClick={onCancelClick}
                  className="rounded-lg px-6 border-gray-300 text-gray-700 hover:border-gray-400 hover:text-gray-900 transition-colors"
                >
                  Cancel
                </Button>
                <Button
                  icon={editBankData ? <FaRegEdit /> : <BsBank />}
                  loading={btnLoader}
                  type="primary"
                  htmlType="submit"
                  className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 border-blue-600 px-8 py-2 text-white font-medium shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5"
                >
                  {editBankData ? "Update Client" : "Create Client"}
                </Button>
              </div>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
