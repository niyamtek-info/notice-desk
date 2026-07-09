'use client';

import React, { useEffect, useState } from "react";
import { Form, Button, Modal, Image, Spin } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import config from "@/config";
import { useAppNoContext } from "@/context/AppNoContext";

const MetaSection: React.FC<{ title: string; children: React.ReactNode }> = ({
    title,
    children,
}) => (
    <div>
        <h2 className="text-[18px] font-bold border-b-1 text-gray-800 border-gray-100 px-5 py-3.5 mb-3">
            {title}
        </h2>
        {children}
    </div>
);

interface MetaDisplayProps {
    label: string;
    value: string | null | undefined;
}

const formatLabel = (key: string) => {
    return key
        .replace(/_/g, " ")
        .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase())
        .trim();
};

const MetaDisplay: React.FC<MetaDisplayProps> = ({ label, value }) => {
    return (
        <div className="mb-4">
            <p className="text-gray-800 pb-1 text-md font-semibold mb-1">{label}</p>
            <p className="text-gray-800 border-1 border-gray-100 p-2 rounded-lg text-sm mb-0 bg-gray-20">
                {value || '-'}
            </p>
        </div>
    );
};

const LoanPropertyInfoContent: React.FC = () => {
    const [form] = Form.useForm();
    const [photoModalVisible, setPhotoModalVisible] = useState<boolean>(false);
    const [currentPhotoIndex, setCurrentPhotoIndex] = useState<number>(0);
    const [loading, setLoading] = useState<boolean>(false);
    const [propertyPhotos, setPropertyPhotos] = useState<string[]>([]);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [data, setData] = useState<Record<string, any> | null>(null);
    const [loadingData, setLoadingData] = useState(true);

    const { applicationNumber } = useAppNoContext();
    const appId = applicationNumber;

    // Fetch application data
    useEffect(() => {
        if (!appId) return;

        setLoadingData(true);
        fetch(`${process.env.NEXT_PUBLIC_API_URL}/applications/${appId}`)
            .then((res) => {
                if (!res.ok) throw new Error(`Failed to fetch application ${appId}, status: ${res.status}`);
                return res.json();
            })
            .then((json) => {
                setData(json);

                const appData = json.data || {};
                const propertyInfo = appData.PROPERTY_INFO || appData.propertyInfo || {};

                setPropertyPhotos(
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    (propertyInfo.IMAGES || propertyInfo.images || []).map((img: Record<string, any>) => {
                        const url = img.thumbUrl || img.url || "";
                        if (url.startsWith("/")) {
                            const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
                            const rootBase = apiBase.replace(/\/api\/v1\/?$/, "");
                            return `${rootBase}${url}`;
                        }
                        return url;
                    })
                );
            })
            .catch((error) => {
                console.error("Fetch error:", error);
                setData(null);
            })
            .finally(() => setLoadingData(false));
    }, [appId]);

    const deletePhoto = (index: number) => {
        const updated = [...propertyPhotos];
        updated.splice(index, 1);
        setPropertyPhotos(updated);
        if (currentPhotoIndex >= updated.length) {
            setCurrentPhotoIndex(Math.max(updated.length - 1, 0));
        }
    };

    const showNextPhoto = () => {
        if (currentPhotoIndex < propertyPhotos.length - 1) {
            setLoading(true);
            setTimeout(() => {
                setCurrentPhotoIndex(prev => prev + 1);
                setLoading(false);
            }, 300);
        }
    };

    const showPreviousPhoto = () => {
        if (currentPhotoIndex > 0) {
            setLoading(true);
            setTimeout(() => {
                setCurrentPhotoIndex(prev => prev - 1);
                setLoading(false);
            }, 300);
        }
    };

    if (loadingData) {
        return <div className="h-full flex items-center justify-center min-h-[400px]"><Spin tip="Loading..." /></div>;
    }

    if (!data) {
        return <div>No application data found for ID: {appId}</div>;
    }

    const appData = (data.data as Record<string, unknown>) || {};
    const loanInfo = (appData.LOAN_INFO as Record<string, unknown>) || (appData.loanInfo as Record<string, unknown>) || {};
    const propertyInfo = (appData.PROPERTY_INFO as Record<string, unknown>) || (appData.propertyInfo as Record<string, unknown>) || {};

    return (
        <>
            <Form form={form} layout="vertical">
                {/* Loan Info Section */}
                <div className="bg-white shadow-md border-gray-100 rounded-lg mb-3">
                    <MetaSection title={`${config.name} Info`}>
                        <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4 px-5">
                            <MetaDisplay label="Application ID" value={data.business_code || "-"} />
                            {Object.entries(loanInfo).map(([key, value], i) => (
                                <MetaDisplay key={i} label={formatLabel(key)} value={value as string} />
                            ))}
                        </div>
                    </MetaSection>
                </div>

                {/* Property Info Section */}
                <div className="bg-white shadow-md border-gray-100 rounded-lg">
                    <MetaSection title="Property Info">
                        <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4 px-5">
                            {Object.entries(propertyInfo)
                                .filter(([key]) => key !== "IMAGES" && key !== "images")
                                .map(([key, value], i) => (
                                    <MetaDisplay key={i} label={formatLabel(key)} value={value as string} />
                                ))}

                            <div className="flex items-center mb-4 pt-6">
                                <Button
                                    className="flex items-center !text-primary-500 !bg-primary-10 !border-transparent hover:!border-primary-500 font-medium rounded-lg text-sm px-4 !h-[40px] w-full justify-center cursor-pointer"
                                    onClick={() => setPhotoModalVisible(true)}
                                >
                                    Property Photos
                                </Button>
                            </div>
                        </div>
                    </MetaSection>
                </div>
            </Form>

            {/* Photo Viewer Modal */}
            <Modal
                title="Property Photo Viewer"
                open={photoModalVisible}
                onCancel={() => setPhotoModalVisible(false)}
                footer={null}
                width={600}
                centered
            >
                {propertyPhotos.length > 0 ? (
                    <div className="p-2 border border-gray-200 rounded-lg bg-white w-full max-w-[600px] flex justify-center items-center">
                        <Image
                            src={propertyPhotos[currentPhotoIndex]}
                            alt="Main"
                            preview={{ mask: <span style={{ fontSize: 16 }}>Click to Zoom</span> }}
                            style={{ maxWidth: "100%", maxHeight: "400px", objectFit: "contain", borderRadius: "8px" }}
                        />
                    </div>
                ) : (
                    <div className="h-[250px] flex items-center justify-center">No photos uploaded.</div>
                )}

                {propertyPhotos.length > 0 && (
                    <div className="flex overflow-x-auto mt-4 gap-4 px-2 pb-2">
                        {propertyPhotos.map((photo, index) => (
                            <div
                                key={index}
                                className={`relative group cursor-pointer rounded border-2 ${index === currentPhotoIndex ? "border-blue-400" : "border-gray-200"
                                    }`}
                                onClick={() => setCurrentPhotoIndex(index)}
                            >
                                <img src={photo} alt={`Thumb ${index + 1}`} className="h-20 w-28 object-cover rounded" />
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        deletePhoto(index);
                                    }}
                                    className="absolute top-1 right-1 bg-white text-red-500 rounded-full p-1 shadow hidden group-hover:block"
                                    aria-label="Delete Photo"
                                >
                                    <DeleteOutlined style={{ fontSize: 16, color: "red" }} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                <div className="flex justify-end mt-4 space-x-2">
                    {loading || currentPhotoIndex === 0 ? (
                        ""
                    ) : (
                        <Button
                            onClick={showPreviousPhoto}
                            disabled={loading || currentPhotoIndex === 0}
                            className="flex items-center !text-gray-50 !bg-primary-500 hover:bg-blue-800 font-medium rounded-lg text-sm px-4 py-2 cursor-pointer"
                        >
                            Previous
                        </Button>
                    )}
                    {loading || currentPhotoIndex >= propertyPhotos.length - 1 ? (
                        ""
                    ) : (
                        <Button
                            onClick={showNextPhoto}
                            disabled={loading || currentPhotoIndex >= propertyPhotos.length - 1}
                            className="flex items-center !text-gray-50 !bg-primary-500 hover:bg-blue-800 font-medium rounded-lg text-sm px-4 py-2 cursor-pointer"
                        >
                            Next
                        </Button>
                    )}
                </div>
            </Modal>
        </>
    );
};

export default LoanPropertyInfoContent;
