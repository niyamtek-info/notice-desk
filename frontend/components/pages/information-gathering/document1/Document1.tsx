import React, { useEffect, useState } from "react";
import {
  Table,
  Button,
  Dropdown,
  Typography,
  Modal,
  Form,
  Descriptions,
  Input,
  message,
} from "antd";
import type { MenuProps, TableColumnsType, TableProps } from "antd";
import type { UploadFile } from "antd/es/upload/interface";
import { EyeOutlined } from "@ant-design/icons";
// import PDFConverter from "@/components/form/PDFConverter";
import { useAppNoContext } from "@/context/AppNoContext";
import { BsThreeDotsVertical } from "react-icons/bs";
// import Required1, { RequiredDocument } from './Required1'
import AnalysisModal from "@/components/form/AnalysisModal";
import CompareModel from "@/components/form/CompareModal";
import jsonData from "@/data/sample.json";
import { VscFiles } from "react-icons/vsc";
import { FaCheck, FaExchangeAlt } from "react-icons/fa";
import { IoCloudUploadOutline } from "react-icons/io5";
import UploadForm from "@/components/form/UploadForm";
import ProgressModel from "../../application-details/ProgressModel";
import {
  ActiveDocsResponse,
  DocumentApi,
  ExtractDocument,
} from "@/src/services/DocumentApi";
import { RxCross2 } from "react-icons/rx";
import { useAppContext } from "@/context/GlobalContext";

export interface RequiredDocument {
  id: string;
  name: string;
  uploaded: boolean;
  upload_type: "single" | "multiple";
  completed: boolean;
  reason?: string;
  fromWhom?: string;
  targetDate?: string;
  suggestedBy?: string;
  explanation?: string;
  files?: { name: string; size: number }[];
}

const { Title, Text } = Typography;

interface DocumentData {
  id: string;
  filetype: string;
  file?: File;
  meta?: DocumentMeta;
  document_url?: string;
  original_document_url?: string;
  document_name?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  json?: Record<string, any>;
  progress?: number;
  stage?: string;
  status?: string;
  error?: string;
  error_message?: string;
}

interface DocumentMeta {
  title: string;
  uploadedBy: string;
  uploadDate: string;
}

interface DocumentType {
  token: string;
  setDocData: any;
  setTriggerReport: any;
}

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

const getSubPathFormKey = (subPath: (string | number)[], parentKey = ""): string => {
  if (subPath.length === 0) return parentKey;
  const key = subPath[0];
  if (typeof key === "number") {
    const nextParentKey = `${parentKey}${key + 1}`;
    return getSubPathFormKey(subPath.slice(1), nextParentKey);
  } else {
    const formattedKey = formatLabel(key);
    const nextParentKey = parentKey ? `${parentKey}.${formattedKey}` : formattedKey;
    return getSubPathFormKey(subPath.slice(1), nextParentKey);
  }
};

const getFormKeyForPath = (path: (string | number)[]): string => {
  if (path.length < 2) return "";
  const rootKey = path[0];
  if (path.length === 2) {
    return `${rootKey}.${formatLabel(String(path[1]))}`;
  }
  return getSubPathFormKey(path.slice(2), "");
};

const traverseAndUpdate = (
  currentObj: any,
  currentPath: (string | number)[],
  formValues: Record<string, any>
) => {
  if (currentObj === null || currentObj === undefined) return;

  if (Array.isArray(currentObj)) {
    currentObj.forEach((item, index) => {
      const nextPath = [...currentPath, index];
      if (typeof item === "object" && item !== null) {
        traverseAndUpdate(item, nextPath, formValues);
      } else {
        const formKey = getFormKeyForPath(nextPath);
        if (formKey && formValues[formKey] !== undefined) {
          const originalValue = currentObj[index];
          let newValue = formValues[formKey];
          if (typeof originalValue === "number" && newValue !== null && newValue !== "") {
            const parsed = Number(newValue);
            if (!isNaN(parsed)) {
              newValue = parsed;
            }
          } else if (typeof originalValue === "boolean") {
            newValue = newValue === "true" || newValue === true;
          }
          currentObj[index] = newValue;
        }
      }
    });
  } else if (typeof currentObj === "object") {
    Object.entries(currentObj).forEach(([key, value]) => {
      const nextPath = [...currentPath, key];
      if (typeof value === "object" && value !== null) {
        traverseAndUpdate(value, nextPath, formValues);
      } else {
        const formKey = getFormKeyForPath(nextPath);
        if (formKey && formValues[formKey] !== undefined) {
          const originalValue = currentObj[key];
          let newValue = formValues[formKey];
          if (typeof originalValue === "number" && newValue !== null && newValue !== "") {
            const parsed = Number(newValue);
            if (!isNaN(parsed)) {
              newValue = parsed;
            }
          } else if (typeof originalValue === "boolean") {
            newValue = newValue === "true" || newValue === true;
          }
          currentObj[key] = newValue;
        }
      }
    });
  }
};

