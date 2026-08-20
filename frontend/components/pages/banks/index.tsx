"use client"
import { Card, Form, Input, Table, Button, Avatar, message, Dropdown, Select, Modal } from 'antd'
import React, { useEffect, useState, useCallback } from 'react'
import { FaFileSignature, FaPlus } from 'react-icons/fa'
import { IoIosArrowRoundBack, IoIosSearch, IoMdArrowRoundBack } from 'react-icons/io'
import { BsBank } from 'react-icons/bs'
import { MoreOutlined, EyeOutlined } from '@ant-design/icons'
import BankModel from './BankModel'
import type { ColumnsType } from 'antd/es/table'
import Link from 'next/link'
import Image from 'next/image'
import { BankApi } from '@/src/services/BankApi'
import AoModel from './AoModel'
import DeleteConformationModel from '@/components/form/DeleteConformationModel'


interface BankData {
    key: string;
    client_name: string;
    client_code: string;
    description: string;
    logo_path: string;
    aos?: BranchDetail[];
}

interface PostBankData {
    client_name: string;
    client_code: string;
    client_type: string;
    description: string;
    logo: string;
    logo_file_name: string;
}

interface BranchDetail {
    id: string;
    branch_code: string;
    branch_name: string;
    signature: string;
}

interface BankListItem {
    code?: string;
    name: string;
}

