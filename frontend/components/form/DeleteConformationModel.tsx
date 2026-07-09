import { Modal } from 'antd';
import React from 'react'

interface DeleteProps {
    deleteModel:any;
    setDeleteModel:any;
    handleConfirmOk:any;
}

export default function DeleteConformationModel({deleteModel,setDeleteModel,handleConfirmOk}:DeleteProps) {
  return (
    <>
      {/* Confirmation Modal */}
      <Modal
        open={deleteModel?.open}
        onOk={() => {
          handleConfirmOk(deleteModel);
        }}
        onCancel={() => setDeleteModel({open:false, type:"", value:null})}
        okText="Delete"
        okType="danger"
        okButtonProps={{
          className: " hover:!text-white hover:!bg-[#ff4d4f] border-red-600",
        }}
        cancelText="Cancel"
        title="Are you sure?"
        zIndex={1100}
      >
        <p>{`Are you sure you want to delete this ${deleteModel?.type || ""} details ?`}</p>
      </Modal>
    </>
    )
}
