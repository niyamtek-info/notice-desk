'use client';

import React from 'react';
import { Form, Input, Select, DatePicker, Button } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';

const { Option } = Select;
const { RangePicker } = DatePicker;

interface DashboardFilterProps {
    onFilter: (values: any) => void;
    onClear: () => void;
    initialValues?: any;
    setFilterData: (values: any) => void
}

const DashboardFilter: React.FC<DashboardFilterProps> = ({ onFilter, onClear, initialValues, setFilterData }) => {
    const [form] = Form.useForm();

    React.useEffect(() => {
        if (initialValues) {
            form.setFieldsValue(initialValues);
        }
    }, [initialValues, form]);


    const fieldLabels: Record<string, string> = {
        "appNo": "Loan Account No.",
        "borrowerName": "Borrower Name",
        "location": "Location",
        "status": "Status"
    };

    const handleFinish = (values: any) => {
        onFilter(values);
        const formatted = Object.keys(values).map((key) => ({
            name: key,
            label: fieldLabels[key],
            value: values[key],
        })).filter(val => val?.value != undefined);
        setFilterData(formatted)
    };

    const handleClear = () => {
        form.resetFields();
        onClear();
    };

    const locations = ["Chennai", "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Kolkata", "Pune", "Ahmedabad"];
    const banks = ["SBI", "HDFC", "ICICI", "Axis", "Kotak Mahindra", "Bank of Baroda", "Punjab National Bank", "Canara Bank"];
    const statuses = ["Completed", "In Progress", "Rejected", "On Hold"];

    return (
        <div className="p-2">
            <Form
                form={form}
                layout="vertical"
                onFinish={handleFinish}
                className="space-y-4"
            >
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-x-4 gap-y-2">
                    <Form.Item name="appNo" label="Loan Account No." className="mb-0">
                        <Input placeholder="Search No" className="h-[38px] rounded-md" />
                    </Form.Item>

                    <Form.Item name="borrowerName" label="Borrower Name" className="mb-0">
                        <Input placeholder="Enter Name" className="h-[38px] rounded-md" />
                    </Form.Item>

                    <Form.Item name="location" label="Location" className="mb-0">
                        <Select
                            placeholder="Select Location"
                            allowClear
                            showSearch
                            className="h-[38px] rounded-md w-full items-center"
                            filterOption={(input, option) =>
                                (option?.children as unknown as string).toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            {locations.map(loc => <Option key={loc} value={loc}>{loc}</Option>)}
                        </Select>
                    </Form.Item>

                    <Form.Item name="status" label="Status" className="mb-0">
                        <Select
                            placeholder="Status"
                            allowClear
                            showSearch
                            className="h-[38px] rounded-md flex-grow items-center"
                            filterOption={(input, option) =>
                                (option?.children as unknown as string).toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            {statuses.map(status => <Option key={status} value={status}>{status}</Option>)}
                        </Select>
                    </Form.Item>

                    <Form.Item name="dateRange" label="Date range" className="mb-0 col-span-2">
                        <RangePicker className="h-[38px] rounded-md w-full" format="DD-MM-YYYY" />
                    </Form.Item>


                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 mt-4">
                    <Button
                        onClick={handleClear}
                        icon={<ReloadOutlined />}
                        className="h-[40px] px-6 rounded-md flex items-center justify-center border-gray-200 text-gray-600 hover:text-primary-500"
                    >
                        Clear
                    </Button>
                    <Button
                        type="primary"
                        htmlType="submit"
                        icon={<SearchOutlined />}
                        className="h-[40px] px-8 rounded-md flex items-center justify-center bg-primary-500 hover:bg-blue-600 border-none text-white font-medium"
                    >
                        Apply Filters
                    </Button>
                </div>
            </Form>

            <style>{`
                .ant-form-item-label > label {
                    font-size: 13px !important;
                    color: #6b7280 !important;
                    height: auto !important;
                    margin-bottom: 4px !important;
                }
                .ant-select-selector {
                    height: 49px !important;
                    display: flex !important;
                    align-items: center !important;
                }
            `}</style>
        </div>
    );
};

export default DashboardFilter;