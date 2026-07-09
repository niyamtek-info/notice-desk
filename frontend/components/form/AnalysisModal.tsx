"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Modal,
  Form,
  Input,
  Button,
  FormInstance,
  Select,
  message,
  Collapse,
  Table,
  Segmented,
  ConfigProvider,
} from "antd";
import { BiCollapse, BiExpand } from "react-icons/bi";
import { IoMdExpand } from "react-icons/io";
import { useAppContext } from "@/context/GlobalContext";

// Add CSS styles to override Ant Design column constraints
if (typeof window !== "undefined") {
  const style = document.createElement("style");
  style.textContent = `
  .full-width-form .ant-form-item-control {
    flex: 1 1 auto;
    max-width: 100%;
  }
  .full-width-form .ant-form-item-control-input {
    width: 100%;
  }
  .full-width-form .ant-form-item-control-input-content {
    width: 100%;
  }
  .full-width-form .ant-input {
    width: 100%;
  }
  .full-width-form .ant-input-textarea {
    width: 100%;
  }
  .full-width-form .ant-input-textarea > textarea {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }
  
  /* Add background color to accordion panels */
  .ant-collapse-item {
    background-color: #f8fafc !important;
  }
  .ant-collapse-item .ant-collapse-header {
    background-color: #f8fafc !important;
  }
  .ant-collapse-item .ant-collapse-content {
    background-color: #f8fafc !important;
  }
`;
  document.head.appendChild(style);
}

export interface AnalysisModalProps {
  open: boolean;
  onClose: () => void;
  analysisData: Record<string, unknown> | null;
  selectedDoc?: {
    id: string; // Internal record_id
    filetype?: string;
    document_url?: string;
    original_document_url?: string;
    document_name?: string;
    file?: File;
    error?: string; // uploaded file
  } | null;
  form: FormInstance;
  onSave: () => void;
  editMode: boolean;
  onToggleEdit: (edit: boolean) => void;
  analysisLoading: boolean;
  setAnalysisLoading: (edit: boolean) => void;
  token: string;
}

// ----------- Helper: Table View Components ----------
interface TableRow {
  key: string;
  field: string;
  value: string;
}

const flattenDataForTable = (
  data: unknown,
  parentKey = "",
  rows: TableRow[] = [],
): TableRow[] => {
  if (data === null || data === undefined) {
    return rows;
  }

  if (typeof data === "object" && !Array.isArray(data)) {
    Object.entries(data).forEach(([key, value]) => {
      const fieldKey = parentKey
        ? `${parentKey}.${formatLabel(key)}`
        : formatLabel(key);

      if (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value)
      ) {
        flattenDataForTable(value, fieldKey, rows);
      } else {
        rows.push({
          key: fieldKey,
          field: fieldKey,
          value: String(value),
        });
      }
    });
  }

  if (Array.isArray(data)) {
    data.forEach((item, index) => {
      const arrayKey = `${parentKey}${index + 1}`;

      if (typeof item === "object" && item !== null) {
        flattenDataForTable(item, arrayKey, rows);
      } else {
        rows.push({
          key: arrayKey,
          field: `${index + 1}. ${parentKey}`, // Change to 1-based indexing
          value: String(item),
        });
      }
    });
  }

  return rows;
};

// Helper function to flatten data for form initialization
const flattenDataForForm = (
  obj: Record<string, unknown>,
  parentPath: string[] = [],
): { key: string; value: unknown }[] => {
  return Object.entries(obj).flatMap(([key, value]) => {
    const formattedKey = formatLabel(key);
    const currentPath = [...parentPath, formattedKey];
    const fieldKey = currentPath.join(".");

    if (typeof value === "object" && value !== null) {
      return flattenDataForForm(value as Record<string, unknown>, currentPath);
    }

    return [{ key: fieldKey, value }];
  });
};

