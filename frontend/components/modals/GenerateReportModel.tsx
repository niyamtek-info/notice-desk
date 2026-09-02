import React, { useState } from 'react'
import { Modal, Form, Select, Button, message, Radio } from 'antd'
import { FileTextOutlined, FilePdfOutlined, FileExcelOutlined } from '@ant-design/icons'
import { fromJS } from 'immutable';

interface GenerateModelProps {
  visible: boolean;
  onSuccess: (setLoading:any) => void;
  onCancel: () => void;
  type: string;
}

const reportOptions = [
  // { label: 'Loan Details', value: 'loan_details' },
  { label: '13.2 Details', value: 'details_13_2' },
  // { label: '14.2 Details', value: 'details_14_2' }
]

export default function GenerateReportModel({ visible, onSuccess, onCancel,type }: GenerateModelProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [downloadFormat, setDownloadFormat] = useState<'pdf' | 'excel'>('pdf')

  const handleSubmit = async (values: any) => {
    onSuccess(setLoading)
  }

  const handleCancel = () => {
    form.resetFields()
    onCancel()
  }

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 mb-4">
          <FileTextOutlined className="!text-blue-600 text-lg" />
          <h1 className="text-lg flex items-center font-semibold">Generate {type == "multiple" ? "Multiple" :""} Report</h1>
        </div>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={700}
      destroyOnClose
      className="generate-report-modal"
      style={{ paddingTop: '24px', paddingRight: '24px', paddingBottom: '24px', paddingLeft: '24px' }}
    >
      <style>{`
        .generate-report-modal .ant-modal-content {
          border-radius: 12px;
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .generate-report-modal .ant-form-item-label > label {
          font-weight: 600;
          color: #374151;
        }
        
        .generate-report-modal .ant-select-selector {
          border-radius: 8px !important;
        }
        
        .generate-report-modal .ant-btn-primary {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          border: none;
          border-radius: 8px;
          height: 40px;
          font-weight: 600;
        }
        
        .generate-report-modal .ant-btn-primary:hover {
          background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        }
        
        .generate-report-modal .ant-btn-default {
          border-radius: 8px;
          height: 40px;
          font-weight: 600;
        }
      `}</style>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        className="space-y-4"
      >
        <Form.Item
          label="Select Report Type"
          name="reportType"
          rules={[{ required: false, message: 'Please select a report type' }]}
        >
          <Select
            placeholder="Choose report type"
            size="large"
            className="h-[40px] custom-select-height"
            options={reportOptions}
            defaultValue="13.2 Details"
          />
        </Form.Item>


        <div className="flex gap-3 justify-end pt-4">
          <Button
            onClick={handleCancel}
            size="large"
          >
            Cancel
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            size="large"
          >
            Generate Report
          </Button>
        </div>
      </Form>
    </Modal>
  )
}
