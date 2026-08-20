import React, { useMemo, useState } from 'react'
import { Modal, Form, Select, Button, message } from 'antd'
import { FileExcelOutlined, FilePdfOutlined, FileTextOutlined } from '@ant-design/icons'
import { ReportApi } from '@/src/services/ReportApi';

interface NoticeModelProps {
  visible: boolean
  onCancel: () => void;
  onSuccess: (values: any,setLoading:any) => void;
  templatesType: any;
  banks: any;
  selectedBank:any;
}


export default function NoticeReportModel({ visible, onCancel,onSuccess,templatesType,banks,selectedBank }: NoticeModelProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  
  const { Option } = Select;

  const handleSubmit = async (values: any) => {
    onSuccess(values,setLoading) 

  }

  const handleCancel = () => {
    form.resetFields()
    onCancel()
  }

  const filterAoDatas = useMemo(()=>{
   const result = banks?.find((res:any)=>res?.client_code === selectedBank || res?.client_name === selectedBank || res?.client === selectedBank)?.aos || [];
   return result
  },[banks,selectedBank])

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 mb-4">
          <FileTextOutlined className="!text-blue-600 text-lg" />
          <span className="text-lg font-semibold">Generate Notice</span>
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
      <style jsx global>{`
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
          label="Select Notice Type"
          name="reportType"
          rules={[{ required: true, message: 'Please select a report type' }]}
        >
          <Select
            placeholder="Choose notice type"
            size="large"
            className="h-[40px] custom-select-height"
          >
            {templatesType.map((template: any, index: number) => (
              <Option key={template?.template_code} value={template?.id}>
                <div className="flex items-center gap-2">
                  <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                    {template?.template_code}
                  </span>
                  <span>{template?.template_type}</span>
                </div>
              </Option>
            ))}
          </Select>  
        </Form.Item>

                {/* Client Name */}
        <Form.Item
          name="aoCode"
          label="Select AO"
          rules={[{ required: true, message: "Please select a AO" }]}
        >
          <Select
            placeholder="Select AO"
            className="h-[40px] custom-select-height"
            showSearch
            allowClear
          >
            {filterAoDatas?.map((ao: any, index: number) => (
              <Option key={ao?.ao_code} value={ao?.ao_code}>
                <div className="flex items-center gap-2">
                  <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                    {ao.ao_code}
                  </span>
                  <span>{ao.ao_name}</span>
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>

        
        {/* <Form.Item
          label="Download Format"
          name="downloadFormat"
          initialValue="pdf"
          rules={[{ required: true, message: 'Please select download fromat' }]}
        >
          <div className="grid grid-cols-2 gap-4">
            
            <div
              onClick={() => setDownloadFormat("pdf")}
              className={`flex items-center justify-between px-6 py-4 rounded-xl cursor-pointer border transition-all
              ${
                downloadFormat === "pdf"
                  ? "border-blue-500 bg-blue-50 shadow-sm"
                  : "border-gray-200 hover:border-blue-400"
              }`}
            >
              <div className="flex items-center gap-3">
                <FilePdfOutlined className="!text-blue-600 text-xl" />
                <div>
                  <p className="font-medium">PDF</p>
                  <p className="text-xs text-gray-500">
                    Best for sharing & printing
                  </p>
                </div>
              </div>

              {downloadFormat === "pdf" && (
                <div className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center">
                  ✓
                </div>
              )}
            </div>

            <div
              onClick={() => setDownloadFormat("excel")}
              className={`flex items-center justify-between px-6 py-4 rounded-xl cursor-pointer border transition-all
              ${
                downloadFormat === "excel"
                  ? "border-blue-500 bg-blue-50 shadow-sm"
                  : "border-gray-200 hover:border-blue-400"
              }`}
            >
              <div className="flex items-center gap-3">
                <FileExcelOutlined className="!text-blue-600 text-xl" />
                <div>
                  <p className="font-medium">Excel</p>
                  <p className="text-xs text-gray-500">
                    Best for data editing
                  </p>
                </div>
              </div>

              {downloadFormat === "excel" && (
                <div className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center">
                  ✓
                </div>
              )}
            </div>

          </div>
        </Form.Item> */}

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
            Generate Notice
          </Button>
        </div>
      </Form>
    </Modal>
  )
}