export default function Document1({ token, setDocData, setTriggerReport }: DocumentType) {
  const [data, setData] = useState<DocumentData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentData | null>(null);
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [requiredDocs, setRequiredDocs] = useState<RequiredDocument[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [analysisData, setAnalysisData] = useState<Record<string, any> | null>(
    null,
  );
  const [form] = Form.useForm();
  const [formUpload] = Form.useForm();

  const [editMode, setEditMode] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const [diffData, setDiffData] = useState<{
    oldText?: string;
    newText?: string;
  } | null>(null);
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [compareOptionsVisible, setCompareOptionsVisible] = useState(false);
  const [image1, setImage1] = useState<string | null>(null);
  const [image2, setImage2] = useState<string | null>(null);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [confirmVisible, setConfirmVisible] = useState<boolean>(false);
  const [deleteData, setDeleteData] = useState<any>();
  const [fileId, setFileId] = useState<string>("");
  const [open, setOpen] = useState<boolean>(false);
  const [trigger, setTrigger] = useState<number>(0);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>("");
  const [previewType, setPreviewType] = useState<string>("");
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [isPreviewExpanded, setIsPreviewExpanded] = useState(false);

  const { docFileId, setDocFileId } = useAppContext();


  // Track currently uploading files to show progress
  const [uploadingFiles, setUploadingFiles] = useState<
    Record<
      string,
      {
        docType: string;
        progress: number;
        stage: string;
        status?: string;
        error?: string;
        document_name?: string;
      }
    >
  >({});

  const handleUploadStarted = (fileId: string, docType: string) => {
    setUploadingFiles((prev) => ({
      ...prev,
      [fileId]: {
        docType,
        progress: 0,
        stage: "Starting extraction...",
        status: "queued",
      },
    }));
  };

  const handleUploadSuccess = (file: File) => {
    setUploadModalVisible(false);
    setPreviewUrl("");
    setPreviewType("");
    setFileList([]);
    setTriggerReport((prev: any) => prev + 1);
  };


  const handleEditSave = async () => {
    try {
      const values = await form.validateFields();

      if (!applicationNumber || !selectedDoc?.id) {
        console.error("Missing applicationNumber or file_id");
        return;
      }

      const originalJson = selectedDoc.json || {};
      const updatedJson = JSON.parse(JSON.stringify(originalJson));
      traverseAndUpdate(updatedJson, [], values);

      const payload = {
        file_id: selectedDoc.id,
        doc_type: selectedDoc.filetype,
        document_url: selectedDoc.document_url,
        document_name: selectedDoc.document_name,
        ai_parsed_output: updatedJson,
        json: updatedJson,
      };

      const res: any = await DocumentApi.documentPutApi(selectedDoc.id, payload);

      if (!res) {
        throw new Error("Failed to update document");
      }

      const result = await res;

      // Close edit mode after save
      setEditMode(false);
      setHasChanges(false);
      setAnalysisLoading(false);
      // Refresh table data
      setRefreshKey((k) => k + 1);
      setTriggerReport((prev: any) => prev + 1);
    } catch (err) {
      console.error("❌ Error saving edits:", err);
      setAnalysisLoading(false);
    }
  };

  const rowSelection: TableProps<DocumentData>["rowSelection"] = {
    selectedRowKeys,
    onChange: (selectedKeys) => {
      setSelectedRowKeys(selectedKeys);
    },
  };
  const { applicationNumber } = useAppNoContext();

  const [refreshKey, setRefreshKey] = useState(0);



  useEffect(() => {
    if (!applicationNumber) return;

    setLoading(true);

    DocumentApi.getDocuments(applicationNumber)
      .then(
        ({
          docs,
          activeDocs,
        }: {
          docs: ExtractDocument[];
          activeDocs: ActiveDocsResponse;
        }) => {
          const mappedDocs: DocumentData[] = docs.map(
            (doc: ExtractDocument) => {
              const activeDoc = activeDocs[doc.file_id];
              const parts = (doc.file_id as string).split("_");

              const maybeVersion = parts[parts.length - 1];
              const hasVersion =
                maybeVersion.startsWith("v") &&
                !isNaN(Number(maybeVersion.slice(1)));

              const version = hasVersion ? maybeVersion : "v1";

              const docType = hasVersion
                ? parts.slice(1, -1).join("_")
                : parts.slice(1).join("_");
              return {

                id: doc.file_id as string,
                filetype: ((doc.doc_type as string)?.replaceAll("_", " ") ||
                  docType.replaceAll("_", " ") ||
                  "Unknown") as string,
                version,
                document_url: doc.document_url as string,
                original_document_url: doc.original_document_url as string,
                document_name: doc.document_name as string,

                json: (doc.ai_parsed_output || doc.json || {}) as Record<
                  string,
                  any
                >,

                meta: {
                  title: `${docType} (${version})`,
                  uploadedBy: "System",
                  uploadDate: new Date().toLocaleDateString(),
                },
                progress:
                  typeof activeDoc?.progress === "number" && activeDoc?.status !== "failed"
                    ? activeDoc.progress
                    : undefined,
                stage:
                  activeDoc?.stage ||
                  (activeDoc?.status === "failed"
                    ? "Extraction failed"
                    : undefined),
                status: activeDoc?.status,
                error: activeDoc?.error || doc.error_message,
              };
            },
          );

          setData(mappedDocs);
          setDocData(mappedDocs);

          setUploadingFiles((prev) => {
            const next = { ...prev };
            Object.entries(activeDocs).forEach(([fid, val]: [string, any]) => {
              next[fid] = {
                docType: val.doc_type,
                document_name: val.document_name,
                progress: typeof val.progress === "number" ? val.progress : undefined,
                stage:
                  val.stage ||
                  (val.status === "failed" ? "Extraction failed" : ""),
                status: val.status,
                error: val.error,
              };
            });

            return next;
          });
        },
      )
      .catch((err: any) => console.error("Error fetching documents:", err))
      .finally(() => setLoading(false));
  }, [applicationNumber, refreshKey]);

  // Combine fetched data with currently uploading files
  const combinedData = React.useMemo(() => {
    const combined = [...data];
    // Add uploading files that aren't already in the data list
    Object.entries(uploadingFiles).forEach(([fileId, uploadState]) => {
      // If it's already in the main data (completed), don't show the temp row
      if (!combined.some((d) => d.id === fileId)) {
        combined.push({
          id: fileId,
          filetype: uploadState.docType ? uploadState.docType : "",
          document_name: uploadState?.document_name ? uploadState?.document_name : "",
          progress: uploadState.progress,
          stage: uploadState.stage,
          status: uploadState.status,
          error: uploadState.error,
        });
      }
    });
    return combined;
  }, [data, uploadingFiles, trigger]);



  useEffect(() => {
    if (!docFileId?.length) return;

    let cancelled = false;

    const pollProgress = async () => {
      for (const docId of docFileId) {
        try {
          const progressData: any =
            await DocumentApi.documentProgressGetApi(docId);

          if (cancelled) return;

          const currentFileId = docId;
          const percent = progressData?.progress ?? 0;
          const stage = progressData?.stage ?? "";
          const status = String(progressData?.status ?? "").toLowerCase();
          setTrigger((pre: any) => pre + 1)

          const isFailed =
            status === "failed" || stage.toLowerCase().includes("failed");

          const isCompleted =
            percent >= 100 || status === "completed";

          // ✅ YOUR LOGIC (unchanged)
          if (isCompleted || isFailed) {
            setTrigger(0)
            setUploadingFiles((prev) => {
              const next = { ...prev };
              delete next[currentFileId];
              return next;
            });

            let filterId =
              docFileId.filter((res: any) => res !== docId) || [];

            setDocFileId(filterId);

            if (isFailed) {
              messageApi.error(progressData?.error);
            }

            setRefreshKey((k) => k + 1);

            return;
          }

          // progress update
          setUploadingFiles((prev) => {
            if (
              !prev[currentFileId] ||
              (prev[currentFileId].progress === percent &&
                prev[currentFileId].stage === stage &&
                prev[currentFileId].status === status)
            ) {
              return prev;
            }

            return {
              ...prev,
              [currentFileId]: {
                ...prev[currentFileId],
                progress: percent,
                stage,
                status,
                error: progressData?.error,
                document_name: progressData?.document_name
              },
            };
          });
        } catch (error) {
          if (cancelled) return;
          console.error("Error fetching progress for file", docId, error);
        }
      }
    };

    pollProgress();

    const intervalId = window.setInterval(pollProgress, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [docFileId]);



  useEffect(() => {
    if (!applicationNumber) return;

    const fetchPendingDocs = async () => {
      try {
        const res: any =
          await DocumentApi.documentRecommentation(applicationNumber);
        const data = (await res) as Record<string, unknown>;
        const pendingDocs =
          (data.pending_documents as Record<string, unknown>[]) || [];

        const mappedRequiredDocs: RequiredDocument[] = pendingDocs.map(
          (doc: Record<string, unknown>) => ({
            id: (doc.document_name as string)
              .toLowerCase()
              .replace(/\s+/g, "_"),
            name: doc.document_name as string,
            upload_type: ((doc.status as string) === "pending"
              ? "multiple"
              : "single") as "single" | "multiple",
            uploaded: false,
            completed: false,
            reason: (doc.reason as string) || "",
            explanation: (doc.explanation as string) || "",
            files: [],
          }),
        );

        setRequiredDocs(mappedRequiredDocs);
      } catch (err) {
        console.error("Error fetching pending documents:", err);
      }
    };

    // fetchPendingDocs();
  }, [applicationNumber]);

  const generateDocId = (docName: string) => {
    const docKey = docName.toUpperCase().replace(/\s+/g, "");
    return `${applicationNumber}-${docKey}`;
  };

  const handleRequiredDocUpload = (
    docId: string,
    file: File,
    docName: string,
  ) => {
    const newEntry: DocumentData = {
      id: generateDocId(docName),
      filetype: docName.replaceAll("_", " "),
      file,
      meta: {
        title: docName,
        uploadedBy: "Hema",
        uploadDate: new Date().toLocaleDateString(),
      },
    };

    setData((prev) => [...prev, newEntry]);

    setRequiredDocs((prev: RequiredDocument[]) =>
      prev.map((doc: RequiredDocument) =>
        doc.id === docId
          ? { ...doc, uploaded: true, file, uniqueId: newEntry.id }
          : doc,
      ),
    );
  };

  const handleAnalysis = (record: DocumentData) => {
    setSelectedDoc(record);
    form.resetFields();
    if (record.json && Object.keys(record.json).length > 0) {
      const flatData: Record<string, unknown> = {};
      flattenData(record.json).forEach((item) => {
        flatData[item.namePath.join(".")] = item.value; // nested keys
      });

      setAnalysisData(record.json);
      form.setFieldsValue(flatData);
    } else {
      setAnalysisData(null);
    }

    setModalVisible(true);
  };

  const handleDelete = async (record: DocumentData) => {
    // Show loading
    messageApi.open({
      type: "loading",
      content: `Deleting ${record.filetype}...`,
      key: "delete",
      duration: 0, // keep open until manually closed
    });

    try {

      const res: any = await DocumentApi.documentDeleteApi(record.id);

      if (!res) {
        // const errData = await res?.json();
        throw new Error("Delete failed");
      }

      // Close loading + show success
      messageApi.open({
        type: "success",
        content: "Document deleted successfully",
        key: "delete",
        duration: 2,
      });

      // Trigger refresh by updating refreshKey
      setUploadingFiles((prev) => {
        const next = { ...prev };
        delete next[record.id];
        return next;
      });
      setRefreshKey((k) => k + 1);
      setConfirmVisible(false);
      setTriggerReport((prev: any) => prev + 1);
    } catch (error: unknown) {
      const err = error as Error;
      // Close loading + show error
      messageApi.open({
        type: "error",
        content: err.message || "Unable to delete document",
        key: "delete",
        duration: 2,
      });
      console.error(err);
    }
  };

  const handleCompare = async (mode: "text" | "image") => {
    // ON: show loading message
    messageApi.open({
      type: "loading",
      content: "Comparing...",
      key: "compare",
      duration: 0, // keep open manually
    });

    if (selectedRowKeys.length !== 2) {
      messageApi.destroy("compare");
      return Modal.warning({
        title: "Please select exactly 2 documents to compare",
      });
    }

    const [doc1, doc2] = data.filter((d) => selectedRowKeys.includes(d.id));

    try {
      const res: any = await DocumentApi.compareDocuments(
        applicationNumber,
        doc1.id,
        doc2.id,
        mode,
      );
      const result = (await res) as {
        oldText?: string;
        newText?: string;
        type?: string;
        image1?: string;
        image2?: string;
      };

      if (mode === "image" && result.type === "image") {
        setImage1(result.image1 as string);
        setImage2(result.image2 as string);
      } else {
        setDiffData(result);
      }

      // OFF + Success message
      messageApi.open({
        type: "success",
        content: "Comparison complete!",
        key: "compare",
        duration: 2,
      });

      setCompareModalOpen(true);
    } catch (err) {
      // OFF + Error message
      messageApi.open({
        type: "error",
        content: "Comparison failed!",
        key: "compare",
        duration: 2,
      });

      console.error(err);
    }
  };

  const menuItems = (record: DocumentData): MenuProps["items"] => [
    {
      key: "analysis",
      label: <span>Analysis</span>,
      onClick: () => handleAnalysis(record),
    },
    {
      key: "delete",
      danger: true,
      label: <span>Delete</span>,
      onClick: () => {
        (setConfirmVisible(true), setDeleteData(record));
      },
    },
  ];

  const fileTypeMap: Record<string, string> = {
    "LegalReport": "Legal Report",
    "Memorandum of Deposit of Title Deeds": "Memorandum of Deposit of Title Deed",
  };


  const columns: TableColumnsType<DocumentData> = [

    {
      title: "Document Name",
      dataIndex: "document_name",
      width: "350px",
      render: (value: number | string, record: DocumentData) => (

        <>
          <span
            className={`cursor-pointer hover:underline ${record.progress !== undefined ? "text-gray-400 cursor-not-allowed" : "text-blue-700"}`}
            onClick={() =>
              record.progress === undefined && handleAnalysis(record)
            }
          >
            {record?.document_name
              ? record.document_name?.replaceAll("_", " ")?.toString().slice(0, 38)
              : record?.id
                ? record.id.toString().slice(0, 38)
                : ""}
          </span>
        </>
      ),
    },
    {
      title: "File Type", dataIndex: "filetype",
      render: (value: number | string, record: DocumentData) => (

        <>
          <span>
            {fileTypeMap[record?.filetype] || record?.filetype || ""}
          </span>
        </>
      ),
    },
    {
      title: "Progress Status",
      key: "progress",
      width: "250px",
      render: (_: any, record: any) => {
        const isFailed =
          record.status?.toLowerCase() === "failed" ||
          record.stage?.toLowerCase().includes("failed");
        return record?.progress !== undefined ? (
          <div className="flex flex-col w-full min-w-[150px]">
            <div className="flex justify-between items-center text-xs mb-1">
              <span
                className={`truncate max-w-[120px] ${isFailed ? "text-red-500 font-medium" : "text-gray-600"}`}
                title={record.stage}
              >
                {record.stage || "Uploading..."}
              </span>
              <span
                className={`font-medium ${isFailed ? "text-red-600" : "text-primary-600"}`}
              >
                {record.progress}%
              </span>
            </div>
            {isFailed && record.error ? (
              <span
                className="mt-1 text-[11px] text-red-600 truncate"
                title={record.error}
              >
                {record.error}
              </span>
            ) : null}
            <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-1.5 rounded-full transition-all duration-300 ease-out ${isFailed ? "bg-red-500" : "bg-primary-500"}`}
                style={{ width: `${record.progress}%` }}
              ></div>
            </div>
          </div>
        ) : (
          <div className="flex items-center">
            {record.error ? (
              <span className="flex items-center bg-red-500 text-white px-[6px] py-0.5 text-[12px] font-medium border border-red-200 rounded-full">
                <RxCross2 className="text-red-500 bg-white rounded-full p-[2px] mr-1 text-[12px]" />
                <span className="block">Error</span>
              </span>
            ) : (
              <span className="flex items-center bg-green-500 text-white px-[6px] py-0.5 text-[12px] font-medium border border-green-200 rounded-full">
                <FaCheck className="text-green-500 bg-white rounded-full p-[2px] mr-1 text-[12px]" />
                <span className="block">Completed</span>
              </span>
            )}
          </div>
        );
      },
    },
    // {title: "Status" , dataIndex: "status"},
    {
      title: "Action",
      key: "action",
      render: (_, record) => {
        const isFailed =
          record.status?.toLowerCase() === "failed" ||
          record.stage?.toLowerCase().includes("failed");
        if (record.progress !== undefined && !isFailed) {
          return (
            <span className="text-gray-400 cursor-not-allowed">
              <BsThreeDotsVertical />
            </span>
          );
        }

        const menu =
          record.progress !== undefined && isFailed
            ? [
              {
                key: "delete",
                danger: true,
                label: <span>Discard Failed Upload</span>,
                onClick: () => {
                  setConfirmVisible(true);
                  setDeleteData(record);
                },
              },
            ]
            : menuItems(record);

        return (
          <Dropdown trigger={["click"]} menu={{ items: menu }}>
            <span
              onClick={(e) => e.preventDefault()}
              style={{ cursor: "pointer", display: "inline-flex" }}
            >
              <BsThreeDotsVertical />
            </span>
          </Dropdown>
        );
      },
    },
  ];

  const flattenData = (
    obj: Record<string, unknown>,
    parentPath: string[] = [],
  ): { label: string; namePath: (string | number)[]; value: unknown }[] => {
    return Object.entries(obj).flatMap(([key, value]) => {
      const currentPath = [...parentPath, key];
      const label = currentPath.join(" > ");
      if (typeof value === "object" && value !== null) {
        return flattenData(value as Record<string, unknown>, currentPath);
      }
      return [{ label, namePath: currentPath, value }];
    });
  };


  return (
    <div>
      {contextHolder}
      <div className="grid grid-cols-12 grid-rows-1 gap-4">
        <div className="col-span-12 shadow-md border border-gray-100 rounded-lg bg-white min-h-[80vh]">
          <div className="p-4">
            <div className="flex justify-between items-center mb-6">
              <h1 className="text-[20px] font-bold text-stone-800 mb-0">
                Documents Table
              </h1>
              <button
                onClick={() => setUploadModalVisible(true)}
                className="flex items-center gap-2 bg-primary-500 hover:bg-primary-600 cursor-pointer text-white px-4 py-2 rounded-lg transition-colors"
              >
                <IoCloudUploadOutline className="text-lg" />
                Upload Document
              </button>
            </div>

            <div>
              <Table<DocumentData>
                rowSelection={rowSelection}
                loading={loading}
                columns={columns}
                dataSource={combinedData}
                scroll={{ x: "max-content" }}
                bordered
                rowKey="id"
              />
            </div>
          </div>
        </div>
      </div>

      <Modal
        title={
          <h1 className="text-[18px] font-semibold mb-6">Upload Document</h1>
        }
        open={uploadModalVisible}
        onCancel={() => {
          (setUploadModalVisible(false),
            formUpload.resetFields(),
            setPreviewUrl(""),
            setPreviewType(""),
            setFileList([]),
            setIsPreviewExpanded(false));
        }}
        footer={null}
        width={isPreviewExpanded ? "98%" : "80%"}
        style={isPreviewExpanded ? { top: 10, maxWidth: "100%" } : {}}
        styles={{ body: isPreviewExpanded ? { height: "85vh" } : {} }}
        centered={!isPreviewExpanded}
      >
        <UploadForm
          onUploadSuccess={handleUploadSuccess}
          onCancel={() => setUploadModalVisible(false)}
          recommendedDocs={requiredDocs.map((d) => d.name)}
          setFileId={(id, docType) => {
            if (docType) {
              handleUploadStarted(id, docType);
            }
            setFileId(id);
          }}
          setOpen={setOpen}
          token={token}
          formUpload={formUpload}
          previewUrl={previewUrl}
          setPreviewUrl={setPreviewUrl}
          previewType={previewType}
          setPreviewType={setPreviewType}
          fileList={fileList}
          setFileList={setFileList}
          isPreviewExpanded={isPreviewExpanded}
          setIsPreviewExpanded={setIsPreviewExpanded}
        />
      </Modal>
      <AnalysisModal
        open={modalVisible}
        onClose={() => {
          (setModalVisible(false), setEditMode(false));
        }}
        analysisData={analysisData}
        selectedDoc={selectedDoc}
        form={form}
        editMode={editMode}
        onToggleEdit={() => setEditMode(true)}
        onSave={handleEditSave}
        analysisLoading={analysisLoading}
        setAnalysisLoading={setAnalysisLoading}
        token={token}
      />
      <CompareModel
        open={compareModalOpen}
        onClose={() => setCompareModalOpen(false)}
        diffData={diffData || undefined}
      />

      {/* Confirmation Modal */}
      <Modal
        open={confirmVisible}
        onOk={() => handleDelete(deleteData)}
        onCancel={() => setConfirmVisible(false)}
        okText="Yes, Delete"
        cancelText="Cancel"
        title="Are you sure?"
        okType="danger"
        okButtonProps={{
          className: " hover:!text-white hover:!bg-[#ff4d4f] border-red-600",
        }}
      >
        <p>Are you sure you want to delete this file?</p>
      </Modal>
    </div>
  );
}