const renderTableView = (
  data: unknown,
  form: FormInstance,
  editMode: boolean,
): React.ReactNode => {
  const rows = flattenDataForTable(data);
  const columns = [
    {
      title: <div className=" p-2 rounded font-bold">Field</div>,
      dataIndex: "field",
      key: "field",
      width: "40%",
      render: (text: string) => (
        <div className="p-2 rounded font-normal">{text}</div>
      ),
    },
    {
      title: <div className=" p-2 rounded font-bold">Value</div>,
      dataIndex: "value",
      key: "value",
      width: "60%",
      onCell: () => ({
        style: {
          padding: 0, // 🔥 remove default padding
        },
      }),
      render: (text: string, record: TableRow) => {
        // Get current form value to ensure it reflects translation updates
        const currentValue = form.getFieldValue(record.key);
        const displayValue = currentValue !== undefined ? currentValue : text;

        return (
          <div
            style={{ width: "100%", margin: 0, background: "white" }}
            className="!p-[10px_0px]"
          >
            <Form.Item
              key={`${record.key}`}
              name={record.key}
              initialValue={text}
              style={{ margin: 0, width: "100%" }}
            >
              <Input.TextArea
                readOnly={!editMode}
                autoSize={{ minRows: 1, maxRows: 10 }}
                style={{
                  resize: "none",
                  width: "100%",
                  display: "block",
                }}
                className={`font-extralight !w-full ${editMode ? "" : "!border-none focus:!ring-0 focus:!outline-none"}`}
                value={displayValue}
              />
            </Form.Item>
          </div>
        );
      },
    },
  ];

  return (
    <Table
      key={`table`}
      columns={columns}
      dataSource={rows}
      pagination={false}
      size="small"
      rowKey={(record) => `${record.key}`}
      className="analysis-table"
      // scroll={{ y: 400 }}
      style={{ width: "100%" }}
      bordered={editMode ? false : true}
    />
  );
};

// ----------- Helper: Recursive rendering of form fields ----------

const reorderObject = (data: unknown): unknown => {
  // Handle array
  if (Array.isArray(data)) {
    return data.map(reorderObject);
  }

  // Handle object
  if (data && typeof data === "object") {
    const primitiveEntries: [string, any][] = [];
    const objectEntries: [string, any][] = [];

    Object.entries(data as Record<string, any>).forEach(([key, value]) => {
      const reorderedValue = reorderObject(value);

      if (typeof value === "object" && value !== null) {
        objectEntries.push([key, reorderedValue]);
      } else {
        primitiveEntries.push([key, reorderedValue]);
      }
    });

    return Object.fromEntries([...primitiveEntries, ...objectEntries]);
  }

  // Return primitive values directly
  return data;
};

// Helper function to flatten reordered data for form initialization
const flattenReorderedDataForForm = (
  obj: Record<string, unknown>,
  parentPath: string[] = [],
): { key: string; value: unknown }[] => {
  return Object.entries(obj).flatMap(([key, value]) => {
    const formattedKey = formatLabel(key);
    const currentPath = [...parentPath, formattedKey];
    const fieldKey = currentPath.join(".");

    if (typeof value === "object" && value !== null) {
      return flattenReorderedDataForForm(
        value as Record<string, unknown>,
        currentPath,
      );
    }

    return [{ key: fieldKey, value }];
  });
};