export default function BankList() {
    const [form] = Form.useForm();
    const [open, setOpen] = useState(false);
    const [aoOpen, setAoOpen] = useState(false);
    const [banks, setBanks] = useState<BankData[]>([]);
    const [originalBanks, setOriginalBanks] = useState<BankData[]>([])
    const [loading, setLoading] = useState(true);
    const [bankListDrop, setBankListDrop] = useState<BankListItem[]>([]);
    const [bankListDropOrinal, setBankListDropOrinal] = useState<BankListItem[]>([]);
    const [branchModalVisible, setBranchModalVisible] = useState(false);
    const [selectedBankBranches, setSelectedBankBranches] = useState<BranchDetail[]>([]);
    const [selectedBankName, setSelectedBankName] = useState('');
    const [editBankData, setEditBankData] = useState<any>();
    const [trigger, setTrigger] = useState<number>(0)
    const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null)
    const [btnLoader, setBtnLoader] = useState<boolean>(false);
    const [deleteModel, setDeleteModel] = useState<any>({
        open: false,
        type: "",
        value: null
    });

    const [messageApi, contextHolder] = message.useMessage();

    const handleFetchBank = async () => {
        setLoading(true)
        try {
            let response: any = await BankApi.getBankList()
            setBanks(response)
            setOriginalBanks(response)
            setLoading(false)
            let filterBankList = response?.map((res: any) => {
                return {
                    code: res.client_code,
                    name: res.client_name
                }
            })
            setBankListDrop(filterBankList)
            setBankListDropOrinal(filterBankList)

        } catch (error) {
            setLoading(false)
        }
    }

    useEffect(() => {
        handleFetchBank()
    }, [trigger])


    const handleCancel = (resetForm?: () => void) => {
        setOpen(false);
        setAoOpen(false);
        if (resetForm) {
            resetForm();
        }
    }

    const handleCreateBank = async (values: any) => {
        const newBank: PostBankData = {
            client_name: values.client_name,
            client_code: `NYT-${values.client_id}`,
            client_type: values.client_type,
            description: values.client_description || '',
            logo: values.client_logo,
            logo_file_name: values.logo_file_name,
        };
        setLoading(true)
        setBtnLoader(true)
        if (editBankData) {
            try {
                const response: any = await BankApi.putBank(editBankData?.id, newBank)
                setTrigger(pre => pre + 1)
                setOpen(false);
                messageApi.success('Client updated successfully!');
            } catch (error: any) {
                const errorMsg =
                    error?.response?.data?.detail ||
                    error?.message ||
                    "Something went wrong";
                messageApi.error(errorMsg);
            } finally {
                setLoading(false)
                setBtnLoader(false)
                form.resetFields();
            }
        } else {
            try {
                const response: any = await BankApi.postBank(newBank)
                setTrigger(pre => pre + 1)
                setOpen(false);
                messageApi.success('Client created successfully!');
            } catch (error: any) {
                const errorMsg =
                    error?.response?.data?.detail ||
                    error?.message ||
                    "Something went wrong";
                messageApi.error(errorMsg);
            } finally {
                setLoading(false)
                setBtnLoader(false)
                form.resetFields();
            }

        }

    }

    const handleCreateAO = async (values: any) => {

        setLoading(true)
        setBtnLoader(true)
        if (editBankData) {
            try {
                const response: any = await BankApi.putAO(editBankData?.id, values)
                setTrigger(pre => pre + 1)
                setAoOpen(false);
                message.success('Client created successfully!');
                setBranchModalVisible(false)
            } catch (error: any) {
                const errorMsg =
                    Array.isArray(error?.response?.data?.detail) ? "Something went wrong" : error?.response?.data?.detail ||
                        error?.message ||
                        "Something went wrong";
                messageApi.error(errorMsg);

            } finally {
                setLoading(false)
                setBtnLoader(false)
                form.resetFields();
            }
        } else {
            try {
                const response: any = await BankApi.postAO(values)
                setTrigger(pre => pre + 1)
                setAoOpen(false);
            } catch (error: any) {
                const errorMsg =
                    Array.isArray(error?.response?.data?.detail) ? "Something went wrong" : error?.response?.data?.detail ||
                        error?.message ||
                        "Something went wrong";
                messageApi.error(errorMsg);
            } finally {
                setLoading(false)
                setBtnLoader(false)
                form.resetFields();
            }

        }

    }

    const handleConfirmOk = async (deleteData: any) => {
        if (deleteData?.type === "client") {
            setLoading(true)
            try {
                const response = await BankApi.deleteBank(deleteData?.value?.id);
                setTrigger(pre => pre + 1)
                messageApi.success("Client delete successfully!");
                setDeleteModel((pre: any) => ({ ...pre, open: false, type: "", value: null }))
            } catch (error) {
                console.error("Delete failed:", error);

            } finally {
                setLoading(false)
            }
        } else if (deleteData?.type === "ao") {
            setLoading(true)
            try {
                const response = await BankApi.deleteAO(deleteData?.value?.id);
                setTrigger(pre => pre + 1)
                messageApi.success("AO delete successfully!");
                setDeleteModel((pre: any) => ({ ...pre, open: false, type: "", value: null }))
                setBranchModalVisible(false)

            } catch (error) {
                console.error("Delete failed:", error);

            } finally {
                setLoading(false)
            }
        }
    }

    // Filter banks based on search
    const filteredBanks = banks?.length > 0 ? banks?.filter(client => {
        const searchTerm = form?.getFieldValue('searchbank')?.toLowerCase() || "";
        return (
            client?.client_name?.toLowerCase().includes(searchTerm) ||
            client?.client_code?.toLowerCase().includes(searchTerm) ||
            client?.description?.toLowerCase().includes(searchTerm)
        );
    }) : [];

    const handleOnchangeBank = async (value: any) => {
        const selectedBank: any = bankListDrop.find(client => client.name === value);
        setLoading(true)
        if (selectedBank) {
            // try {
            //     // const response: any = await BankApi.getBankCodeList(selectedBank?.code)
            const response: any = originalBanks?.filter((res: any) => res?.client_code == selectedBank?.code) || []
            setBanks(response)
            setLoading(false)
            // } catch (error) {

            // } finally {
            //     setLoading(false)
            // }
        } else {
            setTrigger(pre => pre + 1)
        }
    }

    const handleSearchFilter = useCallback((value: string) => {
        // Clear existing timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Set new timeout for debouncing (300ms delay)
        const timeout = setTimeout(() => {
            if (value !== "") {
                const filterList = originalBanks.filter(res =>
                    res?.client_code.toLowerCase().includes(value.toLowerCase()) ||
                    res?.client_name.toLowerCase().includes(value.toLowerCase())
                );
                setBanks(filterList);
            } else {
                // Reset to original banks when search is cleared
                setBanks(originalBanks);
            }
        }, 300);

        setSearchTimeout(timeout);
    }, [originalBanks, searchTimeout]);



    const columns: ColumnsType<BankData> = [
        {
            title: 'Client Code',
            dataIndex: 'client_code',
            key: 'bankCd',
            align: 'center',
            width: '15%',
            className: 'font-medium',
        },
        {
            title: 'Client Name',
            dataIndex: 'client_name',
            key: 'bankName',
            align: 'center',
            width: '20%',
            sorter: (a, b) => a.client_name.localeCompare(b.client_name),
            className: 'font-medium',
            render: (text: string) => (
                <div
                    style={{
                        whiteSpace: 'normal',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                    }}
                >
                    {text}
                </div>
            ),
        },
        {
            title: 'Client Type',
            dataIndex: 'client_type',
            key: 'clientType',
            align: 'center',
            width: '15%',
            className: 'font-medium',
            render: (text: string) => (
                <div
                    style={{
                        whiteSpace: 'normal',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                    }}
                >
                    {text}
                </div>
            ),
        },
        {
            title: 'Client Logo',
            dataIndex: 'logo',
            key: 'logo',
            align: 'center',
            width: '15%',
            render: (_, record) => (
                <div className="flex justify-center w-full h-full">
                    {record.logo_path ? (
                        <Image
                            src={record.logo_path}
                            alt={`${record.client_name} logo`}
                            width={50}
                            height={50}
                            className="object-cover"
                        />
                    ) : (
                        <Avatar
                            shape="square"
                            size={50}
                            icon={<BsBank />}
                            className="!bg-blue-50 !text-primary-100"
                        />
                    )}
                </div>
            ),
        },

        {
            title: 'Description',
            dataIndex: 'description',
            key: 'description',
            align: 'center',
            width: '20%',
            ellipsis: false,
            className: 'font-medium',
            render: (text: string) => (
                <div
                    style={{
                        whiteSpace: 'normal',
                        wordBreak: 'break-word',
                        overflowWrap: 'break-word',
                    }}
                >
                    {text}
                </div>
            ),
        },
        {
            title: 'AO',
            dataIndex: 'branches',
            key: 'branches',
            align: 'center',
            width: '15%',
            render: (branches: string, record: BankData) => (
                <div className="flex flex-col items-center gap-2">
                    {record && (
                        <button
                            onClick={() => {
                                setSelectedBankBranches(record.aos || []);
                                setSelectedBankName(record.client_name);
                                setBranchModalVisible(true);
                            }}
                            className="cursor-pointer rounded-md border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-600 transition hover:bg-blue-100"
                        >
                            <EyeOutlined /> {`View AO (${record?.aos?.length})`}
                        </button>
                    )}
                </div>
            ),
        },
        {
            title: 'Actions',
            key: 'actions',
            align: 'center',
            width: '15%',
            render: (_, record) => (
                <Dropdown
                    menu={{
                        items: [
                            {
                                key: "0",
                                label: (
                                    <button
                                        onClick={() => {
                                            const editData = {
                                                ...record,
                                                _timestamp: Date.now()
                                            };
                                            setEditBankData(editData);
                                            setOpen(true);
                                        }}
                                        className="cursor-pointer font-semibold text-gray-700 transition-colors"
                                    >
                                        Edit Client
                                    </button>
                                ),
                            },
                            {
                                key: "1",
                                label: (
                                    <button
                                        onClick={() => setDeleteModel({ open: true, type: "client", value: record })}
                                        className="cursor-pointer font-semibold text-red-600 transition-colors"
                                    >
                                        Delete Client
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
                    >

                    </Button>
                </Dropdown>
            ),
        },
    ];

    return (
        <>
            {contextHolder}
            <div className="grid grid-cols-12 grid-rows-1 gap-4 py-4 ">
                <div className="col-span-12 ">
                    <div className='pb-4'>
                        <div className="flex justify-between items-center py-4">
                            <div>
                                <h1 className='text-[26px] font-bold mb-1'> Client List</h1>
                                <p className='text-sm text-gray-500'>Manage and track all client applications</p>
                            </div>
                            <div className='flex gap-2'>
                                <button
                                    onClick={() => {
                                        setAoOpen(true);
                                        setEditBankData(undefined); // Clear edit data for new client
                                    }}
                                    className="flex items-center !text-gray-50 !bg-primary-500 hover:bg-blue-800 font-medium rounded-lg text-[16px] px-4 py-2 mb-2 cursor-pointer transition-colors">
                                    <FaPlus className="mr-1.5" />
                                    Add AO
                                </button>
                                <button
                                    onClick={() => {
                                        setOpen(true);
                                        setEditBankData(undefined); // Clear edit data for new client
                                    }}
                                    className="flex items-center !text-gray-50 !bg-primary-500 hover:bg-blue-800 font-medium rounded-lg text-[16px] px-4 py-2 mb-2 cursor-pointer transition-colors">
                                    <FaPlus className="mr-1.5" />
                                    Add Client
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Search Card */}
                    <Card className="shadow-md rounded-lg mb-5 border-none" bodyStyle={{ padding: '20px' }}>
                        <div className="flex items-start gap-4">
                            {/* Search Section (70% width) */}
                            <Form
                                form={form}
                                layout="inline"
                                className="flex-[0.7]"
                            >

                                <Form.Item name="searchbank" className="w-full mb-0">
                                    <Input
                                        placeholder="Search by client name or code..."
                                        prefix={<IoIosSearch size={18} className="text-primary-400" />}
                                        className="h-[42px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                                        onChange={(e) => handleSearchFilter(e.target.value)}
                                    />
                                </Form.Item>

                            </Form>

                            {/* Bank Filter Section (30% width) */}
                            <div className="flex-[0.3]">
                                <Form form={form}>
                                    <Form.Item name="filterClient">
                                        <Select
                                            placeholder={
                                                <div className="flex items-center">
                                                    <BsBank className="mr-2 text-primary-500" />
                                                    Filter by Client
                                                </div>
                                            }
                                            style={{ width: '100%', height: '40px' }}
                                            showSearch
                                            onChange={(value) => handleOnchangeBank(value)}
                                            filterOption={false}
                                            onSearch={(value) => {
                                                if (value) {
                                                    // Filter the client list based on search input
                                                    const filtered = bankListDrop.filter((item) =>
                                                        item.name.toLowerCase().includes(value.toLowerCase())
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
                                    </Form.Item>
                                </Form>
                            </div>
                        </div>
                    </Card>
                </div >

                <div className="col-span-12">
                    <Card className="shadow-md rounded-lg border-none" bodyStyle={{ padding: '0' }}>
                        <Table
                            columns={columns}
                            dataSource={filteredBanks}
                            pagination={{ pageSize: 10 }}
                            loading={loading}
                            locale={{ emptyText: 'No clients created yet. Click "Create Client" to add one.' }}
                            className="bank-table !p-[20px]"
                            bordered
                        />
                    </Card>
                </div>
            </div >


            {/* Branch Details Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-4">
                        <Avatar
                            shape="square"
                            size={60}
                            icon={<BsBank />}
                            className="bg-primary-100 text-primary-600"
                        />
                        <div>
                            <h2 className="text-[20px] font-bold text-gray-900">AO's for {selectedBankName}</h2>
                            <p className="text-sm text-gray-600">{selectedBankBranches.length} {selectedBankBranches.length === 1 ? 'AO' : `AO's`}</p>
                        </div>
                    </div>
                }
                open={branchModalVisible}
                onCancel={() => setBranchModalVisible(false)}
                footer={null}
                centered
                width="max-content"
                style={{ top: 20, minWidth: '50%' }}
                classNames={{
                    content: ' !shadow-none'
                }}
            >
                <div className="mt-6">
                    {selectedBankBranches.length > 0 ? (
                        <Table
                            columns={[
                                {
                                    title: 'AO Code',
                                    dataIndex: 'ao_code',
                                    key: 'AOCode',
                                    align: 'center',
                                    className: 'font-medium',
                                    render: (text: string) => (
                                        <span className="px-3 py-2 bg-gray-50 rounded-lg inline-block break-words max-w-full">
                                            {text}
                                        </span>
                                    ),
                                },
                                {
                                    title: 'AO Name',
                                    dataIndex: 'ao_name',
                                    key: 'AOName',
                                    align: 'center',
                                    className: 'font-medium',
                                    render: (text: string) => (
                                        <span className="px-4 py-2 bg-white rounded-lg inline-block break-words max-w-full">
                                            {text}
                                        </span>
                                    ),
                                },
                                {
                                    title: 'AO Email',
                                    dataIndex: 'ao_email',
                                    key: 'AOEmail',
                                    align: 'center',
                                    className: 'font-medium',
                                    render: (text: string) => (
                                        <span className="px-4 py-2 bg-white rounded-lg inline-block break-words max-w-full">
                                            {text}
                                        </span>
                                    ),
                                },
                                {
                                    title: 'Signature',
                                    dataIndex: 'signature_path',
                                    key: 'signature',
                                    align: 'center',
                                    render: (signaturePath: string) => (
                                        signaturePath ? (
                                            <div className="flex justify-center">
                                                <img
                                                    src={signaturePath}
                                                    alt="Branch Signature"
                                                    className="max-h-20 rounded-lg object-cover"
                                                />
                                            </div>
                                        ) : (
                                            <div className="text-center text-gray-500 bg-gray-50 px-4 py-3 rounded-xl">
                                                <div className="text-lg mb-1 flex justify-center items-center"><FaFileSignature /></div>
                                                <span className="text-sm font-medium">No signature</span>
                                            </div>
                                        )
                                    ),
                                },
                                {
                                    title: 'Actions',
                                    key: 'actions',
                                    align: 'center',
                                    render: (_, record) => (
                                        <div className="flex items-center justify-center gap-3">
                                            <button
                                                onClick={() => {
                                                    const editData = {
                                                        ...record,
                                                        _timestamp: Date.now(),
                                                    };
                                                    setEditBankData(editData);
                                                    setAoOpen(true);
                                                }}
                                                className="cursor-pointer rounded-md border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-600 transition hover:bg-blue-100"
                                            >
                                                Edit
                                            </button>

                                            <button
                                                onClick={() => setDeleteModel({ open: true, type: "ao", value: record })}
                                                className="cursor-pointer rounded-md border border-red-200 bg-red-50 px-3 py-1 text-sm font-semibold text-red-600 transition hover:bg-red-100"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    ),
                                }
                            ]}
                            dataSource={selectedBankBranches}
                            pagination={{ pageSize: 5 }}
                            scroll={{ x: 'max-content' }}
                            className="branch-details-table"
                            rowClassName="hover:bg-gray-50 transition-colors"
                            bordered
                        />
                    ) : (
                        <div className="text-center py-12 text-gray-500 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
                            <div className="text-4xl mb-2 flex items-center justify-center"><BsBank /></div>
                            <p className="text-lg font-medium">No AO's found</p>
                            <p className="text-sm">This client currently has no AO's registered.</p>
                        </div>
                    )}
                </div>
            </Modal>

            <BankModel open={open}
                handleCancel={handleCancel}
                onSuccess={handleCreateBank}
                editBankData={editBankData}
                btnLoader={btnLoader}
            />

            <AoModel aoOpen={aoOpen}
                handleCancel={handleCancel}
                onSuccess={handleCreateAO}
                editBankData={editBankData}
                btnLoader={btnLoader}
                bankListDrop={bankListDrop} />

            {deleteModel?.open &&
                <DeleteConformationModel
                    deleteModel={deleteModel}
                    setDeleteModel={setDeleteModel}
                    handleConfirmOk={handleConfirmOk} />}

        </>
    )
}
