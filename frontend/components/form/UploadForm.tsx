"use client";
import React, { useEffect, useState } from "react";
import { InboxOutlined, EyeOutlined } from "@ant-design/icons";
import { Form, Select, Upload, Button, App, Modal, Input, Radio, Space } from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import { useAppNoContext } from "@/context/AppNoContext";
import { RiUploadCloud2Line } from "react-icons/ri";
import { FaRegCheckCircle } from "react-icons/fa";
import { addLog } from "@/src/utils/log";
import axios from "axios";
import { logoutUser } from "@/src/utils/auth";
import { useAppContext } from "@/context/GlobalContext";
import { BiCollapse } from "react-icons/bi";
import { IoMdExpand } from "react-icons/io";

const { Dragger } = Upload;
const { Option } = Select;

const DOC_TYPES = [
  { value: "Sanction_Letter", label: "Sanction Letter" },
  { value: "Loan_Agreement", label: "Loan Agreement" },
  {
    value: "Memorandum_of_Deposit_of_Title_Deeds",
    label: "Memorandum of Deposit of Title Deeds",
  },
  { value: "Sale_Deed", label: "Sale Deed" },
  { value: "Foreclosure_Statement", label: "Foreclosure Statement" },
  { value: "Statement_of_Accounts", label: "Statement of Accounts" },
  { value: "LegalReport", label: "Legal Report" },
];

const LANGUAGES = [
  { value: "english", label: "English" },
  { value: "tamil", label: "Tamil" },
];

const MAX_FILE_SIZE_MB = 50;

const parsePageRange = (rangeStr: string, maxPages: number): number[] => {
  const pages: Set<number> = new Set();
  const parts = rangeStr.split(",");
  for (const part of parts) {
    const trimmed = part.trim();
    if (trimmed.includes("-")) {
      const [startStr, endStr] = trimmed.split("-");
      const start = parseInt(startStr, 10);
      const end = parseInt(endStr, 10);
      if (!isNaN(start) && !isNaN(end)) {
        const from = Math.min(start, end);
        const to = Math.min(Math.max(start, end), maxPages);
        for (let i = from; i <= to; i++) {
          if (i >= 1 && i <= maxPages) {
            pages.add(i);
          }
        }
      }
    } else {
      const val = parseInt(trimmed, 10);
      if (!isNaN(val) && val >= 1 && val <= maxPages) {
        pages.add(val);
      }
    }
  }
  return Array.from(pages).sort((a, b) => a - b);
};

interface PageBatch {
  text: string;
  isValid: boolean;
  pagesCount: number;
}

const getPageBatches = (rangeStr: string, maxPages: number | null): PageBatch[] => {
  if (!rangeStr.trim()) return [];
  const parts = rangeStr.split(",");
  const batches: PageBatch[] = [];

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    if (trimmed.includes("-")) {
      const [startStr, endStr] = trimmed.split("-");
      const start = parseInt(startStr, 10);
      const end = parseInt(endStr, 10);

      if (!isNaN(start) && !isNaN(end)) {
        const from = Math.min(start, end);
        const to = Math.max(start, end);
        const isValid = from >= 1 && (maxPages === null || to <= maxPages);
        const pagesCount = to - from + 1;
        batches.push({
          text: `${from}-${to}`,
          isValid,
          pagesCount,
        });
      } else {
        batches.push({
          text: trimmed,
          isValid: false,
          pagesCount: 0,
        });
      }
    } else {
      const val = parseInt(trimmed, 10);
      if (!isNaN(val)) {
        const isValid = val >= 1 && (maxPages === null || val <= maxPages);
        batches.push({
          text: `${val}`,
          isValid,
          pagesCount: 1,
        });
      } else {
        batches.push({
          text: trimmed,
          isValid: false,
          pagesCount: 0,
        });
      }
    }
  }
  return batches;
};

interface UploadFormValues {
  docName: string;
  docType: string;
  docLang: string;
  docFormat: string;
}

interface UploadFormProps {
  docId?: string; // ✅ Changed from number to string
  initialDocType?: string;
  onUploadSuccess: (file: File) => void;
  onCancel?: () => void;
  recommendedDocs?: string[];
  setFileId?: (fileId: string, docType?: string) => void;
  setOpen: (open: boolean) => void;
  token?: string;
  formUpload?: any;
  previewUrl?: string | null;
  setPreviewUrl?: (previewUrl: string | null) => void;
  previewType?: string;
  setPreviewType?: (previewType: string) => void;
  fileList: any;
  setFileList: any;
  isPreviewExpanded: boolean;
  setIsPreviewExpanded: (val: boolean) => void;
}

