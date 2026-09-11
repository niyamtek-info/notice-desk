import React, { useEffect, useState } from 'react'
import { ConfigProvider, Modal, Segmented, Tabs } from 'antd'
import Document1 from '../pages/information-gathering/document1/Document1'
import NewChecklistContent from '../pages/application-details/NewChecklistContent'


interface DocsandCheckListModelProps {
  visible: boolean
  onCancel: () => void
  applicationId: string;
  token: string; 
  setTriggerReport: any;
}

export const DocsandCheckListModel: React.FC<DocsandCheckListModelProps> = ({
  visible,
  onCancel,
  applicationId,
  token,
  setTriggerReport,
}) => {

  const [type,setType] = useState<string>("Document");
  const [docData,setDocData] = useState<any>([]);
  const [disableCheklist,setDisableCheklist] = useState<boolean>(false)


  const isValid = (arr:any) => {
  const has = (types: string[]) =>
    arr.some(
      (item:any) =>
        types.some(t => item.filetype?.toLowerCase() === t.toLowerCase()) &&
        !item.error &&
        !["",null,undefined].includes(item.document_url) 
    );

  return (
    (has(["Sale Deed", "Sales Deed"]) &&
      has(["Memorandum of Deposit of Title Deed", "Memorandum of Deposit of Title Deeds"])) ||
    (has(["Loan Agreement"]) &&
      has(["Sanction Letter"]))
  );
};


  useEffect(()=>{
    if(docData?.length == 0){
      setDisableCheklist(false)
    }else{
     const result = isValid(docData);
     setDisableCheklist(result)
    }
  
  },[docData])


  return (
    <Modal
      open={visible}
      onCancel={onCancel}
      width="100%"
      height="95%"
      footer={null}
      centered
      destroyOnClose
      className="docs-checklist-modal"
      title={<span className="text-[20px] font-bold text-stone-800 mb-0">
              {type || ""} Details
            </span>}
      
    >
         <div className="flex justify-center items-center p-[0px_0px_10px_0px] z-10 bg-white sticky top-[30px] border-b border-gray-200 mb-4">
            
            <div className="flex items-center gap-3 pr-[30px]">
              <ConfigProvider
                theme={{
                  components: {
                    Segmented: {
                      itemSelectedBg: "#2563EB", // Blue-600
                      itemSelectedColor: "#ffffff",
                      trackBg: "#F3F4F6", // Gray-100
                      itemColor: "#4B5563", // Gray-600
                      trackPadding: 2,
                      borderRadius: 20,
                    },
                  },
                }}
              >
                <Segmented
                  options={[
                    { label: "Document", value: "Document" },
                    { label: "CheckList", value: "CheckList", disabled: !disableCheklist }
                  ]}
                  size="middle"
                  value={type}
                  onChange={(value) => {
                    setType(value as "Document" | "CheckList");
                    // form.resetFields();
                  }}
                  className="font-medium !text-[14px]"
                />
              </ConfigProvider>
            </div>
          </div>
          {type == "Document" ? 
          <div style={{ maxHeight: '75vh', overflow: 'auto' }}>
            <Document1 token={token} setDocData={setDocData} setTriggerReport={setTriggerReport}/>
          </div>
          :
          <div style={{ maxHeight: '75vh', overflow: 'auto' }}>
            <NewChecklistContent applicationId={applicationId} setTriggerReport={setTriggerReport}/>
          </div>}
    </Modal>
  )
}
