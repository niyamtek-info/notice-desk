'use client';

import React, { useEffect, useRef, useState } from "react";
import { Form, Input, Button, Select, DatePicker, Upload, message, Result, Modal } from "antd";
import type { UploadFile } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useRouter } from "next/navigation";
import { useAppDispatch } from "@/store/hooks";
import { addApplication } from "@/store/slices/applicationsSlice";
import Link from "next/link";
import dayjs from "dayjs";
import { motion } from "framer-motion";
import { useAppNoContext } from "@/context/AppNoContext";
import { addLog } from "@/src/utils/log";
import usePageTitle from "@/hooks/usePageTitle";
import { ApplicationApi } from "@/src/services/ApplicationApi";


const { Option } = Select;

export default function LoanPropertyForm() {
  const [form] = Form.useForm();
  const [phase, setPhase] = useState(1);
  const [propertyType, setPropertyType] = useState<string>("");
  const [propertyImages, setPropertyImages] = useState<UploadFile[]>([]);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [successModalOpen, setSuccessModalOpen] = useState(false);
  const { setApplicationNumber } = useAppNoContext();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const [messageApi, contextHolder] = message.useMessage();
  const phase2Ref = useRef<HTMLDivElement | null>(null);
  const phase3Ref = useRef<HTMLDivElement | null>(null);

  usePageTitle('Loan & Property Application');

  useEffect(() => {
    const saved = localStorage.getItem("loanPropertyForm");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed.LOAN_REQUEST_DATE) {
        parsed.LOAN_REQUEST_DATE = dayjs(parsed.LOAN_REQUEST_DATE);
      }
      form.setFieldsValue(parsed);
      if (parsed.PROPERTY_TYPE) setPropertyType(parsed.PROPERTY_TYPE);
      if (parsed.IMAGES) setPropertyImages(parsed.IMAGES);
      if (parsed.PHASE) setPhase(parsed.PHASE);
    }
  }, [form]);

  const saveToLocalStorage = (extra: object = {}) => {
    const values = form.getFieldsValue(true);
    const allData = {
      ...values,
      IMAGES: propertyImages,
      PHASE: phase,
      ...extra,
    };
    localStorage.setItem("loanPropertyForm", JSON.stringify(allData));
  };

  const handleSavePhase1 = async () => {
    try {
      await form.validateFields([
        "LOAN_REQUESTER_NAME",
        "LOAN_REQUEST_AMOUNT",
        "LOAN_REQUEST_DATE",
        "PRE_APPREOVAL_AMOUNT",
        "PREAPPROVAL_STATUS",
      ]);
      saveToLocalStorage({ PHASE: Math.max(phase, 2) });
      setPhase((p) => {
        const next = Math.max(p, 2);
        if (next === 2) {
          setTimeout(() => {
            if (phase2Ref.current) {
              const y = phase2Ref.current.getBoundingClientRect().top + window.scrollY - 95;
              window.scrollTo({ top: y, behavior: "smooth" });
            }
          }, 300);
        }
        return next;
      });
      messageApi.success("Loan Info saved!");
      const applicationNumber = Number(localStorage.getItem("applicationNumber"));
      if (applicationNumber) {
        await addLog(String(applicationNumber), "success", "loan-info-saved", "Loan info section completed");
      }
    } catch { }
  };

  const handleSavePhase2 = async () => {
    try {
      await form.validateFields([
        "PROPERTY_TYPE",
        "SURVEY_NO",
        "SUBDIVISION",
        "PROPERTY_STREET",
        "PROPERTY_LOCALITY",
        "PROPERTY_TOWN",
        "TALUK",
        "VILLAGE",
        "DISTRICT",
        "PINCODE",
        "ZONE",
        "STATE",
      ]);
      saveToLocalStorage({ PHASE: Math.max(phase, 3) });
      setPhase((p) => {
        const next = Math.max(p, 3);
        if (next === 3) {
          setTimeout(() => {
            if (phase3Ref.current) {
              const y = phase3Ref.current.getBoundingClientRect().top + window.scrollY - 95;
              window.scrollTo({ top: y, behavior: "smooth" });
            }
          }, 300);
        }
        return next;
      });
      messageApi.success("Property Info saved!");
      const applicationNumber = Number(localStorage.getItem("applicationNumber"));
      if (applicationNumber) {
        await addLog(String(applicationNumber), "success", "property-info-saved", "Property info section completed");
      }
    } catch { }
  };

  const handleSubmit = async () => {
    try {
      await form.validateFields();

      // Use properties directly but strip domain for storage to save space
      const processedImages = propertyImages.map(img => {
        if (img.response && img.response.url) {
          // Keep only the relative path /uploads/filename.ext
          return {
            ...img,
            thumbUrl: img.response.url,
            url: img.response.url
          };
        }
        return img;
      });

      const values = form.getFieldsValue(true);
      const payload = {
        LOAN_INFO: {
          LOAN_REQUESTER_NAME: values.LOAN_REQUESTER_NAME,
          LOAN_REQUEST_AMOUNT: values.LOAN_REQUEST_AMOUNT,
          LOAN_REQUEST_DATE: values.LOAN_REQUEST_DATE?.format("DD-MM-YYYY") || "",
          PRE_APPREOVAL_AMOUNT: values.PRE_APPREOVAL_AMOUNT,
          PREAPPROVAL_STATUS: values.PREAPPROVAL_STATUS,
        },
        PROPERTY_INFO: {
          PROPERTY_TYPE: values.PROPERTY_TYPE,
          SURVEY_NO: values.SURVEY_NO,
          SUBDIVISION: values.SUBDIVISION,
          PLOT_NUMBER: values.PLOT_NUMBER,
          DOOR_NUMBER: values.DOOR_NUMBER,
          BUILDING_NAME: values.BUILDING_NAME,
          FLOOR: values.FLOOR,
          PROPERTY_STREET: values.PROPERTY_STREET,
          PROPERTY_LOCALITY: values.PROPERTY_LOCALITY,
          PROPERTY_TOWN: values.PROPERTY_TOWN,
          TALUK: values.TALUK,
          VILLAGE: values.VILLAGE,
          DISTRICT: values.DISTRICT,
          PINCODE: values.PINCODE,
          ZONE: values.ZONE,
          STATE: values.STATE,
          EXTENT: values.EXTENT,
          LATITUDE: values.LATITUDE,
          LONGITUDE: values.LONGITUDE,
          APPARTMENT_SIZE: values.APPARTMENT_SIZE,
          RERA_NO: values.RERA_NO,
          RERA_STATUS: values.RERA_STATUS,
          UDS: values.UDS,
          PROMOTOR: values.PROMOTOR,
          NAME_OF_THE_PROJECT: values.NAME_OF_THE_PROJECT,
          PROPERTY_TAX_NUMBER: values.PROPERTY_TAX_NUMBER,
          WATERCONNECTION_NUMBER: values.WATERCONNECTION_NUMBER,
          ELECTRICITY_CONNECTION_NUMBER: values.ELECTRICITY_CONNECTION_NUMBER,
          PLAN_APPROVAL_STATUS: values.PLAN_APPROVAL_STATUS,
          PLAN_APPROVAL_NUMBER: values.PLAN_APPROVAL_NUMBER,
          BUILDING_YEAR: values.BUILDING_YEAR,
          BUILDING_VALUE: values.BUILDING_VALUE,
          SRO_OFFICE: values.SRO_OFFICE,
          PATTA_NUMBER: values.PATTA_NUMBER,
          IMAGES: processedImages,
        },
      };
      // ...


      const json: any = await ApplicationApi.create({ data: payload });

      dispatch(addApplication(json));
      const appId = json.business_code || json.record_id;
      setApplicationId(appId);

      if (appId) {
        localStorage.setItem("applicationNumber", appId);
        await addLog(
          appId,
          "success",
          "application-create",
          `Loan requested by ${values.LOAN_REQUESTER_NAME} for amount ${values.LOAN_REQUEST_AMOUNT}`
        );
      }
      setPhase(4);
      setSuccessModalOpen(true);
      localStorage.removeItem("loanPropertyForm");
    } catch (err: any) {
      console.error("Submission failed:", err);
      messageApi.error(err.message || "Submission failed");
    }
  };

  const buttonClass =
    "flex items-center !text-gray-50 !bg-primary-500 hover:bg-blue-800 font-medium rounded-lg text-md !px-4 !py-3 mb-2 cursor-pointer";

  // ---- CATEGORY OPTIONS (update here when needed) ----
  const propertyCategories = [
    { value: "land(vacant)", label: "Land (Vacant)" },
    { value: "land and building", label: "Land and Building" },
    { value: "new apartment", label: "New Apartment" },
    { value: "old apartment", label: "Old Apartment (Second Hand Sales)" },
    { value: "industrial land and building", label: "Industrial Land and Building" },
    { value: "state housing board property", label: "State Housing Board Property" },
    { value: "agriculture land", label: "Agriculture Land" },
    { value: "state industrial promotion land", label: "State Industrial Promotion Land (SIPCOT, APISC, CIDCO)" },
  ];

  return (
    <div className="mx-auto py-6" id="loan-property-form">
      {contextHolder}
      {/* <h2 className="text-[24px] font-bold text-gray-700 mb-5">Loan & Property Application</h2> */}
      <Form form={form} layout="vertical">
        {/* ---------------- PHASE 1 ---------------- */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="rounded-lg p-6 mb-6 shadow-md bg-white"
        >
          <h3 className="text-[20px] font-semibold mb-6 text-gray-800">Loan Info</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Form.Item name="LOAN_REQUESTER_NAME" label="Loan Requester Name" rules={[{ required: true }]}>
              <Input className="custom-input-field" />
            </Form.Item>
            <Form.Item name="LOAN_REQUEST_AMOUNT" label="Loan Request Amount" rules={[{ required: true }]}>
              <Input className="custom-input-field" />
            </Form.Item>
            <Form.Item name="LOAN_REQUEST_DATE" label="Loan Request Date" rules={[{ required: true }]}>
              <DatePicker className="custom-input-field w-full" />
            </Form.Item>
            <Form.Item name="PRE_APPREOVAL_AMOUNT" label="Pre-Approval Amount">
              <Input className="custom-input-field" />
            </Form.Item>
            <Form.Item name="PREAPPROVAL_STATUS" label="Pre-Approval Status" rules={[{ required: true }]}>
              <Select className="custom-select-field">
                <Option value="Yes">Yes</Option>
                <Option value="No">No</Option>
              </Select>
            </Form.Item>
          </div>
          <div className="flex justify-end mt-4">
            <Button type="primary" onClick={handleSavePhase1} className={buttonClass}>
              Save & Continue
            </Button>
          </div>
        </motion.div>

        {/* ---------------- PHASE 2 ---------------- */}
        {phase >= 2 && (
          <motion.div
            ref={phase2Ref}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="rounded-lg p-6 mb-6 shadow-md bg-white"
          >
            <h3 className="text-lg font-semibold mb-6 text-gray-800">Property Info</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Form.Item name="PROPERTY_TYPE" label="Property Type" rules={[{ required: true }]}>
                <Select onChange={setPropertyType} className="custom-select-field">
                  {propertyCategories.map((cat) => (
                    <Option key={cat.value} value={cat.value}>{cat.label}</Option>
                  ))}
                </Select>
              </Form.Item>
              {/* ---- Survey No and Subdivision fields moved immediately after property type ---- */}
              <Form.Item name="SURVEY_NO" label="Survey No" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="SUBDIVISION" label="Subdivision" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              {propertyType === "land(vacant)" && (
                <Form.Item name="PLOT_NUMBER" label="Plot Number" rules={[{ required: true }]}>
                  <Input className="custom-input-field" />
                </Form.Item>
              )}
              {(propertyType === "new apartment" || propertyType === "old apartment" || propertyType === "land and building" || propertyType === "industrial land and building" || propertyType === "state housing board property" || propertyType === "state industrial promotion land") && (
                <>
                  <Form.Item name="DOOR_NUMBER" label="Door Number" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="BUILDING_NAME" label="Building Name" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                </>
              )}
              {(propertyType === "new apartment" || propertyType === "old apartment") && (
                <>
                  <Form.Item name="FLOOR" label="Floor" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="APPARTMENT_SIZE" label="Apartment / Property Size" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="UDS" label="UDS">
                    <Input className="custom-input-field" />
                  </Form.Item>
                </>
              )}
              {propertyType === "new apartment" && (
                <>
                  <Form.Item name="RERA_NO" label="RERA No" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="RERA_STATUS" label="RERA Status" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="PROMOTOR" label="Promotor" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="NAME_OF_THE_PROJECT" label="Name of the Project" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                </>
              )}
              {/* Common */}
              <Form.Item name="PROPERTY_STREET" label="Property Street" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="PROPERTY_LOCALITY" label="Property Locality" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="PROPERTY_TOWN" label="Property Town" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="TALUK" label="Taluk" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="VILLAGE" label="Village" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="DISTRICT" label="District" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="PINCODE" label="Pincode" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="ZONE" label="Zone" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="STATE" label="State" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
            </div>
            <div className="flex justify-end mt-4">
              <Button type="primary" onClick={handleSavePhase2} className={buttonClass}>
                Save & Continue
              </Button>
            </div>
          </motion.div>
        )}
        {/* ---------------- PHASE 3 ---------------- */}
        {phase >= 3 && (
          <motion.div
            ref={phase3Ref}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="rounded-lg p-6 mb-6 shadow-md bg-white"
          >
            <h3 className="text-lg font-semibold mb-6 text-gray-800">Additional Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {(propertyType === "new apartment" || propertyType === "old apartment" || propertyType === "land and building" || propertyType === "industrial land and building" || propertyType === "state housing board property" || propertyType === "state industrial promotion land") && (
                <>
                  <Form.Item name="PLAN_APPROVAL_STATUS" label="Plan Approval Status" >
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="PLAN_APPROVAL_NUMBER" label="Plan Approval Number">
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="BUILDING_YEAR" label="Building Year" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                  <Form.Item name="BUILDING_VALUE" label="Building Value" rules={[{ required: true }]}>
                    <Input className="custom-input-field" />
                  </Form.Item>
                </>
              )}

              {/* Common */}
              <Form.Item name="PROPERTY_TAX_NUMBER" label="Property Tax Number" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="WATERCONNECTION_NUMBER" label="Water Connection Number" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="ELECTRICITY_CONNECTION_NUMBER" label="Electricity Connection Number" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="SRO_OFFICE" label="SRO Office">
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="PATTA_NUMBER" label="Patta Number" rules={[{ required: true }]}>
                <Input className="custom-input-field" />
              </Form.Item>

              <Form.Item name="EXTENT" label="Extent" >
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="LATITUDE" label="Latitude">
                <Input className="custom-input-field" />
              </Form.Item>
              <Form.Item name="LONGITUDE" label="Longitude">
                <Input className="custom-input-field" />
              </Form.Item>

              <Form.Item
                name="IMAGES_REQUIRED"
                label="Upload Property Images"
                rules={[{ required: propertyImages.length === 0, message: "Please upload at least one image" }]}
                className="col-span-2"
              >
                <Upload
                  listType="picture-card"
                  fileList={propertyImages}
                  action={ApplicationApi.getUploadUrl()}
                  onChange={({ fileList }) => {
                    const newFileList = fileList.map(file => {
                      if (file.status === 'done' && file.response) {
                        // Construct absolute URL for display purposes in the UI
                        // Assuming NEXT_PUBLIC_API_URL ends with /api/v1, we need to go up two levels or just use the root.
                        // Since we don't have the root variable easily, and we know the structure:
                        // API: http://localhost:8000/api/v1
                        // Static: http://localhost:8000/uploads

                        const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
                        // Remove /api/v1 suffix if present to get root
                        const rootBase = apiBase.replace(/\/api\/v1\/?$/, '');

                        const fullUrl = `${rootBase}${file.response.url}`;

                        return {
                          ...file,
                          thumbUrl: fullUrl,
                          url: fullUrl
                        };
                      }
                      return file;
                    });
                    setPropertyImages(newFileList);
                    saveToLocalStorage();
                    const applicationNumber = Number(localStorage.getItem("applicationNumber"));
                    if (applicationNumber && fileList.length > 0) {
                      const lastFile = fileList[fileList.length - 1];
                      if (lastFile.status === 'done') {
                        addLog(String(applicationNumber), "success", "document-upload", `${lastFile.name} uploaded`);
                      }
                    }
                  }}
                  multiple
                >
                  {propertyImages.length >= 8 ? null : (
                    <div>
                      <PlusOutlined />
                      <div style={{ marginTop: 8 }}>Upload</div>
                    </div>
                  )}
                </Upload>
              </Form.Item>
            </div>
            <div className="flex justify-end mt-4">
              <Button type="primary" onClick={handleSubmit} className={buttonClass}>
                Submit
              </Button>
            </div>
          </motion.div>
        )}
      </Form>
      {/* Success Modal */}
      <Modal open={successModalOpen} closable={false} footer={null} centered>
        <Result
          status="success"
          title="Application Submitted Successfully"
          subTitle={
            <p className="text-lg">
              Your Application ID is:{" "}
              <Link href={`/application-details/${applicationId}`} className="font-bold text-primary-500 underline">
                {applicationId}
              </Link>
            </p>
          }
          extra={
            <Button
              type="primary"
              onClick={() => {
                if (applicationId) {
                  setApplicationNumber(applicationId.toString()); // 🔥 update context
                  router.push(`/application-details/${applicationId}`);
                }
              }}
              className={buttonClass}
            >
              Go to Info
            </Button>
          }
        />
      </Modal>
    </div>
  );
}
