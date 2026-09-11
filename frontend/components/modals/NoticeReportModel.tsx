import React, { useMemo, useState } from 'react'
import { Modal, Form, Select, Button, message } from 'antd'
import { RiErrorWarningLine, RiFileList3Line } from "react-icons/ri";
import { ReportApi } from '@/src/services/ReportApi';

interface NoticeModelProps {
  visible: boolean
  onCancel: () => void;
  onSuccess: (values: any, setLoading: any) => void;
  templatesType: any;
  banks: any;
  selectedBank: any;
}

export default function NoticeReportModel({
  visible,
  onCancel,
  onSuccess,
  templatesType,
  banks,
  selectedBank,
}: NoticeModelProps) {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const { Option } = Select;

  const isClientNotSelected = useMemo(() => {
    if (!selectedBank) return true;
    const normalized = String(selectedBank).trim().toLowerCase();
    return (
      normalized === "all" ||
      normalized === "all client" ||
      normalized === "all clients"
    );
  }, [selectedBank]);

  const handleSubmit = async (values: any) => {
    if (isClientNotSelected) {
      message.error("Please select an individual client instead of 'All Client'");
      return;
    }
    onSuccess(values, setLoading);
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  const filterAoDatas = useMemo(() => {
    if (isClientNotSelected) return [];
    const result =
      banks?.find(
        (res: any) =>
          res?.client_code === selectedBank ||
          res?.client_name === selectedBank ||
          res?.client === selectedBank
      )?.aos || [];
    return result;
  }, [banks, selectedBank, isClientNotSelected]);

  return (
    <Modal
      title={
        <div className="flex items-center gap-3 pb-3 border-b border-gray-100">
          <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shadow-sm flex-shrink-0">
            <RiFileList3Line className="text-xl" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-800 leading-tight m-0">
              Generate Notice
            </h3>
            <p className="text-xs text-gray-500 m-0 mt-0.5 font-normal">
              Select notice type and AO to generate notice documents
            </p>
          </div>
        </div>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={560}
      centered
      destroyOnClose
      className="generate-report-modal"
    >
      <style>{`
        .generate-report-modal .ant-modal-content {
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .generate-report-modal .ant-modal-header {
          margin-bottom: 16px;
        }

        .generate-report-modal .ant-form-item-label > label {
          font-weight: 600;
          color: #374151;
          font-size: 13.5px;
        }
        
        .generate-report-modal .ant-select-selector {
          border-radius: 8px !important;
          height: 42px !important;
          display: flex;
          align-items: center;
        }
        
        .generate-report-modal .ant-btn-primary:not(:disabled) {
          background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
          border: none;
          border-radius: 8px;
          font-weight: 600;
        }
        
        .generate-report-modal .ant-btn-primary:not(:disabled):hover {
          background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        }

        .generate-report-modal .ant-btn-primary:disabled,
        .generate-report-modal .ant-btn-primary[disabled] {
          background: #f5f5f5 !important;
          color: rgba(0, 0, 0, 0.25) !important;
          border: 1px solid #d9d9d9 !important;
          cursor: not-allowed !important;
          box-shadow: none !important;
          border-radius: 8px;
        }
        
        .generate-report-modal .ant-btn-default {
          border-radius: 8px;
          font-weight: 600;
        }
      `}</style>

      {isClientNotSelected && (
        <div className="flex items-start gap-3 p-3.5 my-4 rounded-xl bg-red-50/90 border border-red-200 text-red-700 transition-all">
          <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0 text-red-600 mt-0.5">
            <RiErrorWarningLine className="text-xl" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-red-600">
              Please select an individual client
            </div>
            <p className="text-xs text-red-600/90 m-0 mt-0.5 leading-relaxed">
              Notice generation is not available for <span className="font-semibold">&quot;All Client&quot;</span>. Please select a specific individual client from the dashboard to load notice types and AO details.
            </p>
          </div>
        </div>
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        className={isClientNotSelected ? "mt-2" : "mt-4"}
      >
        <Form.Item
          label="Select Notice Type"
          name="reportType"
          className="!mb-4"
          rules={[
            {
              required: !isClientNotSelected,
              message: "Please select a report type",
            },
          ]}
        >
          <Select
            placeholder="Choose notice type"
            size="large"
            className="w-full"
            disabled={isClientNotSelected}
          >
            {templatesType?.map((template: any) => (
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

        <Form.Item
          name="aoCode"
          label="Select AO"
          className="!mb-6"
          rules={[
            {
              required: !isClientNotSelected,
              message: "Please select an AO",
            },
          ]}
        >
          <Select
            placeholder="Select AO"
            size="large"
            className="w-full"
            showSearch
            allowClear
            disabled={isClientNotSelected}
          >
            {filterAoDatas?.map((ao: any) => (
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

        <div className="flex gap-3 justify-end pt-4 border-t border-gray-100">
          <Button
            onClick={handleCancel}
            size="large"
            className="h-[40px] px-5 rounded-lg font-medium border-gray-300 text-gray-600 hover:text-gray-800"
          >
            Cancel
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            size="large"
            disabled={isClientNotSelected}
            className={`h-[40px] px-5 rounded-lg font-semibold transition-all ${isClientNotSelected
                ? "!bg-gray-100 !border-gray-200 !text-gray-400 !cursor-not-allowed shadow-none"
                : "!bg-blue-600 hover:!bg-blue-700 !text-white shadow-sm"
              }`}
          >
            Generate Notice
          </Button>
        </div>
      </Form>
    </Modal>
  );
}