const renderRoot = (
  analysisValue: Record<string, unknown> | null,
  form: FormInstance,
  editMode: boolean,
  selectedDoc: any,
  analysisData: Record<string, unknown> | null
): React.ReactNode => {
  if (!analysisData) {
    return (
      <div className="h-full min-h-[500px] flex items-center justify-center p-6">
        <div className="max-w-xl w-full rounded-2xl border border-red-200 bg-red-50 shadow-sm p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-red-100">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6 text-red-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3m0 4h.01M10.29 3.86l-7.5 13A1 1 0 003.66 18h16.68a1 1 0 00.87-1.5l-7.5-13a1 1 0 00-1.74 0z"
                />
              </svg>
            </div>

            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-700">
                Document mismatch
              </h3>
              <p className="mt-2 text-sm leading-6 text-red-600">
                {selectedDoc?.error ||
                  "The uploaded document does not match the expected document type."}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!analysisValue || Object.keys(analysisValue).length === 0) {
    return null;
  }

  const [rootKey, rootValue] = Object.entries(analysisValue)[0];

  return (
    <div className="mb-6">
      <div className="bg-[#f8fafc] p-3">
        <h3 className="mb-5 text-left text-lg font-bold text-gray-900">
          {formatLabel(rootKey)} :
        </h3>
        {renderFields(reorderObject(rootValue), form, editMode, rootKey)}
      </div>
    </div>
  );
};

const formatLabel = (value: string): string => {
  return value
    .replace(/\$(\d+)\$\./g, (_, num) => `${Number(num) + 1}.`)
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .replaceAll("_", " ")
    .split(" ")
    .map((word) =>
      word === word.toUpperCase()
        ? word
        : word.charAt(0).toUpperCase() + word.slice(1),
    )
    .join(" ")
    .trim();
};

const renderFields = (
  data: unknown,
  form: FormInstance,
  editMode: boolean,
  parentKey = "",
): React.ReactNode => {
  if (!data) return null;

  if (typeof data === "object" && !Array.isArray(data)) {
    return Object.entries(data).map(([key, value], index) => {
      const fieldKey = parentKey
        ? `${parentKey}.${formatLabel(key)}`
        : formatLabel(key);

      if (typeof value === "object" && value !== null) {
        return (
          <>
            <Collapse
              key={`${fieldKey}`}
              className="!mb-4 !bg-[#f4f8fc] rounded-xl"
              bordered={false}
              items={[
                {
                  key: fieldKey,
                  label: formatLabel(key),
                  children: renderTableView(value, form, editMode),
                  className: "font-semibold",
                },
              ]}
            />
          </>
        );
      }

      return (
        <>
          <Form.Item
            key={`${fieldKey}`}
            name={fieldKey}
            label={
              <span className="whitespace-normal break-words text-left block">
                {formatLabel(key)}
              </span>
            }
            style={{ marginBottom: 10 }}
            initialValue={value}
            className="mb-4 !font-extralight !text-left"
          >
            <Input.TextArea
              readOnly={!editMode}
              variant="outlined"
              autoSize={{ minRows: 1, maxRows: 10 }}
              style={{ resize: "none" }}
              className={`!text-left !pt-[5px] ${editMode ? "bg-white" : "!border-none !bg-transparent"
                } p-0`}
            />
          </Form.Item>
        </>
      );
    });
  }

  if (Array.isArray(data)) {
    return data.map((item, index) => {
      const arrayKey = `${parentKey}[${index}]`;

      if (typeof item === "object") {
        return (
          <Collapse
            key={`${arrayKey}`}
            className="!mb-4 bg-[#f8fafc] rounded-xl"
            bordered={false}
            items={[
              {
                key: arrayKey,
                label: `${parentKey} #${index + 1}`,
                children: renderTableView(item, form, editMode),
                className: "font-semibold",
              },
            ]}
          />
        );
      }

      return (
        <Form.Item
          key={`${arrayKey}`}
          name={arrayKey}
          label={
            <span style={{ whiteSpace: "normal", wordBreak: "break-word" }}>
              {`${parentKey}[${index}]`}
            </span>
          }
          initialValue={item}
          className="mb-4"
        >
          <Input.TextArea
            readOnly={!editMode}
            variant="outlined"
            autoSize={{ minRows: 1, maxRows: 10 }}
            style={{ resize: "none" }}
            className={!editMode ? "bg-gray-100" : ""}
          />
        </Form.Item>
      );
    });
  }

  return null;
};

// ----------- Document Preview Component --------------

/**
 * Normalise a document URL so the browser can actually fetch it.
 *
 * On GCP the backend may store or return gs:// URIs or raw
 * storage.googleapis.com public URLs for private-bucket objects.
 * Both fail in the browser.  When we detect either pattern we rewrite
 * the URL to the backend /files/serve endpoint which uses the VM's ADC
 * credentials and therefore always has read access.
 */
function normalizeDocumentUrl(url: string): string {
  // V4 signed URL — has X-Goog-Algorithm query param, already browser-accessible
  // directly from storage.googleapis.com. Pass through unchanged.
  if (
    url.match(/^https?:\/\/storage\.googleapis\.com\//) &&
    url.includes("X-Goog-Algorithm=")
  ) {
    return url;
  }

  // Everything else (gs:// URIs, unsigned GCS URLs, backend serve URLs with any host)
  // is routed through the Next.js server-side proxy.  This keeps port 8000 private
  // (GCP firewall does not need to expose it) and ensures the proxy can always reach
  // the backend via localhost on the same VM.
  return `/api/proxy?url=${encodeURIComponent(url)}`;
}

const DocumentPreview: React.FC<{
  selectedDoc?: {
    filetype?: string;
    document_url?: string;
    original_document_url?: string;
    document_name?: string;
    file?: File;
  } | null;
  docView: "Extraction Doc" | "Original Doc";
}> = ({ selectedDoc, docView }) => {
  const [previewFileUrl, setPreviewFileUrl] = useState<string | null>(null);

  useEffect(() => {
    if (selectedDoc?.document_url || selectedDoc?.original_document_url) {
      const rawUrl =
        (docView === "Extraction Doc"
          ? selectedDoc.document_url
          : selectedDoc.original_document_url) ?? null;
      setPreviewFileUrl(rawUrl ? normalizeDocumentUrl(rawUrl) : null);

      if (
        !selectedDoc.filetype &&
        selectedDoc.document_name?.toLowerCase().endsWith(".pdf")
      ) {
        selectedDoc.filetype = "application/pdf";
      }
    } else {
      setPreviewFileUrl(null);
    }
  }, [selectedDoc, docView]);

  // Determine file type from the active raw URL (before normalization strips the extension)
  const activeRawUrl = docView === "Extraction Doc"
    ? selectedDoc?.document_url
    : selectedDoc?.original_document_url;
  const isPdf =
    selectedDoc?.filetype === "application/pdf" ||
    selectedDoc?.document_name?.toLowerCase().endsWith(".pdf") ||
    activeRawUrl?.toLowerCase().includes(".pdf") ||
    previewFileUrl?.toLowerCase().includes(".pdf");

  if (!previewFileUrl) {
    return <p className="text-gray-400">No preview available</p>;
  }

  return isPdf ? (
    <iframe
      src={previewFileUrl}
      title="PDF Preview"
      width="100%"
      height="580px"
      className="rounded-md border-0"
    />
  ) : (
    <img
      src={previewFileUrl}
      alt={selectedDoc?.document_name || "Document Preview"}
      className="h-[580px] w-full rounded-md object-contain"
    />
  );
};

// ------------------- Main Modal ----------------------
const AnalysisModal: React.FC<AnalysisModalProps> = ({
  open,
  onClose,
  analysisData,
  selectedDoc,
  form,
  onSave,
  editMode,
  onToggleEdit,
  analysisLoading,
  setAnalysisLoading,
  token,
}) => {
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState("Tamil");
  const [isTranslating, setIsTranslating] = useState(false);
  const [expandedSection, setExpandedSection] = useState<"preview" | "form" | null>(null);
  const [docView, setDocView] = useState<"Extraction Doc" | "Original Doc">("Original Doc");
  const [analysisValue, setAnalysisValue] = useState<any>(null); // ✅ Initialize as null
  const [translationProgress, setTranslationProgress] = useState<number>(0);
  const [translationStage, setTranslationStage] = useState<string>("");
  const [hasChanges, setHasChanges] = useState<boolean>(false);
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { docProgressId, setDocProgressId } = useAppContext();


  // ✅ FIXED: Form initialization for initial analysisData
  useEffect(() => {
    if (analysisData && open) {
      const flatData: Record<string, unknown> = {};

      // Use the reordered data for form initialization to match the accordion structure
      const reorderedData = reorderObject(analysisData);
      if (typeof reorderedData === "object" && reorderedData !== null) {
        flattenReorderedDataForForm(
          reorderedData as Record<string, unknown>,
        ).forEach((item) => {
          flatData[item.key] = item.value;
        });
      }

      form.setFieldsValue(flatData);
      setAnalysisValue(analysisData); // ✅ Set analysisValue here too
    }
  }, [analysisData, open, form]); // ✅ Proper dependencies

  // ✅ NEW: Separate useEffect for translation data updates (analysisValue changes)
  useEffect(() => {
    if (analysisValue && open && analysisValue !== analysisData) {
      // This handles translated data updates
      const flatData: Record<string, unknown> = {};
      const reorderedData = reorderObject(analysisValue);

      if (typeof reorderedData === "object" && reorderedData !== null) {
        flattenReorderedDataForForm(
          reorderedData as Record<string, unknown>,
        ).forEach((item) => {
          flatData[item.key] = item.value;
        });
      }

      // Reset and set new values in one go
      form.resetFields();
      form.setFieldsValue(flatData);
    }
  }, [analysisValue, open, form, analysisData]); // ✅ Proper dependencies

  useEffect(() => {
    return () => {
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const restoreActiveTranslation = async () => {
      if (!open || !selectedDoc?.id || isTranslating) {
        return;
      }
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/translate/active/${selectedDoc.id}?target_language=${encodeURIComponent(targetLanguage)}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          },
        );
        if (!response.ok) {
          return;
        }
        const active = await response.json();
        const status = String(active?.status || "").toLowerCase();
        if (
          (status === "queued" || status === "processing") &&
          (active?.process_id || active?.task_id)
        ) {
          setIsTranslating(true);
          startTranslationProgressPolling(active.process_id || active.task_id);
          setDocProgressId(active.process_id || active.task_id);
        }
      } catch {
        // Best-effort restore only.
      }
    };

    restoreActiveTranslation();
  }, [open, selectedDoc?.id, targetLanguage, token]);

  useEffect(() => {
    if (docProgressId) {
      setIsTranslating(true);
      startTranslationProgressPolling(docProgressId);
    }
  }, [docProgressId]);

  const languages = [
    { label: "Tamil", value: "Tamil" },
    { label: "Hindi", value: "Hindi" },
    { label: "Telugu", value: "Telugu" },
    { label: "Kannada", value: "Kannada" },
    { label: "Malayalam", value: "Malayalam" },
    { label: "Bengali", value: "Bengali" },
    { label: "Gujarati", value: "Gujarati" },
    { label: "Marathi", value: "Marathi" },
    { label: "English", value: "English" },
  ];

  // ✅ FIXED: Simplified applyTranslatedData - just updates state
  const applyTranslatedData = useCallback((translatedData: any) => {
    setAnalysisValue(translatedData);
  }, []);

  const stopTranslationPolling = () => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  };

  // ✅ FIXED: Updated polling with proper translation completion
  const startTranslationProgressPolling = (processId: string) => {
    stopTranslationPolling();

    const poll = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/translate/progress/${processId}`,
          {
            headers: { Authorization: `Bearer ${token}` },
          },
        );
        if (!response.ok) {
          throw new Error("Progress request failed");
        }
        const progressData = await response.json();
        const status = String(progressData?.status || "").toLowerCase();
        const percentValue =
          status === "completed"
            ? 100
            : status === "failed"
              ? 0
              : (progressData?.progress ?? 0);
        const stageValue = progressData?.stage ?? "Translation in progress";

        setTranslationProgress(percentValue);
        setTranslationStage(stageValue);
        message.loading({
          content: `${stageValue} (${percentValue}%)`,
          key: "translating",
        });

        if (status === "completed") {
          stopTranslationPolling();
          setIsTranslating(false);
          setTranslationProgress(100);
          setTranslationStage("Translation completed");

          const translatedData = progressData?.result?.translated_data;
          if (translatedData) {
            // ✅ Just update state - useEffect handles form update
            applyTranslatedData(translatedData);
          }

          setTargetLanguage(progressData?.target_language || "Tamil");
          message.success({
            content: `Translated to ${targetLanguage} successfully!`,
            key: "translating",
          });
          setDocProgressId(null);
        } else if (status === "failed") {
          stopTranslationPolling();
          setIsTranslating(false);
          setTranslationProgress(0);
          setTranslationStage("Translation failed");
          message.error({
            content: progressData?.error || "Failed to translate content.",
            key: "translating",
          });
          setDocProgressId(null);
        }
      } catch (err) {
        stopTranslationPolling();
        setIsTranslating(false);
        setTranslationProgress(0);
        setTranslationStage("Translation failed");
        message.error({
          content: "Failed to translate content.",
          key: "translating",
        });
        setDocProgressId(null);
      }
    };

    poll();
    progressTimerRef.current = setInterval(poll, 2000);
  };

  // ✅ FIXED: handleTranslate with proper immediate response handling
  const handleTranslate = async () => {
    if (!selectedDoc?.id) {
      message.error("No document ID found for translation.");
      return;
    }

    setIsTranslating(true);
    setTranslationProgress(0);
    setTranslationStage("Translation queued");
    message.loading({
      content: `Translating to ${targetLanguage}...`,
      key: "translating",
    });

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/translate/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            record_id: selectedDoc.id,
            target_language: targetLanguage,
          }),
        },
      );

      if (!response.ok) {
        throw new Error("Translation request failed.");
      }

      const result = await response.json();
      if (result?.translated_data) {
        // ✅ Handle immediate translation result
        applyTranslatedData(result.translated_data);
        setTranslationProgress(100);
        setTranslationStage("Translation completed");
        setTargetLanguage(result?.language || "Tamil");
        message.success({
          content: `Translated to ${targetLanguage} successfully!`,
          key: "translating",
        });
        setIsTranslating(false);
      } else if (result?.process_id || result?.task_id) {
        startTranslationProgressPolling(result.process_id || result.task_id);
        setDocProgressId(result.process_id || result.task_id);
      } else {
        throw new Error(
          "Translation response did not include data or process id.",
        );
      }
    } catch (error) {
      console.error("Translation error:", error);
      message.error({
        content: "Failed to translate content.",
        key: "translating",
      });
      setTranslationStage("Translation failed");
      setTranslationProgress(0);
      setIsTranslating(false);
    }
  };

  const handleSaveClick = () => {
    setConfirmVisible(true);
  };

  const handleConfirmOk = () => {
    setConfirmVisible(false);
    onSave();
    onToggleEdit(false);
  };

  const handleConfirmCancel = () => setConfirmVisible(false);

  const handleCancel = () => {
    onToggleEdit(false);
    setExpandedSection(null);
    onClose();
  };

  const handleCancelEdit = () => {
    onToggleEdit(false);
  };

  const handleReset = () => {
    onToggleEdit(false);
  };

  // Watch for form changes to enable save button
  const handleFormValuesChange = () => {
    if (editMode) {
      setHasChanges(true);
    }
  };

  const handleDocChange = (value: string) => {
    setDocView(value as "Extraction Doc" | "Original Doc");
  }

  return (
    <>
      <Modal
        destroyOnHidden
        open={open}
        onCancel={handleCancel}
        width={1100}
        title={`Analysis for ${selectedDoc?.filetype || "Document"}`}
        styles={{
          body: { background: "#fff", overflow: "hidden" },
        }}
        footer={
          <></>
        }
        centered
        maskClosable={false}
        zIndex={1000}
      >
        <div className="grid grid-cols-12 gap-4">
          {/* Left: Document Preview */}
          <div className={`${expandedSection === "preview" ? "col-span-12" : expandedSection === "form" ? "hidden" : "col-span-6"}`}>
            <div className="rounded-lg border border-gray-200 bg-white p-2 max-h-[600px]">
              <div className="flex justify-between items-center mb-2 mt-2">
                <ConfigProvider
                  theme={{
                    components: {
                      Segmented: {
                        itemSelectedBg: "#2563EB",
                        itemSelectedColor: "#ffffff",
                        trackBg: "#F3F4F6",
                        itemColor: "#4B5563",
                        trackPadding: 2,
                        borderRadius: 20,
                      },
                    },
                  }}
                >
                  <Segmented
                    options={["Original Doc", "Extraction Doc"]}
                    size="middle"
                    value={docView}
                    onChange={(value) => {
                      handleDocChange(value)
                    }}
                    className="font-medium !text-[14px]"
                  />
                </ConfigProvider>

                <div
                  onClick={() => setExpandedSection(expandedSection === "preview" ? null : "preview")}
                  className="inline-flex items-center gap-2 border border-gray-200 rounded px-3 py-1 cursor-pointer"
                >

                  {expandedSection === "preview" ? (
                    <>
                      <BiCollapse className="text-[20px]" />
                      <span className="text-sm">Collapse</span>
                    </>
                  ) : (
                    <>
                      <IoMdExpand className="text-[20px]" />
                      <span className="text-sm">Expand</span>
                    </>
                  )}
                </div>
              </div>
              <DocumentPreview selectedDoc={selectedDoc} docView={docView} />
            </div>
          </div>

          {/* Right: Form section */}
          <div className={`${expandedSection === "form" ? "col-span-12" : expandedSection === "preview" ? "hidden" : "col-span-6"}`}>
            <div className="border border-gray-100 px-5 p-[16px_16px_0px_16px] rounded-lg max-h-[600px] overflow-auto small-scrollbar">
              <div className="flex justify-end mb-4">
                <div
                  onClick={() => setExpandedSection(expandedSection === "form" ? null : "form")}
                  className=" inline-flex items-center gap-2 border border-gray-200 rounded px-3 py-1 cursor-pointer"
                >
                  {expandedSection === "form" ? (
                    <>
                      <BiCollapse className="text-[20px]" />
                      <span className="text-sm">Collapse</span>
                    </>
                  ) : (
                    <>
                      <IoMdExpand className="text-[20px]" />
                      <span className="text-sm">Expand</span>
                    </>
                  )}
                </div>
              </div>
              {/* ✅ REMOVED forceRerender key - using proper React patterns */}
              <Form
                form={form}
                layout="horizontal"
                labelAlign="left"
                labelCol={{ span: 10 }}
                wrapperCol={{ span: 16 }}
                className="pr-2 full-width-form"
                onValuesChange={handleFormValuesChange}
                style={{ width: "100%" }}
              >
                <div className="mb-5">
                  {renderRoot(analysisValue, form, editMode, selectedDoc, analysisData)}
                </div>
              </Form>

              {/*Footer  */}
              {analysisData &&
                <div className="sticky bottom-0 bg-white border-t border-gray-200 py-2">
                  <span className="" style={{ fontWeight: "600" }}>Translate:</span>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: expandedSection === "form" ? "space-between" : "",
                      gap: expandedSection === "form" ? "0" : "52px",
                      alignItems: "center",
                      width: "100%",
                    }}
                  >

                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <div className="flex flex-col">
                        {/* <span style={{ fontWeight: "600" }}>Translate:</span> */}
                        <Select
                          value={targetLanguage}
                          onChange={setTargetLanguage}
                          options={languages}
                          style={{ width: 120 }}
                        />
                      </div>
                      <Button
                        type="primary"
                        className="!text-white"
                        onClick={handleTranslate}
                        loading={isTranslating}
                        disabled={!analysisData}
                      >
                        Translate
                      </Button>
                      {/* {isTranslating && (
                  <span className="text-sm text-gray-600">
                    {translationStage} ({translationProgress}%)
                  </span>
                )} */}
                    </div>
                    <div style={{ display: "flex", gap: "8px" }}>

                      {!editMode ? (
                        <Button type="primary" onClick={() => onToggleEdit(true)}>
                          Edit Data
                        </Button>
                      ) : (
                        <Button
                          className={`${!hasChanges ? "opacity-65" : ""} !text-white`}
                          loading={analysisLoading}
                          type="primary"
                          onClick={handleSaveClick}
                          disabled={!hasChanges}
                        >
                          Save
                        </Button>
                      )}

                      <Button onClick={handleCancel}>Close</Button>
                    </div>
                  </div>
                </div>
              }
            </div>
          </div>
        </div>
      </Modal>

      {/* Confirmation Modal */}
      <Modal
        open={confirmVisible}
        onOk={() => {
          handleConfirmOk();
          setAnalysisLoading(true);
        }}
        onCancel={handleConfirmCancel}
        okText="Yes, Save"
        cancelText="Cancel"
        title="Are you sure?"
        zIndex={1100}
      >
        <p>Are you sure you want to save the changes to this file?</p>
      </Modal>
    </>
  );
};

export default AnalysisModal;