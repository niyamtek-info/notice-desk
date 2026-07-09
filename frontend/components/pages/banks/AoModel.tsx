import { Modal, Form, Input, Upload, Button, message, Tooltip, Select } from "antd";
import React, { useEffect, useState } from "react";
import { UploadOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { RiDeleteBinLine } from "react-icons/ri";
import type { UploadProps } from "antd";
import { FiUpload } from "react-icons/fi";
import { FaRegCircleCheck } from "react-icons/fa6";
import { FaPlus, FaRegEdit } from "react-icons/fa";
import { BsBank } from "react-icons/bs";

interface AoModelProps {
    aoOpen: boolean;
    handleCancel: (resetFormOrEvent?: (() => void) | any) => void;
    onSuccess?: (values: any) => void;
    editBankData?: any;
    btnLoader: boolean;
    bankListDrop: any;
}

interface BranchData {
    ao_name: string;
    client_code: string;
    ao_email: string;
    signature_path: any;
    file_name: string | undefined;
}

export default function AoModel({
    aoOpen,
    handleCancel,
    onSuccess,
    editBankData,
    btnLoader,
    bankListDrop
}: AoModelProps) {
    const [form] = Form.useForm();
    const [addedBranches, setAddedBranches] = useState<BranchData[]>([]);
    const [currentBranchName, setCurrentBranchName] = useState("");
    const [currentBranchCode, setCurrentBranchCode] = useState("");
    const [currentEmail, setCurrentEmail] = useState("");
    const [currentSignature, setCurrentSignature] = useState<any>(null);
    const [signatureKey, setSignatureKey] = useState(0);
    const [bankLogoFile, setBankLogoFile] = useState<any>(null);

    const [logoFileName, setLogoFileName] = useState<string>("");
    const [signFileName, setSignFileName] = useState<string>("");

    const [editChange, setEditChange] = useState<boolean>(false)

    const [messageApi, contextHolder] = message.useMessage();
    const { Option } = Select;


    useEffect(() => {
        if (editBankData) {
            // Set form values for editing
            let findClient = bankListDrop?.find((res: any) => res?.code == editBankData?.client_code)
            form.setFieldsValue({
                AOName: editBankData?.ao_name,
                clientName: {
                    value: findClient?.code,
                    label: findClient?.name,
                },
                AOEmail: editBankData?.ao_email,
            });

            setCurrentSignature(
                editBankData?.signature_path
                    ? { name: editBankData.file_name }
                    : null
            );

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
        const formData = editBankData ?
            {
                is_active: true,
                ao_name: values?.AOName?.trimEnd(),
                client_code: values?.clientName?.value?.trimEnd(),
                ao_email: values?.AOEmail?.trimEnd(),
                signature_path: currentSignature?.base64 ? currentSignature?.base64 : editBankData?.signature_path,
                file_name: signFileName ? signFileName : editBankData?.file_name,
            }
            :
            {
                aos: addedBranches.map((branch) => ({
                    ...branch,
                    signature_path:
                        branch?.signature_path?.base64 || branch?.signature_path?.url || "",
                    signature_file_name:
                        branch?.file_name || branch?.signature_path?.name || "",
                })),
            };

        // messageApi.success("Client created successfully!");
        if (onSuccess) {
            onSuccess(formData);
        }
        handleCancel(resetForm);
    };

    const handleAdd = () => {
        if (currentBranchName && currentSignature) {
            const newBranch: BranchData = {
                ao_name: currentBranchName,
                client_code: form.getFieldValue("clientName")?.value,
                ao_email: currentEmail,
                signature_path: currentSignature,
                file_name: signFileName || undefined,
            };
            setAddedBranches([...addedBranches, newBranch]);
            // messageApi.success("Branch added successfully!");
            setCurrentBranchName("");
            setCurrentBranchCode("");
            setCurrentEmail("");
            setCurrentSignature(null);
            setSignFileName("");
            setSignatureKey((prev) => prev + 1);
            form.setFieldsValue({ AOName: "" });
            form.setFieldsValue({ AOCode: "" });
            form.setFieldValue("clientName", undefined);
            form.setFieldsValue({ AOEmail: "" });
            form.setFieldsValue({ signature: "" });
        } else {
            messageApi.error("Please fill in both branch name and signature");
        }
    };

    const handleBranchNameChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        setCurrentBranchName(e.target.value);
        setEditChange(true)
    };

    const handleBranchCodeChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        setCurrentBranchCode(
            e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""),
        );
        setEditChange(true)
    };

    const handleAoEmialChange = (
        e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    ) => {
        const value = e.target.value;
        setCurrentEmail(value);
        setEditChange(true)
    };

    const handleSignatureChange = (info: any) => {
        if (info.fileList && info.fileList.length > 0) {
            const file = info.fileList[0];
            const fileName = file.name;
            const allowedTypes = ["image/jpeg", "image/jpg", "image/png"];

            if (!allowedTypes.includes(file.type)) {
                messageApi.error("Only JPG, JPEG, and PNG files are allowed");
                return;
            }
            setSignFileName(fileName);
            convertFileToBase64(file, (base64: string) => {
                setCurrentSignature({
                    ...file,
                    base64: base64,
                    name: fileName,
                });
            });
            setEditChange(true)
        } else {
            setCurrentSignature(null);
            setSignFileName("");
        }
    };


    const handleDeleteBranch = (index: number) => {
        const updatedBranches = addedBranches.filter((_, i) => i !== index);
        setAddedBranches(updatedBranches);
    };

    const resetForm = () => {
        form.resetFields();
        setAddedBranches([]);
        setCurrentBranchName("");
        setCurrentBranchCode("");
        setCurrentEmail("");
        setCurrentSignature(null);
        setSignFileName("");
        setSignatureKey(0);
        setBankLogoFile(null);
        setLogoFileName("");
        setEditChange(false)
        form.setFieldValue(" clientName", undefined);
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
                messageApi.error("You can only upload image files!");
            }
            return false;
        },
    };


    const emailRegex = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

    return (
        <>
            {contextHolder}
            <Modal
                title={
                    <>
                        <div className="flex items-center gap-3">
                            <div>
                                <h2 className="text-[19px] font-bold text-gray-900">
                                    {editBankData ? "Edit AO" : "Create AO"}
                                </h2>
                            </div>
                        </div>
                        {/* <div className='bg-gray-200 w-full h-[1.3px]'/> */}
                    </>
                }
                open={aoOpen}
                onCancel={() => handleCancel(resetForm)}
                footer={null}
                centered
                width={addedBranches?.length == 0 ? "40%" : "65%"}
                // style={{ maxWidth: 1000 }}
                zIndex={2000}
                className="professional-modal"
                style={{ top: 10, padding: "20px_40px_0_40px" }}
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
                    <div className={`grid grid-cols-1 ${addedBranches?.length == 0 ? "lg:grid-cols-1" : "lg:grid-cols-2"}
 relative border border-gray-200 p-[10px_20px] rounded-[12px] mb-3`}>
                        {/* Center Divider Line */}
                        {addedBranches?.length > 0 &&
                            <div className="absolute left-1/2 top-0 bottom-0 w-px bg-gray-200 transform -translate-x-1/2 hidden lg:block"></div>
                        }

                        {/* Left Side - Bank Details */}
                        <div className="space-y-4">
                            <div className=" rounded-xl">
                                <div className="flex items-center gap-2 mb-4">
                                    <div>
                                        <h3 className="text-[16px] font-semibold text-gray-900">
                                            AO Management
                                        </h3>
                                    </div>
                                </div>

                                <div className="space-y-4 pr-2">
                                    <div className="grid grid-cols-1">
                                        {/* <div className="grid grid-cols-2 gap-3"> */}
                                        <Form.Item
                                            name="AOName"
                                            label={
                                                <span className="text-sm font-medium">AO Name</span>
                                            }
                                            rules={[
                                                {
                                                    required: editBankData ? true : addedBranches?.length == 0,
                                                    message: "Please enter AO name",
                                                },
                                            ]}
                                            getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
                                            className="mb-1"
                                        >
                                            <Input
                                                placeholder="Enter AO name"
                                                className="h-[40px] rounded-lg border-gray-300 focus:border-green-500 focus:ring-green-500 transition-colors"
                                                value={currentBranchName}
                                                onChange={handleBranchNameChange}
                                            />
                                        </Form.Item>


                                        <Form.Item
                                            name="clientName"
                                            label="Client Name"
                                            rules={[{ required: editBankData ? true : addedBranches?.length == 0, message: 'Please select a Client' }]}
                                        >
                                            <Select
                                                placeholder="Select Client"
                                                className="h-[40px] custom-select-height"
                                                showSearch
                                                allowClear
                                                labelInValue
                                                labelRender={(props) => {
                                                    const bank = bankListDrop.find((item: any) => item.code === props.value);

                                                    if (!bank) return <span>{props.label}</span>;

                                                    return (
                                                        <div className="flex items-center gap-2">
                                                            <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                                                                {bank.code}
                                                            </span>
                                                            <span>{bank.name}</span>
                                                        </div>
                                                    );
                                                }}
                                            >
                                                {bankListDrop.map((bank: any, index: number) =>
                                                    <Option key={bank?.code} value={bank?.code} label={bank?.name}>
                                                        <div className="flex items-center gap-2">
                                                            <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                                                                {bank.code}
                                                            </span>
                                                            <span>{bank.name}</span>
                                                        </div>
                                                        {/* {bank?.bank_name} - {bank?.bank_code} */}
                                                    </Option>
                                                )}
                                            </Select>
                                        </Form.Item>
                                        {/* </div> */}

                                        <Form.Item
                                            name="AOEmail"
                                            label={
                                                <span className="text-sm font-medium">AO Email</span>
                                            }
                                            rules={[
                                                {
                                                    required: editBankData ? true : addedBranches?.length == 0,
                                                    message: "Please enter AO emial",
                                                },
                                                {
                                                    type: "email",
                                                    message: "Please enter a valid email",
                                                },
                                            ]}
                                            className="mb-1"
                                            getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
                                        >
                                            <Input
                                                placeholder="Enter AO email"
                                                className="h-[40px] rounded-lg border-gray-300 focus:border-green-500 focus:ring-green-500 transition-colors"
                                                value={currentEmail}
                                                onChange={handleAoEmialChange}
                                            />
                                        </Form.Item>

                                        <Form.Item
                                            name="signature"
                                            className="w-full bank-logo"
                                            label={
                                                <span className="text-sm font-medium">
                                                    {editBankData && <span className="text-red-500">*</span>} AO Signature
                                                </span>
                                            }
                                            rules={[
                                                {
                                                    required: editBankData ? !editBankData?.signature_path : addedBranches?.length == 0,
                                                    message: "Please upload signature",
                                                },
                                            ]}
                                        >
                                            {currentSignature ? (
                                                <div className="border-2 border-gray-200 rounded-lg p-4 bg-gray-50 w-full">
                                                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                                                        <div className="flex items-start gap-3 flex-1 min-w-0">
                                                            <FaRegCircleCheck
                                                                color="#22c55e"
                                                                className="text-xl flex-shrink-0"
                                                            />
                                                            <div className="flex-1 min-w-0">
                                                                <p className="font-medium text-gray-900 truncate">
                                                                    {currentSignature?.name}
                                                                </p>
                                                                {currentSignature?.size &&
                                                                    <p className="text-sm text-gray-600">
                                                                        {(currentSignature?.size / 1024).toFixed(2)} KB
                                                                    </p>}
                                                            </div>
                                                        </div>
                                                        <div className="flex gap-2 flex-shrink-0">
                                                            <Button
                                                                icon={<RiDeleteBinLine size={15} />}
                                                                onClick={() => {
                                                                    (setCurrentSignature(null),
                                                                        setSignFileName(""));
                                                                }}
                                                                className="border-2 border-dashed !bg-red-500 !text-white whitespace-nowrap"
                                                            >
                                                                Delete
                                                            </Button>
                                                        </div>
                                                    </div>
                                                    {currentSignature.url && (
                                                        <div className="mt-3">
                                                            <img
                                                                src={currentSignature.url}
                                                                alt="Branch Signature"
                                                                className="max-h-32 rounded-lg w-full object-contain"
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            ) : (
                                                <>
                                                    <Upload
                                                        {...uploadProps}
                                                        showUploadList={false}
                                                        onChange={handleSignatureChange}
                                                        className={`w-full`}
                                                    >
                                                        <div className="flex items-center justify-between p-3 border-2 border-dashed border-gray-300 rounded-lg w-full">
                                                            <div className="flex items-center gap-3 cursor-pointer">
                                                                <FiUpload className="text-gray-900 text-xl" />
                                                                <div>
                                                                    <span className="font-medium text-gray-700">
                                                                        Upload or Drag & Drop Branch Signature
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
                                                </>
                                            )}
                                        </Form.Item>


                                        {!editBankData && <div className=" flex justify-end">
                                            <Button
                                                disabled={
                                                    !currentBranchName ||
                                                    !emailRegex.test(currentEmail) ||
                                                    !currentSignature
                                                }
                                                onClick={handleAdd}
                                                className={`px-4  !text-white ${!currentBranchName || !currentSignature || !emailRegex.test(currentEmail) ? "!bg-primary-100" : "!bg-primary-500"}`}
                                            >
                                                <FaPlus />
                                                Add AO
                                            </Button>
                                        </div>}
                                    </div>

                                </div>
                            </div>
                        </div>
                        {/* Right Side - Branch Section */}
                        <div className="space-y-4 pl-4">
                            {/* Added Branches List */}
                            {addedBranches?.length > 0 && (
                                <div className="mt-2">
                                    <div className="flex items-center gap-2 mb-4">
                                        <h4 className="font-semibold text-gray-800 flex items-center gap-2">
                                            Added AO ({addedBranches.length})
                                        </h4>
                                    </div>
                                    <div className="space-y-3 overflow-y-auto max-h-[400px]">
                                        {addedBranches.map((branch, index) => (
                                            <div
                                                key={index}
                                                className="flex items-center justify-between p-2 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow"
                                            >
                                                <div className="flex items-start justify-between gap-2 full">
                                                    <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center bank-branch-style">
                                                        <span className="text-green-600 font-semibold text-sm">
                                                            {index + 1}
                                                        </span>
                                                    </div>
                                                    <div className="max-w-[348px] w-full">
                                                        <div className="grid grid-cols-[90px_1fr] gap-x-2 gap-y-1.5 text-sm leading-normal">
                                                            <div className="font-semibold text-gray-950">AO Name:</div>
                                                            <div className="text-gray-600 break-all whitespace-normal font-medium">
                                                                {branch.ao_name}
                                                            </div>

                                                            <div className="font-semibold text-gray-950">Client:</div>
                                                            <div className="text-gray-600 break-all whitespace-normal font-medium">
                                                                {(() => {
                                                                    const client = bankListDrop?.find(
                                                                        (res: any) => res?.code === branch?.client_code
                                                                    );
                                                                    return client ? `${client.code} - ${client.name}` : "-";
                                                                })()}
                                                            </div>

                                                            <div className="font-semibold text-gray-950">AO Email:</div>
                                                            <div className="text-gray-600 break-all whitespace-normal font-medium">
                                                                {branch.ao_email}
                                                            </div>

                                                            <div className="font-semibold text-gray-950">Signature:</div>
                                                            <div className="text-gray-600 break-all whitespace-normal font-medium">
                                                                <Tooltip
                                                                    title={
                                                                        branch.signature_path?.name?.length > 40
                                                                            ? branch.signature_path?.name
                                                                            : null
                                                                    }
                                                                >
                                                                    <span>
                                                                        {branch.signature_path?.name?.length > 40
                                                                            ? branch.signature_path?.name.slice(
                                                                                0,
                                                                                40,
                                                                            ) + "..."
                                                                            : branch.signature_path?.name}
                                                                    </span>
                                                                </Tooltip>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <button
                                                        type="button"
                                                        onClick={() => handleDeleteBranch(index)}
                                                        className="p-2 rounded-2xl bg-red-100 hover:bg-red-200 !text-red-500 cursor-pointer whitespace-nowrap"
                                                        title="Delete branch"
                                                    >
                                                        <RiDeleteBinLine size={15} />
                                                    </button>
                                                </div>

                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
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
                                    disabled={(editBankData ? !editChange : addedBranches?.length == 0)}
                                    icon={editBankData ? <FaRegEdit /> : <BsBank />}
                                    loading={btnLoader}
                                    type="primary"
                                    htmlType="submit"
                                    className={`${(editBankData ? !editChange : addedBranches?.length == 0) ? "opacity-65" : ""} rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 border-blue-600 px-8 py-2 !text-white font-medium shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5`}
                                >
                                    {editBankData ? "Update AO" : "Create AO"}
                                </Button>
                            </div>
                        </div>
                    </Form.Item>
                </Form>
            </Modal>

        </>
    );
}
