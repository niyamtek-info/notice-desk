import React, { useEffect, useState } from 'react';
import { Modal, Form, Button, Upload, message, Select } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import { BankApi } from '@/src/services/BankApi';

interface CreateNoticeModalProps {
  visible: boolean;
  onCancel: () => void;
  onSubmit: (values: CreateNoticeFormValues) => void;
  editTempalteData: any
}

export interface CreateNoticeFormValues {
  headerImageUrl?: string;
  footerImageUrl?: string;
  headerImgName?: string;
  footerImgName?: string;
  clientName?: string;
  aoCode?: string;
  clientCode?: string;
  templateType?: string;

}

const CreateNoticeModal: React.FC<CreateNoticeModalProps> = ({
  visible,
  onCancel,
  onSubmit,
  editTempalteData
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [headerImageList, setHeaderImageList] = useState<UploadFile[]>([]);
  const [footerImageList, setFooterImageList] = useState<UploadFile[]>([]);
  const [headerBase64, setHeaderBase64] = useState<string>('');
  const [footerBase64, setFooterBase64] = useState<string>('');
  const [banks, setBanks] = useState<any>([]);
  const [templatesType, setTemplatesType] = useState<any>([]);
  const [headerImgName,setHeaderImgName] = useState<string>("")
  const [footerImgName,setFooterImgName] = useState<string>("")


  const [aoData,setAoData] = useState<any>([]);

  const { Option } = Select;

  const handleFetchBank = async () => {
    try {
      let response: any = await BankApi.getBankList();
      setBanks(response);
    } catch (error) { }
  };

  const handleFetchTemplate = async () => {
    try {
      let response: any = await BankApi.getTemplateType();
      setTemplatesType(response);
    } catch (error) { }
  }

  useEffect(() => {
    handleFetchBank()
    handleFetchTemplate()
  }, [])


async function extractBodyContent(htmlString:any) {
  // Reset previous image states
  setHeaderBase64('');
  setHeaderImageList([]);
  form.setFieldValue("headerImageUrl", undefined);
  
  setFooterBase64('');
  setFooterImageList([]);
  form.setFieldValue("footerImageUrl", undefined);

  if (!htmlString?.html_presigned_url) return;

  try {
    // Always fetch via proxy — never fall back to a direct GCS URL fetch.
    // A direct fetch of a private-bucket URL returns an XML AccessDeniedException
    // body that would be treated as valid HTML template content.
    const proxyUrl = `/api/proxy?url=${encodeURIComponent(htmlString.html_presigned_url)}`;
    const response = await fetch(proxyUrl);
    if (!response.ok) {
      console.error("Failed to fetch HTML template via proxy:", response.status);
      return;
    }

    let htmlData = await response.text();
    let cleaned = htmlData
      ?.replace(/\\r\\n/g, "")
      ?.replace(/\\"/g, '"');

    const headerMatch = cleaned.match(
      /<header[\s\S]*?(data:image\/[^;]+;base64,[^"'>\s]+)[\s\S]*?<\/header>/i
    );
    if (headerMatch) {
      setHeaderBase64(headerMatch[1]);
      setHeaderImageList([{ uid: 'edit-header', name: htmlString?.header_image_name || "" , status: 'done' }]);
      form.setFieldValue("headerImageUrl", headerMatch[1]);
    }

    const footerMatch = cleaned.match(
      /<footer[\s\S]*?(data:image\/[^;]+;base64,[^"'>\s]+)[\s\S]*?<\/footer>/i
    );
    if (footerMatch) {
      setFooterBase64(footerMatch[1]);
      setFooterImageList([{ uid: 'edit-footer', name: htmlString?.footer_image_name || "", status: 'done' }]);
      form.setFieldValue("footerImageUrl", footerMatch[1]);
    }
  } catch (error) {
    console.error("Failed to extract body content in modal:", error);
  }
}

  // Effect 1: Fetch content and set image names when template and visibility change
  useEffect(() => {
    if (visible && editTempalteData) {
      setHeaderImgName(editTempalteData?.header_image_name || "");
      setFooterImgName(editTempalteData?.footer_image_name || "");
      extractBodyContent(editTempalteData);
    }
  }, [editTempalteData, visible]);

  // Effect 2: Set form field values when banks/templates load or template changes
  useEffect(() => {
    if (visible && editTempalteData && banks.length > 0 && templatesType.length > 0) {
      form.setFieldsValue({
        clientName: editTempalteData.client_name || editTempalteData.bank_name,
        templateType: editTempalteData.template_type || editTempalteData.template || editTempalteData.template_name
      });
    }
  }, [editTempalteData, visible, banks, templatesType]);

  const handleSubmit = async (values: any) => {
    setLoading(true);

    try {
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Include base64 data in the submitted values
      const formData = {
        headerImageUrl: headerBase64,
        footerImageUrl: footerBase64,
        headerImgName: headerImgName,
        footerImgName: footerImgName,
        clientName: values?.clientName,
        aoCode: values?.aoCode,
        clientCode: banks?.find((res: any) => res?.client_name == values?.clientName)?.client_code || "",
        templateType: values?.templateType,
      };

      // message.success('Notice template created successfully!');
      form.resetFields();
      setHeaderImageList([]);
      setFooterImageList([]);
      setHeaderBase64('');
      setFooterBase64('');
      onSubmit(formData);
    } catch (error) {
      message.error('Failed to create template. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setHeaderImageList([]);
    setFooterImageList([]);
    setHeaderBase64('');
    setFooterBase64('');
    onCancel();
  };

  // Handle header image upload
  const headerUploadProps: UploadProps = {
    listType: 'text',
    fileList: headerImageList.length > 0 ? [{ uid: '0', name: headerImageList[0].name, status: 'done' }] : [],
    maxCount: 1,
    accept: 'image/*',
    showUploadList: {
      showPreviewIcon: false,
      showRemoveIcon: true,
      showDownloadIcon: false,
    },
    beforeUpload: (file) => {
      const isImage = file.type.startsWith('image/');
      if (!isImage) {
        message.error('You can only upload image files!');
        return false;
      }
      const isLt5M = file.size / 1024 / 1024 < 5;
      if (!isLt5M) {
        message.error('Image must be smaller than 5MB!');
        return false;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const base64 = e.target?.result as string;
        // Store base64 in state
        setHeaderBase64(base64);
        setHeaderImageList([{ uid: file.uid, name: file.name, status: 'done' }]);
        // Set form field value for validation
        form.setFieldsValue({ headerImageUrl: base64 });
        setHeaderImgName(file.name)
      };
      reader.readAsDataURL(file);
      return false;
    },
    onRemove: () => {
      setHeaderImageList([]);
      setHeaderBase64('');
      setHeaderImgName("")
      // Clear form field value
      form.setFieldsValue({ headerImageUrl: undefined });
      return true;
    },
    itemRender: (origin, file, fileList) => (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 10px',
        background: '#f5f5f5',
        borderRadius: '4px',
        width: '100%',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, overflow: 'hidden' }}>
          <UploadOutlined style={{ color: '#666', flexShrink: 0, fontSize: '14px' }} />
          <span style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            color: '#333',
            fontSize: '12px',
          }}>{file.name || headerImgName}</span>
        </div>
        <span
          onClick={() => {
            setHeaderImageList([]);
            setHeaderBase64('');
            setHeaderImgName("")
            // Clear form field value
            form.setFieldsValue({ headerImageUrl: undefined });
          }}
          style={{
            cursor: 'pointer',
            color: '#999',
            marginLeft: '6px',
            flexShrink: 0,
            fontSize: '14px',
          }}
        >
          ✕
        </span>
      </div>
    ),
  };

  // Handle footer image upload
  const footerUploadProps: UploadProps = {
    listType: 'text',
    fileList: footerImageList.length > 0 ? [{ uid: '0', name: footerImageList[0].name, status: 'done' }] : [],
    maxCount: 1,
    accept: 'image/*',
    showUploadList: {
      showPreviewIcon: false,
      showRemoveIcon: false,
      showDownloadIcon: false,
    },
    beforeUpload: (file) => {
      const isImage = file.type.startsWith('image/');
      if (!isImage) {
        message.error('You can only upload image files!');
        return false;
      }
      const isLt5M = file.size / 1024 / 1024 < 5;
      if (!isLt5M) {
        message.error('Image must be smaller than 5MB!');
        return false;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const base64 = e.target?.result as string;
        // Store base64 in state
        setFooterBase64(base64);
        setFooterImageList([{ uid: file.uid, name: file.name, status: 'done' }]);
        // Set form field value for validation
        form.setFieldsValue({ footerImageUrl: base64 });
        setFooterImgName(file.name)
      };
      reader.readAsDataURL(file);
      return false;
    },
    onRemove: () => {
      setFooterImageList([]);
      setFooterBase64('');
      setFooterImgName("")
      // Clear form field value
      form.setFieldsValue({ footerImageUrl: '' });
      return true;
    },
    itemRender: (origin, file, fileList) => (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 10px',
        background: '#f5f5f5',
        borderRadius: '4px',
        width: '100%',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flex: 1, overflow: 'hidden' }}>
          <UploadOutlined style={{ color: '#666', flexShrink: 0, fontSize: '14px' }} />
          <span style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            color: '#333',
            fontSize: '12px',
          }}>{file.name || footerImgName}</span>
        </div>
        <span
          onClick={() => {
            setFooterImageList([]),
            setFooterBase64('');
            setFooterImgName("")
            // Clear form field value
            form.setFieldsValue({ footerImageUrl: '' });}}
          style={{
            cursor: 'pointer',
            color: '#999',
            marginLeft: '6px',
            flexShrink: 0,
            fontSize: '14px',
          }}
        >
          ✕
        </span>
      </div>
    ),
  };

  // Custom upload button component
  const uploadButton = (
    <div style={{
      border: '1px dashed #d9d9d9',
      borderRadius: '4px',
      padding: '16px',
      textAlign: 'center',
      cursor: 'pointer',
      width: '100%',
      background: '#fafafa',
      transition: 'border-color 0.3s',
    }}>
      <UploadOutlined style={{ fontSize: '18px', color: '#1890ff', marginBottom: '8px', display: 'block' }} />
      <span style={{ color: '#666', fontSize: '14px' }}>Click to upload an image, or drag and drop an image to upload.</span>
    </div>
  );

  return (
    <Modal
      title={editTempalteData ? "Update Notice Template" : "Create Notice Template"}
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={520}
      destroyOnClose
      centered
    >
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        {/* Notice Name */}


        {/* Header Image */}
        <Form.Item
          label="Header Image"
          name="headerImageUrl"
          style={{ marginBottom: '16px', width: '100%' }}
          rules={[{ required: true, message: 'Please upload header image' }]}
        >
          <Upload {...headerUploadProps} style={{ width: '100%' }}>
            {headerBase64 ? null : uploadButton}
          </Upload>
        </Form.Item>

        {/* Footer Image */}
        <Form.Item
          label="Footer Image"
          name="footerImageUrl"
          style={{ marginBottom: '20px', width: '100%' }}
          rules={[{ required: true, message: 'Please upload footer image' }]}
        >
          <Upload {...footerUploadProps} style={{ width: '100%' }}>
            {footerImageList.length >= 1 ? null : uploadButton}
          </Upload>
        </Form.Item>
        
        {/* Client Name */}
        <Form.Item
          name="clientName"
          label="Client Name"
          rules={[{ required: true, message: "Please select a Client" }]}
        >
          <Select
            placeholder="Select Client"
            className="h-[40px] custom-select-height"
            showSearch
            allowClear
            onChange={(value, option) => {
              const selectedClient = banks?.find((item:any) => item?.client_name === value)?.aos || [];
              setAoData(selectedClient);
              form.setFieldValue("aoCode", undefined);
             }}
          >
            {banks?.filter((res: any) => res?.client_code !== "all").map((client: any, index: number) => (
              <Option key={client?.client_code} value={client?.client_name}>
                <div className="flex items-center gap-2">
                  <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                    {client.client_code}
                  </span>
                  <span>{client.client_name}</span>
                </div>
                {/* {bank?.bank_name} - {bank?.bank_code} */}
              </Option>
            ))}
          </Select>
        </Form.Item>

        {/* Template Name */}
        <Form.Item
          name="templateType"
          label="Template Type"
          rules={[{ required: true, message: "Please select a Template" }]}
        >
          <Select
            placeholder="Select Template"
            className="h-[40px] custom-select-height"
            showSearch
            allowClear
          >
            {templatesType.map((template: any, index: number) => (
              <Option key={template?.service_code} value={template?.template_type}>
                <div className="flex items-center gap-2">

                  <span>{template.template_type}</span>
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>




        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <Button
            onClick={handleCancel}
            size="middle"
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            size="middle"
          >
            {editTempalteData ? "Update Template" : "Create Template"}
          </Button>
        </div>
      </Form>
    </Modal>
  );
};

export default CreateNoticeModal;