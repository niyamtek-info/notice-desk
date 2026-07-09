import React from 'react'
import { Table, Tag, Button, Space, Typography } from 'antd'
import { EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'

const { Text } = Typography

interface NoticeData {
  key: string
  noticeName: string
  noticeType: string
  status: 'Active' | 'Inactive' | 'Pending' | 'Completed'
}

const NoticeListTable: React.FC = () => {
  const dataSource: NoticeData[] = [
    {
      key: '1',
      noticeName: 'Loan Approval Notice',
      noticeType: 'Approval',
      status: 'Active'
    },
    {
      key: '2',
      noticeName: 'Document Verification Required',
      noticeType: 'Verification',
      status: 'Pending'
    },
    {
      key: '3',
      noticeName: 'Payment Due Reminder',
      noticeType: 'Reminder',
      status: 'Active'
    },
    {
      key: '4',
      noticeName: 'Account Closure Notice',
      noticeType: 'Closure',
      status: 'Inactive'
    },
    {
      key: '5',
      noticeName: 'Interest Rate Change',
      noticeType: 'Information',
      status: 'Completed'
    }
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Active': return 'green'
      case 'Pending': return 'orange'
      case 'Inactive': return 'red'
      case 'Completed': return 'blue'
      default: return 'default'
    }
  }

  const columns = [
    {
      title: 'Notice Name',
      dataIndex: 'noticeName',
      key: 'noticeName',
      render: (text: string) => <Text style={{ fontSize: '14px', fontWeight: 'normal' }}>{text}</Text>
    },
    {
      title: 'Notice Type',
      dataIndex: 'noticeType',
      key: 'noticeType',
      render: (text: string) => <Text style={{ fontSize: '14px', fontWeight: 'normal' }}>{text}</Text>
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)} style={{ fontSize: '14px', fontWeight: 'normal' }}>{status}</Tag>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: () => (
        <Space size="middle">
          <Button type="text" icon={<EyeOutlined />} title="View" />
        </Space>
      )
    }
  ]

  return (
    <div className="notice-list-table">
      <Table
        columns={columns}
        dataSource={dataSource}
        pagination={{
          pageSize: 10,
          showQuickJumper: true,
        }}
        scroll={{ x: 800 }}
        className="custom-table"
      />
      
      <style jsx global>{`
        .notice-list-table .custom-table {
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .notice-list-table .ant-table {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
        }
        
        .notice-list-table .ant-table-thead > tr > th {
          background-color: #f8fafc;
          color: #374151;
          font-weight: 600;
          border-bottom: 2px solid #e5e7eb;
          border-right: 1px solid #e5e7eb;
          font-size: 14px;
          font-weight: normal;
        }
        
        .notice-list-table .ant-table-thead > tr > th:last-child {
          border-right: none;
        }
        
        .notice-list-table .ant-table-tbody > tr > td {
          border-bottom: 1px solid #e5e7eb;
          border-right: 1px solid #e5e7eb;
          padding: 16px;
          font-size: 14px;
          font-weight: normal;
        }
        
        .notice-list-table .ant-table-tbody > tr > td:last-child {
          border-right: none;
        }
        
        .notice-list-table .ant-table-tbody > tr:hover > td {
          background-color: #f8fafc;
        }
        
        .notice-list-table .ant-tag {
          border-radius: 16px;
          padding: 2px 8px;
          font-size: 12px;
          font-weight: 500;
        }
        
        .notice-list-table .ant-btn-text {
          color: #64748b;
          padding: 4px 8px;
        }
        
        .notice-list-table .ant-btn-text:hover {
          color: #2563eb;
        }
      `}</style>
    </div>
  )
}

export default NoticeListTable
