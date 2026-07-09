import { Modal, Form, Input, Upload, Button, message, Select } from 'antd'
import React, { useEffect, useState } from 'react'
import { UploadOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { RiDeleteBinLine } from 'react-icons/ri'
import type { UploadProps } from 'antd'
import { FiUpload } from "react-icons/fi";
import { FaRegCircleCheck } from 'react-icons/fa6'
import { TbTemplate } from "react-icons/tb";
import { FaRegEdit } from 'react-icons/fa'


interface TemplateModelProps {
  open: boolean;
  handleCancel: (resetFormOrEvent?: (() => void) | any) => void;
  onSuccess?: (values: any) => void;
  bankListDropOrinal:any;
  editTempalteData:any;
  setFileUpload: (values:boolean) => void;
}

export default function CreateTemplateModel({ open, handleCancel, onSuccess,bankListDropOrinal,editTempalteData,setFileUpload }: TemplateModelProps) {

  const [form] = Form.useForm();
  const [templateFile, setTemplateFile] = useState<any>();
  const [templateFileName,setTemplateFileName] = useState<string>("")
  const [bankBranches,setBankBranches] = useState<any>([]);
  const [branchCode,setBranchCode] = useState<any>()
  const [editFile,setEditFile] = useState<boolean>(false)


  useEffect(()=>{
    if(editTempalteData){
      form.setFieldsValue({
        template_file:editTempalteData?.file_name || "test",
        template_name:editTempalteData?.template_name,
        template_code:editTempalteData?.template_code,
        bank_code:bankListDropOrinal?.find((res:any) => res?.code == editTempalteData?.bank_id)?.code ,
        bank_branch:bankListDropOrinal?.find((res:any) => res?.code == editTempalteData?.bank_id)?.branches?.find((val:any)=>val?.branch_code == editTempalteData?.branch_id)?.branch_name  
      })
      setTemplateFileName(editTempalteData?.file_name)
      setTemplateFile({
        name:"file",
        size:1
      })
    }
  },[editTempalteData])


  const handleSubmit = async (values: any) => {
   
    const formData = {
      ...values,
      file_path: templateFile,
      file_name: templateFileName,
      branch_code: branchCode
    };
    // message.success('Template created successfully!');


    if (onSuccess) {
      onSuccess(formData);
    }
    handleCancel(resetForm);
  };

 const handleTemplateFileChange = (info: any) => {
  if (info.fileList?.length > 0) {
    const file = info.fileList[0].originFileObj; // IMPORTANT
    setFileUpload(true)
    
    setEditFile(true);
    setTemplateFileName(file?.name)
    setTemplateFile(file);
  } else {
    setTemplateFile(null);
  }
};


  const handleDeleteTemplateFile = () => {
    setTemplateFile(null);
    form.setFieldsValue({ template_file: [] });
  };

  const resetForm = () => {
    form.resetFields();
    setTemplateFile(null);
  };

  const onCancelClick = () => {
    handleCancel(resetForm);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    listType: 'text',
    accept: '.doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    maxCount: 1,
    beforeUpload: (file) => {
      const isDoc = file.type === 'application/msword' || 
                   file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                   file.name.endsWith('.doc') ||
                   file.name.endsWith('.docx');
      if (!isDoc) {
        message.error('You can only upload Word documents (.doc, .docx)!');
        return false;
      }
      return false;
    },
  };

  const handleOnchangeBank = (key:any,value:any) => {

    form.setFieldsValue({bank_branch: null})
    form.setFieldsValue({bank_name: value?.key || ""})
    const filterBranch = bankListDropOrinal?.find((res: any) => res?.code === key)?.branches || [];
    setBankBranches(filterBranch)
  }

  const handleOnchangeBranch = (key:any,value:any) => {
     setBranchCode(value?.value)
    //  form.setFieldsValue({bank_branch_id: value?.key})
  }

  return (
    <Modal
      title={
        <>
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-[19px] font-bold text-gray-900">{editTempalteData ? "Edit Template" : "Create Template"}</h2>           
          </div>
        </div>
         {/* <div className='bg-gray-200 w-full h-[1.3px]'/> */}
         </>
      }
      open={open}
      onCancel={()=>handleCancel(resetForm)}
      footer={null}
      centered
      width="45%"
      // style={{ maxWidth: 1000 }}
      className="professional-modal"
       style={{ top: 20,padding:"20px_40px_0_40px" }}
        classNames={{
          content: '!pb-[0] !shadow-none'
        }}
      
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        className="mt-4"
      >
        {/* Main Layout - Bank Details Left, Branch Section Right */}
        <div className="grid grid-cols-1 lg:grid-cols-1 gap-10 relative p-[10px_20px] rounded-[12px]">
          
          {/* Left Side - Bank Details */}
          <div className="space-y-4">
              {/* <div className="flex items-center gap-2 mb-4">
                <div>
                  <h3 className="text-[16px] font-semibold text-gray-900">Template Information</h3>
                </div>
              </div> */}
              
              <div className="grid grid-cols-1">
                <Form.Item
                  name="template_name"
                  label={<span className="text-sm font-medium">Template Name</span>}
                  rules={[{ required: true, message: 'Please enter template name' }]}
                  className="mb-1"
                >
                  <Input 
                    placeholder="Enter template name" 
                    className="h-[40px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors" 
                  />
                </Form.Item>

                <Form.Item
                  name="template_code"
                  label={<span className="text-sm font-medium">Template Code</span>}
                  rules={[{ required: true, message: 'Please enter template code' }]}
                  className="mb-1"
                >
                  <Input 
                    placeholder="Enter template code" 
                    className="h-[40px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors" 
                  />
                </Form.Item>

                <Form.Item
                  name="bank_code"
                  label={<span className="text-sm font-medium">Bank Code</span>}
                  rules={[{ required: true, message: 'Please select bank code' }]}
                  className="mb-1"
                >

                 <Select
                    placeholder={
                        <div className="flex items-center">
                            Select Bank Code
                        </div>
                    }
                    style={{ width: '100%', height: '40px' }}
                    showSearch
                    onChange={(key,value) => handleOnchangeBank(key,value)}
                    filterOption={true}
                    allowClear
                >
                    {bankListDropOrinal.map((bank:any) => (
                        <Select.Option key={bank.name} value={bank.code}>
                            {bank.code}
                        </Select.Option>
                    ))}
                </Select>

                </Form.Item>


                <Form.Item
                  name="bank_name"
                  label={<span className="text-sm font-medium">Bank Name</span>}
                  rules={[{ required: true, message: 'Please enter bank name' }]}
                  className="mb-1"
                >
                  <Input 
                    readOnly
                    placeholder="Enter bank name" 
                    className="h-[40px] rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500 transition-colors" 
                  />
                </Form.Item>

                 <Form.Item
                  name="bank_branch"
                  label={<span className="text-sm font-medium">Bank Branch</span>}
                  rules={[{ required: true, message: 'Please enter bank branch' }]}
                  className="mb-1"
                >

                <Select
                    placeholder={
                        <div className="flex items-center">
                            Select Bank Code
                        </div>
                    }
                    style={{ width: '100%', height: '40px' }}
                    showSearch
                    onChange={(key,value) => handleOnchangeBranch(key,value)}
                    filterOption={true}
                    allowClear
                >
                    {bankBranches.map((bank:any) => (
                        <Select.Option key={bank.branch_name} value={bank.branch_code}>
                            {bank.branch_name}
                        </Select.Option>
                    ))}
                </Select>

                </Form.Item>


                <Form.Item
                  name="template_file"
                  label={<span className="text-sm font-medium">Template File</span>}
                  valuePropName="fileList"
                  getValueFromEvent={(e) => {
                    // Always return an array of files for consistency with Upload component
                    if (Array.isArray(e)) {
                      return e;
                    }
                    return e?.fileList || templateFile;
                  }}
                  rules={[{ required: true, message: 'Please upload template file' }]}
                  className="mb-0 template-file"
                >
                  {templateFile ? (
                    <div className="border-2 border-gray-200 rounded-lg p-4 bg-gray-50 w-full">
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <FaRegCircleCheck color='#22c55e' className="text-green-500 text-xl flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 truncate">{templateFileName}</p>
                            {/* <p className="text-sm text-gray-600">{(templateFile.size / 1024).toFixed(2)} KB</p> */}
                          </div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <Button 
                            icon={<RiDeleteBinLine size={15} />}
                            onClick={handleDeleteTemplateFile}
                            className="border-2 border-dashed !bg-red-500 !text-white whitespace-nowrap"
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <Upload {...uploadProps} 
                        showUploadList={false}
                          beforeUpload={() => false}   // IMPORTANT

                        onChange={handleTemplateFileChange}
                        className="w-full">
                      <div className="flex items-center justify-between p-3 border-2 border-dashed border-gray-300 rounded-lg w-full">
                        <div className="flex items-center gap-3 cursor-pointer">
                          <FiUpload className="text-gray-900 text-xl" />
                          <div>
                            <span className="font-medium text-gray-700">Upload or Drag & Drop Template File</span>
                            <p className="text-sm text-gray-500">Word documents (.doc, .docx) only</p>
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
                  )}
                </Form.Item>
              </div>
            {/* </div> */}
          </div>
          {/* Right Side - Branch Section */}
        </div>

        {/* Form Actions */}
        <Form.Item className="mb-0">
          <div className="flex justify-end items-center pb-[20px]">
            
            <div className="flex gap-3">
              <Button 
                onClick={onCancelClick} 
                className="rounded-lg px-6 border-gray-300 text-gray-700 hover:border-gray-400 hover:text-gray-900 transition-colors"
              >
                Cancel
              </Button>
              <Button 
                icon={editTempalteData ? <FaRegEdit /> : <TbTemplate />}
                type="primary" 
                htmlType="submit" 
                className="rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 border-blue-600 px-8 py-2 text-white font-medium shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5"
              >
                {editTempalteData ? "Update Template" : "Create Template"}
              </Button>
            </div>
          </div>
        </Form.Item>
      </Form>
    </Modal>
  )
}
