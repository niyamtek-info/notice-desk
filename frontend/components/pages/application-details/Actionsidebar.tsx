import { DocsandCheckListModel } from '@/components/modals/DocsandCheckListModel';
import GenerateReportModel from '@/components/modals/GenerateReportModel';
import NoticeModel from '@/components/modals/NoticeModel';
import { ReportApi } from '@/src/services/ReportApi';
import { message } from 'antd';
import React, { useState } from 'react';
import { BiSolidReport } from 'react-icons/bi';
import {
  MdOutlineDocumentScanner,
  MdOutlineAnnouncement,
  MdOutlineReport,
} from 'react-icons/md';


// Inject custom styles
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    .tooltip-container {
      position: relative;
      display: inline-block;
    }
    
    .tooltip-container:hover .tooltip-text {
      visibility: visible;
      opacity: 1;
    }
    
    .tooltip-text {
      visibility: hidden;
      opacity: 0;
      position: absolute;
      background-color: #1f2937;
      color: white;
      padding: 4px 8px;
      border-radius: 8px;
      font-size: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      z-index: 1000;
      white-space: nowrap;
      margin-top: -40px;
      margin-left: 10px;
      transition: opacity 0.3s;
    }
  `;
  document.head.appendChild(style);
}

interface ActionsidebarProps {
  applicationId: string;
  token: string;
  bankCode: any;
  banks: any;
  setTriggerReport: any;
  initialData?: any;
}

export default function Actionsidebar({applicationId,token,bankCode,banks,setTriggerReport,initialData}:ActionsidebarProps) {
  const [docModel,setDocModel] = useState<boolean>(false)
  const [modelType,setModelType] = useState<string>("")

  const [messageApi, contextHolder] = message.useMessage();

  const menuItems = [
    {
      label: 'Document',
      icon: <MdOutlineDocumentScanner size={25} />,
      bg: 'bg-blue-100',
      text: 'text-blue-600',
      border: 'border-blue-300',
    },
    {
      label: 'Notice',
      icon: <MdOutlineAnnouncement size={25} />,
      bg: 'bg-green-100',
      text: 'text-green-600',
      border: 'border-green-300',
    },
    {
      label: 'Report',
      icon: <BiSolidReport size={25} />,
      bg: 'bg-purple-100',
      text: 'text-purple-600',
      border: 'border-purple-300',
    },
  ];

  const handleDocCancel = () => {
   setDocModel(false)
   setModelType("")
  }

  const handleIconClick = (type:string) => {
      if(type == "Document"){
        setModelType(type)
        setDocModel(true)
      }else if(type == "Notice"){
        setModelType(type)
        setDocModel(true)
      }else if(type == "Report"){
        setModelType(type)
        setDocModel(true)
      }
      
  }

  const handleDownloadApi = async (setLoader:any) => {
        setLoader(true)
        try {
          let payload = {
            "application_numbers":[applicationId]
          }
          const blob: Blob = await ReportApi.create(payload);
    
          const url = window.URL.createObjectURL(blob);
    
          const link = document.createElement("a");
          link.href = url;
          link.download = "Reports.xlsx";
          document.body.appendChild(link);
          link.click();
    
          document.body.removeChild(link);
          window.URL.revokeObjectURL(url);
          setDocModel(false)
        } catch (error) {
          console.error("Download failed:", error);
          messageApi.error(String(error));
        } finally {
          setLoader(false)
        }
  }

  return (
    <>
    {contextHolder}
    <div className="bg-white rounded-xl shadow-sm p-4 sm:p-6 h-full min-h-[600px] w-full">
      <h2 className="text-lg sm:text-xl flex items-center justify-center font-bold mb-4 text-gray-800">
       Actions
      </h2>

      <ul className="">
        {menuItems.map((item) => (
          <li key={item.label}>
            <button
              className="w-full flex items-center justify-center gap-1 sm:gap-3  py-2 rounded-lg transition-all duration-200 hover:bg-gray-50"
            >
              {/* Icon with background and custom tooltip */}
              <div className="tooltip-container w-full">   
                <div
                  className={`w-full p-[12px_8px_5px_8px] sm:p-[12px_8px_5px_8px] flex flex-col items-center gap-2 cursor-pointer rounded-xl border ${item.border} transition-all duration-200 hover:scale-[1.02]`}
                  onClick={()=>handleIconClick(item.label)}
                >
                  <div className={`p-2 rounded-lg ${item.bg} ${item.text}`}>
                    {item.icon}
                  </div>
                  <span className={`font-semibold ${item.text}`}>{item.label}</span>
                </div>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
    {modelType === "Document" &&
    <DocsandCheckListModel visible={docModel} onCancel={handleDocCancel} applicationId={applicationId} token={token} setTriggerReport={setTriggerReport}/>
    }
    {modelType === "Notice" &&
    <NoticeModel visible={docModel} onCancel={handleDocCancel} applicationId={applicationId} token={token} bankCode={bankCode} banks={banks} initialData={initialData}/>
    }
    {modelType === "Report" &&
      <GenerateReportModel visible={docModel} onSuccess={handleDownloadApi} onCancel={handleDocCancel} type={"single"}/>
    }
    </>
  );
}