export default function UploadForm({
  docId,
  initialDocType,
  onUploadSuccess,
  recommendedDocs = [],
  setFileId,
  setOpen,
  token,
  formUpload,
  previewUrl,
  setPreviewUrl,
  previewType,
  setPreviewType,
  fileList,
  setFileList,
  isPreviewExpanded,
  setIsPreviewExpanded,
}: UploadFormProps) {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const { applicationNumber } = useAppNoContext();

  const [fileError, setFileError] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewTitle, setPreviewTitle] = useState<string>("");

  const [canSubmit, setCanSubmit] = useState(false);

  const [docTypeOptions, setDocTypeOptions] = useState(DOC_TYPES);

  const { docFileId, setDocFileId } = useAppContext();

  const [totalPages, setTotalPages] = useState<number | null>(null);
  const [pageSelectionMode, setPageSelectionMode] = useState<"all" | "select">("all");
  const [customPageRange, setCustomPageRange] = useState<string>("");
  const [customPageTags, setCustomPageTags] = useState<string[]>([]);

  useEffect(() => {
    if (recommendedDocs.length > 0) {
      const extraOptions = recommendedDocs.map((doc) => ({
        value: doc.replace(/\s+/g, "_"), // Generate value similar to existing pattern
        label: doc, // Use the name as label
      }));

      const newOptions = [...DOC_TYPES];

      extraOptions.forEach((opt) => {
        // Check if value already exists
        const exists = newOptions.some(
          (existing) =>
            existing.value.toLowerCase() === opt.value.toLowerCase() ||
            existing.label.toLowerCase() === opt.label.toLowerCase(),
        );

        if (!exists) {
          newOptions.push(opt);
        }
      });
      // setDocTypeOptions(newOptions);
    }
  }, [recommendedDocs]);


  // Pre-fill document type if given
  useEffect(() => {
    if (initialDocType) {
      const norm = initialDocType.toLowerCase();
      const normalizedDocType =
        norm === "memorandum_of_deposit_of_title_deed"
          ? "memorandum_of_deposit_of_title_deeds"
          : norm;
      const matched = docTypeOptions.find(
        (d) =>
          d.label.toLowerCase() === normalizedDocType ||
          d.value.toLowerCase() === normalizedDocType,
      );
      if (matched) {
        formUpload.setFieldsValue({ docType: matched.value });
      } else {
        const capitalized =
          normalizedDocType.charAt(0).toUpperCase() + normalizedDocType.slice(1);
        formUpload.setFieldsValue({ docType: capitalized });
      }
    } else {
      formUpload.setFieldsValue({ docType: undefined });
    }
  }, [initialDocType, formUpload, docTypeOptions]);

  // Validate file before upload
  const beforeUpload = (file: File) => {
    if (!(file.type === "application/pdf" || file.type.startsWith("image/"))) {
      const msg = "You can only upload PDF or image files!";
      message.error(msg);
      setFileError(msg);
      return Upload.LIST_IGNORE;
    }
    if (file.size / 1024 / 1024 > MAX_FILE_SIZE_MB) {
      const msg = `File must be smaller than ${MAX_FILE_SIZE_MB} MB!`;
      message.error(msg);
      setFileError(msg);
      return Upload.LIST_IGNORE;
    }
    setFileError("");
    return false;
  };

  // Update file state and re-check submit availability
  const handleUploadChange = ({ fileList }: { fileList: UploadFile[] }) => {
    const lastFile = fileList.slice(-1);
    setFileList(lastFile);
    if (lastFile.length) setFileError("");
    checkCanSubmit(formUpload.getFieldsValue(), lastFile);

    // Auto-show preview when file is uploaded
    if (lastFile.length > 0 && lastFile[0].originFileObj) {
      const fileObj = lastFile[0].originFileObj as File;
      // Use setTimeout to ensure state update completes before preview
      formUpload.setFieldsValue({ docName: lastFile[0].name });
      setTimeout(() => {
        handlePreview(lastFile[0]);
      }, 100);

      // Parse PDF page count
      if (fileObj.type === "application/pdf") {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const arr = new Uint8Array(e.target?.result as ArrayBuffer);
            const decoder = new TextDecoder("latin1");
            const text = decoder.decode(arr);

            // Search for page nodes
            const matches = text.match(/\/Type\s*\/Page\b/g);
            let pageCount = matches ? matches.length : 0;

            if (pageCount === 0) {
              const countMatch = text.match(/\/Count\s+(\d+)/);
              if (countMatch) {
                pageCount = parseInt(countMatch[1], 10);
              }
            }

            if (pageCount > 0) {
              setTotalPages(pageCount);
              setCustomPageRange("");
              setCustomPageTags([]);
            } else {
              setTotalPages(null);
            }
          } catch (err) {
            console.error("Error parsing PDF page count:", err);
            setTotalPages(null);
          }
        };
        reader.readAsArrayBuffer(fileObj);
      } else {
        setTotalPages(null);
      }
    } else {
      setTotalPages(null);
      setCustomPageRange("");
      setCustomPageTags([]);
      setPageSelectionMode("all");
    }
  };

  // Handle preview functionality
  const handlePreview = (file: UploadFile) => {
    if (file.originFileObj) {
      const fileObj = file.originFileObj as File;

      const url = URL.createObjectURL(fileObj);

      setPreviewUrl?.(url);
      setPreviewTitle(file.name || "Preview");
      setPreviewVisible(true);

      // ✅ store type
      setPreviewType?.(fileObj.type);

    }
  };

  // Clean up preview URL when modal closes
  const handlePreviewCancel = () => {
    setPreviewVisible(false);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl?.(null);
    }
  };

  // Check if all required fields are filled and file is uploaded
  const checkCanSubmit = (
    values: Partial<UploadFormValues>,
    files = fileList,
  ) => {
    const allFieldsFilled = !!(
      values.docName &&
      values.docType &&
      values.docLang &&
      values.docFormat &&
      files.length > 0
    );
    setCanSubmit(allFieldsFilled);
  };

  // Trigger check whenever form values change
  const handleValuesChange = (_: unknown, allValues: UploadFormValues) => {
    checkCanSubmit(allValues);
  };

  const handleTagChange = (newValues: string[]) => {
    const formattedValues = newValues.map(val => {
      const trimmed = val.trim();
      if (!trimmed) return "";

      // If it already starts with "Page ", keep it
      if (trimmed.startsWith("Page ")) {
        return trimmed;
      }

      // Otherwise, parse and format it
      if (trimmed.includes("-")) {
        const [startStr, endStr] = trimmed.split("-");
        const start = parseInt(startStr, 10);
        const end = parseInt(endStr, 10);
        if (!isNaN(start) && !isNaN(end)) {
          return `Page ${Math.min(start, end)}-${Math.max(start, end)}`;
        }
      } else {
        const num = parseInt(trimmed, 10);
        if (!isNaN(num)) {
          return `Page ${num}`;
        }
      }
      return trimmed;
    }).filter(Boolean);

    setCustomPageTags(formattedValues);

    // Convert tags back to raw range string for extraction processing
    const rangeStr = formattedValues
      .map(v => v.replace("Page ", ""))
      .join(",");
    setCustomPageRange(rangeStr);
  };



  const handleSubmit = async (values: UploadFormValues) => {
    if (!fileList.length) {
      setFileError("Please upload a file.");
      return;
    }
    setFileError("");
    setLoading(true);

    try {
      const file = fileList[0].originFileObj as File;
      let fileToSend = file;

      // Extract specific pages if PDF and Select Pages is enabled
      if (previewType === "application/pdf" && pageSelectionMode === "select") {
        let pagesToExtract: number[] = [];
        if (customPageRange) {
          pagesToExtract = parsePageRange(customPageRange, totalPages || 1);
        }

        if (pagesToExtract.length === 0) {
          message.error("Please enter a valid page range.");
          setLoading(false);
          return;
        }

        try {
          const arrayBuffer = await file.arrayBuffer();
          const pdfBytes = new Uint8Array(arrayBuffer);

          const { PDFDocument } = await import("pdf-lib");
          const srcDoc = await PDFDocument.load(pdfBytes);
          const dstDoc = await PDFDocument.create();

          const indices = pagesToExtract
            .map((p) => p - 1)
            .filter((idx) => idx >= 0 && idx < srcDoc.getPageCount());

          if (indices.length === 0) {
            message.error("Selected pages are out of bounds.");
            setLoading(false);
            return;
          }

          const copiedPages = await dstDoc.copyPages(srcDoc, indices);
          copiedPages.forEach((page) => dstDoc.addPage(page));

          const newPdfBytes = await dstDoc.save();
          fileToSend = new File([newPdfBytes as any], file.name, {
            type: "application/pdf",
          });
        } catch (pdfErr) {
          console.error("Error splitting PDF:", pdfErr);
          message.error("Failed to extract pages from PDF. Sending original file.");
        }
      }

      const formData = new FormData();
      formData.append("document_name", values.docName);
      formData.append("doc_type", values.docType);
      // formData.append("language", values.docLang);
      // formData.append("format", values.docFormat);
      formData.append("file", fileToSend);
      formData.append("orginal_file", file);
      formData.append("application_number", applicationNumber);

      // ✅ Add docId if provided
      if (docId) {
        formData.append("doc_id", docId);
      }

      // Add selected pages to payload
      if (pageSelectionMode === "select") {
        let pagesToSend = "";
        if (customPageRange) {
          pagesToSend = customPageRange.trim();
        }

        if (pagesToSend) {
          formData.append("pages", pagesToSend);
          formData.append("page_range", pagesToSend);
        }
      }

      const endpoint = `${process.env.NEXT_PUBLIC_API_URL}/extract/process`;

      const res = await axios.post(endpoint, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
      });

      const data = res.data;

      if (data.file_id) {
        // Call success callback only after backend success
        onUploadSuccess(file);
        message.success(
          "File uploaded successfully. Extraction in progress...",
        );
        formUpload.resetFields();
        setFileList([]);
        setCanSubmit(false);
        setTotalPages(null);
        setCustomPageRange("");
        setCustomPageTags([]);
        setPageSelectionMode("all");
        // Add log to backend
        // await addLog(
        //   applicationNumber,
        //   "success",
        //   "upload",
        //   `${values.docType} uploaded successfully`
        // );
        setOpen(true);
        setFileId?.(data.file_id, values.docType);
        setDocFileId([...docFileId, data.file_id as string]);
      } else {
        message.error("Unexpected response from server.");
        await addLog(
          applicationNumber,
          "error",
          "upload",
          "Unexpected response from server",
        );
      }
    } catch (err: unknown) {
      console.error(err);
      const error = err as Error;
      // Axios error handling
      let msg = error.message || "Upload failed";
      if (axios.isAxiosError(err) && err.response) {
        if (err.response.status === 401) {
          logoutUser(false);
          return;
        }
        msg = err.response.data?.detail || err.message;
      }

      message.error(msg);
      await addLog(applicationNumber, "error", "upload", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-12 gap-4">
      {/* Preview Section */}
      <div className={isPreviewExpanded ? "col-span-12" : "col-span-6"}>
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold mb-0">Document Preview</h3>
            {previewVisible && previewUrl && (
              <Button
                type="text"
                icon={isPreviewExpanded ? <BiCollapse className="text-[20px]" /> : <IoMdExpand className="text-[20px]" />}
                onClick={() => setIsPreviewExpanded(!isPreviewExpanded)}
                className="text-primary-500 hover:text-primary-600 font-medium flex items-center gap-1.5"
              >
                {isPreviewExpanded ? "Collapse" : "Expand"}
              </Button>
            )}

          </div>
          {previewVisible && previewUrl ? (
            <div style={{ height: isPreviewExpanded ? "70vh" : "500px", overflow: "auto" }}>
              {previewType === "application/pdf" ? (
                <iframe
                  src={`${previewUrl}#toolbar=1`}
                  title="Document Preview"
                  width="100%"
                  height="100%"
                  style={{ border: "none" }}

                />
              ) : (
                <img
                  src={previewUrl}
                  alt="Document Preview"
                  style={{
                    width: "100%",
                    height: "auto",
                    maxHeight: isPreviewExpanded ? "70vh" : "500px",
                    objectFit: "contain",
                  }}
                />
              )}
            </div>
          ) : (
            <div className={`flex items-center justify-center bg-gray-100 rounded ${isPreviewExpanded ? "h-[70vh]" : "h-[450px]"}`}>
              <p className="text-gray-500">No document preview available</p>
            </div>
          )}
        </div>
      </div>
      {!isPreviewExpanded && (
        <div className="col-span-6">
          <Form
            form={formUpload}
            className="doc_upload"
            layout="vertical"
            onFinish={handleSubmit}
            onValuesChange={handleValuesChange}
            autoComplete="off"
            initialValues={{
              docLang: "english",
              docFormat: "Typed",
              docType: "",
            }}
          >
            {/* File Upload */}
            <Form.Item
              label="File Upload"
              required
              validateStatus={fileError ? "error" : ""}
              help={fileError || ""}
              valuePropName="fileList"
              getValueFromEvent={(e) => e && e.fileList}
              className="!mt-4"
            >
              <Dragger
                name="file"
                accept="application/pdf,image/*"
                multiple={false}
                beforeUpload={beforeUpload}
                onChange={handleUploadChange}
                fileList={fileList}
                onRemove={() => {
                  setFileList([]);
                  checkCanSubmit(formUpload.getFieldsValue(), []);
                }}
                showUploadList={false}
                style={{
                  padding: 0,
                  background: "transparent",
                  borderRadius: "7px",
                }}
              >
                <div className="py-1.5">
                  {fileList.length > 0 ? (
                    <>
                      <p className="mb-4 flex justify-center">
                        <FaRegCheckCircle className="text-green-500 text-[60px]" />
                      </p>
                      <p className="text-lg font-medium text-gray-700 mb-1">
                        {fileList[0].name}
                      </p>
                      <p className="text-sm text-green-600 mb-3">
                        File selected and ready to process
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="mb-2 flex justify-center">
                        <RiUploadCloud2Line className="text-primary-500 text-[40px]" />
                      </p>
                      <p className="text-md mb-2">
                        Click or drag file to this area to upload
                      </p>
                      <p className="text-xs">
                        Support for a single PDF or image upload. No company data
                        or banned files.
                      </p>
                    </>
                  )}
                </div>
              </Dragger>
            </Form.Item>


            {/* Page Selection Controls */}
            {fileList.length > 0 && previewType === "application/pdf" && (
              <div className="bg-gray-50/50 rounded-lg p-1 mb-4">
                <Form.Item
                  label="Pages to Process"
                  required
                  rules={[
                    { required: true, message: "Please choose page selection" },
                  ]}
                  className="!mb-2 font-medium"
                >
                  <Radio.Group
                    value={pageSelectionMode}
                    onChange={(e) => setPageSelectionMode(e.target.value)}
                    className="w-full flex"
                  >
                    <Radio.Button value="all" className="flex-1 text-center">
                      All Pages {totalPages ? `(${totalPages})` : ""}
                    </Radio.Button>
                    <Radio.Button value="select" className="flex-1 text-center">
                      Select Pages
                    </Radio.Button>
                  </Radio.Group>
                </Form.Item>

                {pageSelectionMode === "select" && (
                  <div className="mt-3 space-y-3">
                    <Form.Item
                      label="Custom Page Range / Numbers"
                      help="Enter specific pages or range (e.g. 1, 2, 5 or 1-3)"
                      className="!mb-0"
                    >
                      <Select
                        mode="tags"
                        tokenSeparators={[","]}
                        placeholder="e.g. 1, 3, 5-8"
                        value={customPageTags}
                        onChange={handleTagChange}
                        className="w-full custom-form-field"
                        style={{ minHeight: "40px" }}
                        dropdownStyle={{ display: "none" }}
                        open={false}
                        suffixIcon={null}
                      />
                    </Form.Item>
                  </div>
                )}
              </div>
            )}

            <Form.Item
              label="Document Name"
              name="docName"
              rules={[
                { required: true, message: "Please enter a document name" },
              ]}
            >
              <Input
                placeholder="Enter Document Name"
                className="h-[40px] rounded-md"
              />
            </Form.Item>

            {/* Document Type */}
            <Form.Item
              label="Document Type"
              name="docType"
              rules={[
                { required: true, message: "Please select a document type" },
              ]}
            >
              {initialDocType ? (
                <Select disabled className="custom-form-field">
                  {docTypeOptions.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              ) : (
                <Select
                  placeholder="Select Document Type"
                  allowClear
                  className="custom-form-field"
                >
                  {docTypeOptions.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              )}
            </Form.Item>


            {/* Document Language */}
            {/* <Form.Item
            label="Document Language"
            name="docLang"
            rules={[{ required: true, message: "Please select a language" }]}
          >
            <Select
              placeholder="Select Document Language"
              allowClear
              className="custom-form-field"
            >
              {LANGUAGES.map((lang) => (
                <Option key={lang.value} value={lang.value}>
                  {lang.label}
                </Option>
              ))}
            </Select>
          </Form.Item> */}

            {/* Document Format */}
            {/* <Form.Item
            label="Document Format"
            name="docFormat"
            rules={[
              { required: true, message: "Please select a document format" },
            ]}
          >
            <Select
              placeholder="Select Document Format"
              allowClear
              className="custom-form-field"
            >
              <Option value="Typed">Typed</Option>
              <Option value="Handwritten">Handwritten</Option>
            </Select>
          </Form.Item> */}

            <div>
              <p className="mb-[5px] text-gray-600 font-semibold">
                <span className="font-bold">Note: </span>Accept both printed and
                handwritten documents.
              </p>
            </div>

            {/* Submit Button */}
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                block
                loading={loading}
                disabled={loading}
                style={{
                  backgroundColor: "var(--color-primary-500)",
                  borderRadius: "7px",
                  height: "40px",
                  color: "#fff",
                  opacity: loading ? 0.5 : 1,
                }}
              >
                {loading ? "Processing..." : "Upload"}
              </Button>
            </Form.Item>
          </Form>
        </div>
      )}
    </div>
  );
}