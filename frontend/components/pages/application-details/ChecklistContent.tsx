'use client';

import React, { useState, useEffect } from 'react';
import { Table, Tag, Tooltip, Modal, Button } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, EyeOutlined } from '@ant-design/icons';
import { useAppNoContext } from '@/context/AppNoContext';
import { ChecklistApi, ChecklistItem } from '@/src/services/ChecklistApi';

export default function ChecklistContent() {
    const { applicationNumber } = useAppNoContext();
    const [data, setData] = useState<ChecklistItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [viewRecord, setViewRecord] = useState<ChecklistItem | null>(null);
    const [modalOpen, setModalOpen] = useState(false);

    useEffect(() => {
        if (!applicationNumber) return;

        const fetchChecklist = async () => {
            setLoading(true);
            try {
                const res = await ChecklistApi.getChecklist(applicationNumber);
               

                if (Array.isArray(res)) {
                    setData(res);
                } else if ((res as any).items) {
                    setData((res as any).items);
                } else {
                    // Fallback if it returns a single object for some reason (unlikely for a checklist)
                    setData([res as unknown as ChecklistItem]);
                }

            } catch (err) {
                console.error("Error fetching checklist:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchChecklist();
    }, [applicationNumber]);

    const columns = [
        {
            title: 'Attribute',
            dataIndex: 'attribute_label',
            key: 'attribute_label',
            width: 200,
            fixed: 'left' as const,
        },
        {
            title: 'Document A Value',
            dataIndex: 'document_a_value',
            key: 'document_a_value',
            width: 150,
            render: (text: string) => text || '-',
        },
        {
            title: 'Document B Value',
            dataIndex: 'document_b_value',
            key: 'document_b_value',
            width: 150,
            render: (text: string) => text || '-',
        },
        {
            title: 'Match Status',
            dataIndex: 'match_status',
            key: 'match_status',
            width: 100,
            fixed: 'right' as const,
            render: (status: string | null | undefined) => {
                if (status === null || status === undefined || status === 'NOT_AVAILABLE') return <span className="border border-gray-500 text-[12px] bg-gray-100 text-gray-700 px-2.5 py-1 rounded-[7px] text-center mx-auto">N/A </span>;
                return status === 'MATCH' ?
                    <span className="border border-green-500 text-[12px] bg-green-100 text-green-500 px-2.5 py-1 rounded-[7px] text-center mx-auto">Matched</span> :
                    <span className="border border-red-500 text-[12px] bg-red-100 text-red-500 px-2.5 py-1 rounded-[7px] text-center mx-auto">Mismatch</span>
            },
        },
        // {
        //     title: 'Remarks',
        //     dataIndex: 'remarks',
        //     key: 'remarks',
        //     width: 150,
        //     render: (text: string) => (
        //         <Tooltip title={text}>
        //             <div className="truncate max-w-[150px]">{text || '-'}</div>
        //         </Tooltip>
        //     ),
        // },
        // {
        //     title: 'Action',
        //     key: 'action',
        //     fixed: 'right' as const,
        //     width: 80,
        //     render: (_: unknown, record: ChecklistItem) => (
        //         <Button
        //             type="text"
        //             icon={<EyeOutlined />}
        //             onClick={() => {
        //                 setViewRecord(record);
        //                 setModalOpen(true);
        //             }}
        //         />
        //     ),
        // },
    ];

    return (
        <div className="py-4 pt-0 bg-white rounded-lg shadow-sm p-4">
            <div className="flex justify-between items-center mb-5 mt-1 pt-4">
                <h1 className="text-[20px] font-bold text-stone-800 mb-0">Checklist Validation</h1>
            </div>

            <div className="bg-white rounded-lg ">
                <Table
                    loading={loading}
                    columns={columns}
                    dataSource={data}
                    rowKey="id"
                    scroll={{ x: 'max-content' }}
                    pagination={false}
                    bordered
                />
            </div>

            <Modal
                title="Checklist Item Details"
                open={modalOpen}
                onCancel={() => setModalOpen(false)}
                footer={[
                    <Button key="close" onClick={() => setModalOpen(false)}>
                        Close
                    </Button>
                ]}
                centered
            >
                {viewRecord && (
                    <Table
                        showHeader={false}
                        pagination={false}
                        dataSource={[
                            { label: 'Attribute', value: viewRecord.attribute_label },
                            { label: 'Document A Value', value: viewRecord.document_a_value },
                            { label: 'Document B Value', value: viewRecord.document_b_value },
                            { label: 'Match Status', value: viewRecord.match_status },
                            { label: 'Confidence', value: viewRecord.confidence },
                            { label: 'Remarks', value: viewRecord.remarks },
                        ]}
                        columns={[
                            { title: 'Field', dataIndex: 'label', key: 'label', width: 140, className: 'font-semibold bg-gray-50' },
                            { title: 'Value', dataIndex: 'value', key: 'value', render: val => val === true ? 'Yes' : val === false ? 'No' : (val || '-') }
                        ]}
                        rowKey="label"
                        bordered
                        size="small"
                    />
                )}
            </Modal>
        </div>
    );
}
