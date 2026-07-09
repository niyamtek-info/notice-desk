import { Button, DatePicker, Form, Input, message, Modal } from 'antd'
import React, { useEffect, useState } from 'react'
import { Segmented } from 'antd';
import { ChecklistApi } from '@/src/services/ChecklistApi';
import dayjs, { Dayjs } from 'dayjs';
import { FaArrowRightLong, FaArrowLeftLong } from 'react-icons/fa6';

interface CheckListModalProps {
    open: boolean;
    onCancel: () => void;
    onSuccess?: () => void;
    isEdit?: boolean;
    initialData?: any;
}

const CheckListEditModel: React.FC<CheckListModalProps> = (props) => {
    const [form] = Form.useForm();
    const [messageApi, contextHolder] = message.useMessage();
    const [valueSegment, setValueSegment] = useState<string>('Map')
    const [loading, setLoading] = useState(false);

    const fieldA = props?.initialData?.document_a === "Sanction Letter"
        ? `sanctionLetter${props?.initialData?.attribute_code}`
        : `MODT${props?.initialData?.attribute_code}`;

    const fieldB = props?.initialData?.document_a === "Sanction Letter"
        ? `loanAgreement${props?.initialData?.attribute_code}`
        : `saleDeed${props?.initialData?.attribute_code}`;

    const handleCopyAtoB = () => {
        const valA = form.getFieldValue(fieldA);
        form.setFieldsValue({ [fieldB]: valA });
    };

    const handleCopyBtoA = () => {
        const valB = form.getFieldValue(fieldB);
        form.setFieldsValue({ [fieldA]: valB });
    };

    const parseToDayjs = (
        date: string | null | undefined
    ): Dayjs | null => {
        if (!date) return null;

        // Try ISO first
        const iso = dayjs(date, "DD/MM/YYYY");
        if (iso.isValid()) return iso;

        // Try DD/MM/YYYY
        const slashFormat = dayjs(date, "DD/MM/YYYY", true);
        if (slashFormat.isValid()) return slashFormat;

        // Try DD-MM-YYYY
        const dashFormat = dayjs(date, "DD-MM-YYYY", true);
        if (dashFormat.isValid()) return dashFormat;

        return null;
    };


    useEffect(() => {
        if (props?.open) {
            if (props?.initialData && props.initialData.attribute_label) {

                const checkDateValidA: boolean = props.initialData?.document_a_value && props.initialData?.attribute_code == "date";
                const checkDateValidB: boolean = props.initialData?.document_b_value && props.initialData?.attribute_code == "date";

                const dateValueA: any = parseToDayjs(props.initialData?.document_a_value);
                const dateValueB: any = parseToDayjs(props.initialData?.document_b_value);


                form.setFieldsValue({
                    [`sanctionLetter${props.initialData.attribute_code}`]: checkDateValidA ? dateValueA : props.initialData?.document_a_value,
                    [`loanAgreement${props.initialData.attribute_code}`]: checkDateValidB ? dateValueB : props.initialData?.document_b_value,
                    [`MODT${props?.initialData?.attribute_code}`]: checkDateValidA ? dateValueA : props.initialData?.document_a_value,
                    [`saleDeed${props?.initialData?.attribute_code}`]: checkDateValidB ? dateValueB : props.initialData?.document_b_value,
                    // status: props.initialData?.match_status === 'MATCH' ? 'Match' : 'Mismatch'
                });

                setValueSegment(props.initialData?.match_status === 'MATCH' ? 'Match' : 'Mismatch');
            } else {
                form.resetFields();
                setValueSegment('Match');
            }
        }
    }, [props.open, props.initialData, form]);


    const handleCancel = () => {
        form.resetFields();
        props.onCancel();
    };


    const handleSubmit = async (values: any) => {

        try {
            setLoading(true);
            // Handle form submission here

            let payload = {
                document_a_value: values?.sanctionLetterdate ? dayjs(values?.sanctionLetterdate) :
                    props?.initialData?.document_a == "Sanction Letter" ? values?.[`sanctionLetter${props?.initialData?.attribute_code}`]
                        : values?.[`MODT${props?.initialData?.attribute_code}`] || "",

                document_b_value: values?.loanAgreementdate ? dayjs(values?.loanAgreementdate) :
                    props?.initialData?.document_a == "Sanction Letter" ? values?.[`loanAgreement${props?.initialData?.attribute_code}`]
                        : values?.[`saleDeed${props?.initialData?.attribute_code}`] || ""
            }

            // Call onSuccess callback if provided
            if (props.onSuccess) {
                props.onSuccess();
            }

            form.resetFields();
            props.onCancel();
            messageApi.success('CheckList updated successfully');
        } catch (error) {
            messageApi.error('Failed to update');
        } finally {
            setLoading(false);
        }
    };


    return (
        <>
            <Modal
                title={<div className="text-[19px] font-bold mb-4 text-gray-900">Edit</div>}
                open={props.open}
                onCancel={handleCancel}
                footer={null}
                centered
                width={650}
                className="rounded-lg"
                styles={{
                    body: { paddingBottom: 8, paddingTop: 0 }
                }}
            >
                {contextHolder}
                <Form
                    form={form}
                    layout="vertical"
                    className="mt-4"
                    requiredMark={true}
                    onFinish={handleSubmit}
                >
                    <div className="flex items-center gap-4 w-full mb-6">
                        <div className="flex-1">
                            <Form.Item
                                name={fieldA}
                                label={props?.initialData?.document_a == "Sanction Letter" ? `Sanction Letter ${props?.initialData?.attribute_label}` : `MODT ${props?.initialData?.attribute_label}`}
                                rules={[{ required: true, message: `Please enter ${props?.initialData?.document_a == "Sanction Letter" ? "Sanction Letter" : "MODT"} ${props?.initialData?.attribute_label}.` }]}
                                style={{ marginBottom: 0 }}
                            >
                                {props?.initialData?.attribute_label == "Date" ?
                                    <DatePicker className="w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                                    :
                                    <Input
                                        placeholder={props?.initialData?.document_a == "Sanction Letter" ? `Enter Sanction Letter ${props?.initialData?.attribute_label}` : `Enter MODT ${props?.initialData?.attribute_label}`}
                                        className="h-[40px] rounded-md"
                                    />
                                }
                            </Form.Item>
                        </div>

                        <div className="flex flex-col gap-2 pt-6">
                            <button
                                type="button"
                                onClick={handleCopyAtoB}
                                className="flex items-center justify-center bg-gray-50 border border-gray-200 hover:border-blue-400 hover:bg-blue-400 hover:text-white transition-all duration-200 rounded-[7px] shadow-sm cursor-pointer"
                                style={{
                                    height: "28px",
                                    width: "36px",
                                    padding: 0,
                                }}
                                title="Copy Left to Right"
                            >
                                <FaArrowRightLong className="text-[13px]" />
                            </button>
                            <button
                                type="button"
                                onClick={handleCopyBtoA}
                                className="flex items-center justify-center bg-gray-50 border border-gray-200 hover:border-blue-400 hover:bg-blue-400 hover:text-white transition-all duration-200 rounded-md shadow-sm cursor-pointer"
                                style={{
                                    height: "28px",
                                    width: "36px",
                                    padding: 0,
                                }}
                                title="Copy Right to Left"
                            >
                                <FaArrowLeftLong className="text-[13px]" />
                            </button>
                        </div>

                        <div className="flex-1">
                            <Form.Item
                                name={fieldB}
                                label={props?.initialData?.document_a == "Sanction Letter" ? `Loan Agreement ${props?.initialData?.attribute_label}` : `Sale Deed ${props?.initialData?.attribute_label}`}
                                rules={[{ required: true, message: `Please enter ${props?.initialData?.document_a == "Sanction Letter" ? "Loan Agreement" : "Sale Deed"} ${props?.initialData?.attribute_label}.` }]}
                                style={{ marginBottom: 0 }}
                            >
                                {props?.initialData?.attribute_label == "Date" ?
                                    <DatePicker className="w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                                    :
                                    <Input
                                        placeholder={props?.initialData?.document_a == "Sanction Letter" ? `Enter Loan Agreement ${props?.initialData?.attribute_label}` : `Enter Sale Deed ${props?.initialData?.attribute_label}`}
                                        className="h-[40px] rounded-md"
                                    />
                                }
                            </Form.Item>
                        </div>
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
                            Update Checklist
                        </Button>
                    </div>
                </Form>
            </Modal>
        </>
    );
};

export default CheckListEditModel;
