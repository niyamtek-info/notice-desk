"use client";

import React from 'react';
import { Modal, Button } from 'antd';
import { useDispatch, useSelector } from 'react-redux';
import { RootState, AppDispatch } from '@/store';
import { setSessionExpired } from '@/store/slices/loginSlice';
import { SIGN_IN_PATH } from '@/src/utils/auth';
import { RiErrorWarningLine } from "react-icons/ri";

const SessionExpiryModal: React.FC = () => {
    const dispatch = useDispatch<AppDispatch>();
    const sessionExpired = useSelector((state: RootState) => state.login.sessionExpired);

    const handleLogin = () => {
        // Redirection to sign-in page
        window.localStorage.removeItem("token");
        localStorage.removeItem("notice_editor_draft");
        dispatch(setSessionExpired(false));
        window.location.replace(SIGN_IN_PATH);
    };

    return (
        <Modal
            title={null}
            open={sessionExpired}
            footer={null}
            centered
            closable={false}
            maskClosable={false}
            width={450}
            className="session-expiry-modal"
        >
            <div className="py-4 px-4 text-center">
                <div className="mb-1 flex justify-center">
                    <div className="bg-orange-50 p-4 rounded-full">
                        <RiErrorWarningLine className="text-orange-500 text-[60px]" />
                    </div>
                </div>

                <h2 className="text-[22px] font-bold text-gray-900 mb-2">Session Expired</h2>
                <p className="text-[16px] text-gray-500 mb-8">
                    Your session was expired please login
                </p>

                <Button
                    type="primary"
                    onClick={handleLogin}
                    className="bg-primary-500 hover:bg-blue-600 h-[45px] w-full rounded-md font-semibold text-[16px] text-white shadow-md transition-all"
                >
                    Login
                </Button>
            </div>

            <style jsx global>{`
                .session-expiry-modal .ant-modal-content {
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
                }
            `}</style>
        </Modal>
    );
};

export default SessionExpiryModal;
