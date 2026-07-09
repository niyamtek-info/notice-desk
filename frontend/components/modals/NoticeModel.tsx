import { ConfigProvider, Modal, Segmented } from 'antd';
import React, { useState } from 'react'
import Communication from '../pages/task-management/Communication';
import NoticeListTable from '../pages/task-management/NoticeListTable';

interface NoticeModelProps {
  visible: boolean
  onCancel: () => void
  applicationId: string;
  token: string;
  bankCode: string;
  banks: string;
  initialData?: any;
}

export default function NoticeModel({ visible, onCancel, applicationId, token, bankCode, banks, initialData }: NoticeModelProps) {

  const [type, setType] = useState<string>("Notice List")

  return (
    <>
      <Modal
        open={visible}
        onCancel={onCancel}
        width="100%"
        height="96%"
        footer={null}
        centered
        destroyOnClose
        className="docs-checklist-modal"
        title={<span className="text-[20px] font-bold text-stone-800 mb-0">
          Notice
        </span>}
      >


        <div className="flex justify-between items-center p-[5px_0px_0px_0px] z-10 bg-white sticky top-[30px] border-b border-gray-200 mb-4">
          {/* <span className="text-[20px] font-bold text-stone-800 mb-0">
              Notice
            </span>
            <div className="flex items-center gap-3 pr-[30px]">
              
            </div> */}
        </div>

        <div className="overflow-y-auto md:overflow-hidden md:h-[82vh]" style={{ maxHeight: '90vh' }}>
          <Communication initialApplicationId={applicationId} token={token} bankCode={bankCode} banks={banks} initialData={initialData} />
        </div>

      </Modal>
    </>
  )
}
