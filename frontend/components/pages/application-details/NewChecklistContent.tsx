import React, { useState, useEffect, useRef } from "react";
import {
  Collapse,
  Divider,
  Table,
  Tag,
  Button,
  message,
  Space,
  Dropdown,
  MenuProps,
  ConfigProvider,
  Segmented,
  Input,
  Form,
  DatePicker,
} from "antd";
import dayjs, { Dayjs } from "dayjs";
import type { ColumnsType } from "antd/es/table";
import {
  ChecklistApi,
  ChecklistItem,
  ChecklistStatusResponse,
} from "@/src/services/ChecklistApi";
import CheckListEditModel from "./CheckListEditModel";
import customParseFormat from "dayjs/plugin/customParseFormat";
import utc from "dayjs/plugin/utc";
import { FaEdit, FaRegPlayCircle, FaRegSave } from "react-icons/fa";
import { ImCancelCircle } from "react-icons/im";
import { GiCancel } from "react-icons/gi";
import { FaRegCirclePlay, FaArrowRightLong, FaArrowLeftLong } from "react-icons/fa6";
import { RiErrorWarningLine } from "react-icons/ri";
import { useAppContext } from "@/context/GlobalContext";

const { Panel } = Collapse;

interface NewChecklistContentProps {
  applicationId: string;
  setTriggerReport: any;
}

interface ContextType {
  user: string | null;
  setUser: (user: string | null) => void;
};

const statusColorMap: Record<string, string> = {
  MATCH: "bg-green-400 text-white ",
  MISMATCH: "bg-red-400 text-white ",
  NA: "",
};

const StatusTag = (status: string) => {
  const classes = statusColorMap[status] || "";

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${classes}`}
    >
      {status === "NOT_AVAILABLE" ? "-" : status.toLowerCase() || "-"}
    </span>
  );
};

const getStatusTag = (status: string) => {
  if (status === "MATCH") return <Tag color="green">Match</Tag>;
  if (status === "MISMATCH") return <Tag color="red">Mismatch</Tag>;
  return <Tag color="default">N/A</Tag>;
};

const NewChecklistContent: React.FC<NewChecklistContentProps> = ({
  applicationId,
  setTriggerReport
}): React.ReactElement => {
  const [data, setData] = useState<ChecklistItem[]>([]);
  const [loading, setLoading] = useState(false);

  const [editingRecord, setEditingRecord] = useState<any>([]);
  const [editModalOpen, setEditModalOpen] = useState<boolean>(false);
  const [refreshTrigger, setRefreshTrigger] = React.useState(0);
  const [editMode, setEditMode] = useState<boolean>(false);
  const [showSave, setShowSave] = useState<boolean>(false);
  const [apiPayload, setApiPayload] = useState<any>([]);
  const [getRunvalid, setGetRunvalid] = useState<any>();
  const [saveCheckLoading, setSaveCheckLoading] = useState<boolean>(false);
  const [runLoading, setRunLoading] = useState<boolean>(false);
  const [showEdit, setShowEdit] = useState<boolean>(false);
  const [showRun, setShowRun] = useState<number>(0);
  const [checklistProgress, setChecklistProgress] = useState<number>(0);
  const [checklistStage, setChecklistStage] = useState<string>("");

  const [messageApi, contextHolder] = message.useMessage();

  const { progressId, setProgressId } = useAppContext();

  const [formSL] = Form.useForm();
  const [formMODT] = Form.useForm();
  const checklistPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopChecklistPolling = () => {
    if (checklistPollRef.current) {
      clearInterval(checklistPollRef.current);
      checklistPollRef.current = null;
    }
  };


  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await ChecklistApi.getChecklist(applicationId);
      const checklistResponse = response as ChecklistItem[] | ChecklistStatusResponse;
      const items = Array.isArray(checklistResponse)
        ? checklistResponse
        : Array.isArray(checklistResponse?.items)
          ? checklistResponse.items
          : [];
      const rerunValidation = Array.isArray(checklistResponse)
        ? Number(checklistResponse?.[0]?.rerun_validation ?? 0)
        : Number(checklistResponse?.rerun_validation ?? 0);

      const valid = items.every(
        (res) => res?.document_a_value == null && res?.document_b_value == null,
      );
      setShowEdit(valid);
      setShowRun(rerunValidation);
      setData(items);
    } catch (err) {
      console.error("Error fetching checklist:", err);
      message.error("Failed to fetch checklist data");
    } finally {
      setLoading(false);
    }
  };

  const pollChecklistTask = (taskId: string) => {
    // Clear any existing interval before starting a new one
    stopChecklistPolling();

    setRunLoading(true);
    setChecklistProgress(0);
    setChecklistStage("Checklist validation queued");


    const checkStatus = async () => {
      try {
        const statusRes: any = await ChecklistApi.getProgress(taskId);
        if (typeof statusRes?.progress === "number") {
          setChecklistProgress(statusRes.progress);
        }
        if (statusRes?.stage) {
          setChecklistStage(statusRes.stage);
        }
        const status = String(statusRes?.status || "").toLowerCase();
        if (status === "completed" || status === "success") {
          stopChecklistPolling();
          setRunLoading(false);
          setChecklistProgress(100);
          setChecklistStage("Checklist validation completed");
          setRefreshTrigger((pre) => pre + 1);
          setProgressId(null)
          return;
        }
        if (status === "failed" || status === "failure") {
          stopChecklistPolling();
          setRunLoading(false);
          setChecklistProgress(0);
          setChecklistStage("Checklist validation failed");
          message.error("Checklist validation failed");
          setRefreshTrigger((pre) => pre + 1);
          setProgressId(null)
        }
      } catch (err) {
        stopChecklistPolling();
        setRunLoading(false);
        setChecklistProgress(0);
        setChecklistStage("Checklist validation failed");
        setProgressId(null)
      }
    };

    checkStatus();
    checklistPollRef.current = setInterval(checkStatus, 5000);
  };

  useEffect(() => {
    if (progressId != null) {
      pollChecklistTask(progressId)
    }
    // Cleanup function to clear interval when progressId changes or component unmounts
    return () => {
      stopChecklistPolling();
    };
  }, [progressId])

  const fetchRunValidate = async (applicationId: any) => {
    const payload = {
      Application_number: applicationId,
    };
    setRunLoading(true);
    try {
      const response: any = await ChecklistApi.getRunValidate(payload);
      setGetRunvalid(response);
      if (response?.task_id) {
        setProgressId(response?.task_id)
        pollChecklistTask(response.task_id);
      } else {
        setRefreshTrigger((pre) => pre + 1);
        setRunLoading(false);
      }
    } catch (err) {
      console.error("Error fetching checklist:", err);
      message.error("Failed to fetch run validate data");
      setRunLoading(false);
    }
  };


  useEffect(() => {
    if (applicationId) {
      fetchData();
      // restoreActiveChecklistTask();
    }
  }, [applicationId, refreshTrigger]);

  const handleTriggerAnalysis = async () => {
    setLoading(true);
    try {
      await ChecklistApi.triggerMatching(applicationId);
      message.success("Checklist analysis triggered successfully");
      await fetchData();
    } catch (err) {
      console.error("Error triggering analysis:", err);
      message.error("Failed to trigger checklist analysis");
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<ChecklistItem> = [
    {
      title: "Attribute",
      dataIndex: "attribute_label",
      key: "attribute",
    },
    {
      title: "Document A Value", // Will be overridden in render for specific tables
      dataIndex: "document_a_value",
      key: "doc_a",
      render: (text: string) => text || "-",
    },
    {
      title: "Document B Value", // Will be overridden in render for specific tables
      dataIndex: "document_b_value",
      key: "doc_b",
      render: (text: string) => text || "-",
    },
    {
      title: "Status",
      dataIndex: "match_status",
      key: "status",
      render: (status: string) => StatusTag(status),
    },

  ];

  dayjs.extend(customParseFormat);
  dayjs.extend(utc);

  const parseToDayjs = (
    date: string | Dayjs | null | undefined,
  ): Dayjs | null => {
    if (!date) return null;

    if (dayjs.isDayjs(date)) return date;

    if (typeof date !== "string") return null;

    // ISO format
    if (date.includes("T")) {
      return dayjs(date); // ❌ removed utc to avoid shifting
    }

    const formats = [
      "DD/MM/YYYY",
      "DD-MM-YYYY",
      "DD/MM/YY", // ✅ added
      "DD-MM-YY", // ✅ optional
    ];

    for (const format of formats) {
      const parsed = dayjs(date, format, true);
      if (parsed.isValid()) return parsed;
    }

    return null;
  };

  const sl_la_data = data
    .filter((d) => d.pair_code === "SL_LA")
    .map((res: any) => ({
      ...res,
      document_a_value:
        res.attribute_code === "date"
          ? res.document_a_value &&
          parseToDayjs(res.document_a_value)?.format("DD/MM/YYYY")
          : res.document_a_value,
      document_b_value:
        res.attribute_code === "date"
          ? res.document_b_value &&
          parseToDayjs(res.document_b_value)?.format("DD/MM/YYYY")
          : res.document_b_value,
    }));
  const modt_sd_data = data.filter((d) => d.pair_code === "MODT_SD");

  const getStats = (items: ChecklistItem[]) => {
    const match = items.filter((d) => d.match_status === "MATCH").length;
    const mismatch = items.filter((d) => d.match_status === "MISMATCH").length;
    const na = items.filter((d) => d.match_status === "NOT_AVAILABLE").length;
    return { match, mismatch, na };
  };

  const sl_stats = getStats(sl_la_data);
  const modt_stats = getStats(modt_sd_data);

  // Dynamic columns for specific pairs

  const debounceRef = useRef<any>(null);

  const handleChange = (record: any, value: any, type: string) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      setPayloadFun(record, value, type);
    }, 400);
  };

  const setPayloadFun = (record: any, value: any, type: string) => {
    setApiPayload((prev: any[]) => {
      const existingIndex = prev.findIndex(
        (item) => item.attribute_code === record.attribute_code,
      );

      const formattedValue =
        record.attribute_code === "date"
          ? (parseToDayjs(value)?.format("DD/MM/YYYY") ?? null)
          : (value ?? null);

      if (existingIndex !== -1) {
        const updated = [...prev];

        updated[existingIndex] = {
          ...updated[existingIndex],
          document_a_value:
            type === "doc_a"
              ? formattedValue
              : (updated[existingIndex].document_a_value ?? null),
          document_b_value:
            type === "doc_b"
              ? formattedValue
              : (updated[existingIndex].document_b_value ?? null),
        };

        return updated;
      }

      return [
        ...prev,
        {
          application_number: record.application_number,
          attribute_code: record.attribute_code,
          document_a_value:
            type === "doc_a" ? formattedValue : (record?.document_a_value ?? null),
          document_b_value:
            type === "doc_b" ? formattedValue : (record?.document_b_value ?? null),
        },
      ];
    });
  };

  const formats = ["DD/MM/YYYY", "DD-MM-YYYY", "DD/MM/YY", "DD-MM-YY"];

  const slCols = [
    {
      title: "Attribute",
      dataIndex: "attribute_label",
      key: "attribute",
      width: 200,
    },
    {
      title: "SANCTION LETTER",
      dataIndex: "document_a_value",
      key: "doc_a",
      render: (_: any, record: any) => {
        const checkDateValidA: boolean = record?.attribute_code == "date";
        const dateValueA: any = parseToDayjs(record?.document_a_value);

        return editMode ? (
          checkDateValidA ? (
            <Form.Item
              name={`sanctionLetter${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={dateValueA}
            >
              <DatePicker
                onChange={(date) => {
                  (setShowSave(true), handleChange(record, date, "doc_a"));
                }}
                format={formats}
                style={{ width: "100%" }}
              />
            </Form.Item>
          ) : record?.attribute_code == "loan_amount" ? (
            <Form.Item
              name={`sanctionLetter${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={record.document_a_value}
            >
              <Input
                prefix="₹"
                onChange={(e) => {
                  (setShowSave(true),
                    handleChange(record, e.target.value, "doc_a"));
                }}
              />
            </Form.Item>
          ) : (
            <Form.Item
              name={`sanctionLetter${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={record.document_a_value}
            >
              <Input.TextArea
                autoSize={{ minRows: 1, maxRows: 10 }}
                onChange={(e) => {
                  (setShowSave(true),
                    handleChange(record, e.target.value, "doc_a"));
                }}
              />
            </Form.Item>
          )
        ) : (
          record.document_a_value || "-"
        );
      },
    },
    ...(editMode ? [{
      title: "",
      key: "actions",
      width: 60,
      align: "center" as const,
      render: (_: any, record: any) => {
        const nameA = `sanctionLetter${record.attribute_code}`;
        const nameB = `loanAgreement${record.attribute_code}`;
        const handleCopyAtoB = () => {
          const valA = formSL.getFieldValue(nameA);
          formSL.setFieldsValue({ [nameB]: valA });
          setShowSave(true);
          handleChange(record, valA, "doc_b");
        };
        const handleCopyBtoA = () => {
          const valB = formSL.getFieldValue(nameB);
          formSL.setFieldsValue({ [nameA]: valB });
          setShowSave(true);
          handleChange(record, valB, "doc_a");
        };
        return (
          <div className="flex flex-col gap-1.5 items-center justify-center">
            <button
              type="button"
              onClick={handleCopyAtoB}
              className="flex items-center justify-center bg-gray-50 border border-gray-200 hover:border-blue-400 hover:bg-blue-400 hover:text-white transition-all duration-200 rounded-[7px] shadow-sm cursor-pointer"
              style={{
                height: "26px",
                width: "26px",
                padding: 0,
              }}
              title="Copy Left to Right"
            >
              <FaArrowRightLong className="text-[13px]" />
            </button>
            <button
              type="button"
              onClick={handleCopyBtoA}
              className="flex items-center justify-center bg-gray-50 border border-gray-200 hover:border-blue-400 hover:bg-blue-400 hover:text-white transition-all duration-200 rounded-[7px] shadow-sm cursor-pointer"
              style={{
                height: "26px",
                width: "26px",
                padding: 0,
              }}
              title="Copy Right to Left"
            >
              <FaArrowLeftLong className="text-[13px]" />
            </button>
          </div>
        );
      }
    }] : []),
    {
      title: "LOAN AGREEMENT",
      dataIndex: "document_b_value",
      key: "doc_b",
      render: (_: any, record: any) => {
        const checkDateValidB: boolean = record?.attribute_code == "date";
        const dateValueB: any = parseToDayjs(record?.document_b_value);

        return editMode ? (
          checkDateValidB ? (
            <Form.Item
              name={`loanAgreement${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={dateValueB}
            >
              <DatePicker
                onChange={(date) => {
                  (setShowSave(true), handleChange(record, date, "doc_b"));
                }}
                format={formats}
                style={{ width: "100%" }}
              />
            </Form.Item>
          ) : record?.attribute_code == "loan_amount" ? (
            <Form.Item
              name={`loanAgreement${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={record.document_b_value}
            >
              <Input
                prefix="₹"
                onChange={(e) => {
                  (setShowSave(true),
                    handleChange(record, e.target.value, "doc_b"));
                }}
              />
            </Form.Item>
          ) : (
            <Form.Item
              name={`loanAgreement${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={record.document_b_value}
            >
              <Input.TextArea
                onChange={(e) => {
                  (setShowSave(true),
                    handleChange(record, e.target.value, "doc_b"));
                }}
                autoSize={{ minRows: 1, maxRows: 10 }}
              />
            </Form.Item>
          )
        ) : (
          record.document_b_value || "-"
        );
      },
    },
    {
      title: "Status",
      dataIndex: "match_status",
      key: "status",
      width: 150,
      render: (status: string) => StatusTag(status),
    },
  ];

  const modtCols = [
    {
      title: "Attribute",
      dataIndex: "attribute_label",
      key: "attribute",
      width: 200,
    },
    {
      title: "MODT",
      dataIndex: "document_a_value",
      key: "doc_a",
      render: (_: any, record: any) => {
        const checkDateValidA: boolean = record?.attribute_code == "date";
        const dateValueA: any = parseToDayjs(record?.document_a_value);

        return editMode ? (
          checkDateValidA ? (
            <Form.Item
              name={`MODT${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={dateValueA}
            >
              <DatePicker
                onChange={(date) => {
                  (setShowSave(true), handleChange(record, date, "doc_a"));
                }}
                format={formats}
                style={{ width: "100%" }}
              />
            </Form.Item>
          ) : (
            <Form.Item
              name={`MODT${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={record.document_a_value}
            >
              <Input.TextArea
                onChange={(e) => {
                  (setShowSave(true),
                    handleChange(record, e.target.value, "doc_a"));
                }}
                autoSize={{ minRows: 1, maxRows: 10 }}
              />
            </Form.Item>
          )
        ) : (
          record.document_a_value || "-"
        );
      },
    },
    ...(editMode ? [{
      title: "",
      key: "actions",
      width: 60,
      align: "center" as const,
      render: (_: any, record: any) => {
        const nameA = `MODT${record.attribute_code}`;
        const nameB = `saleDeed${record.attribute_code}`;
        const handleCopyAtoB = () => {
          const valA = formMODT.getFieldValue(nameA);
          formMODT.setFieldsValue({ [nameB]: valA });
          setShowSave(true);
          handleChange(record, valA, "doc_b");
        };
        const handleCopyBtoA = () => {
          const valB = formMODT.getFieldValue(nameB);
          formMODT.setFieldsValue({ [nameA]: valB });
          setShowSave(true);
          handleChange(record, valB, "doc_a");
        };
        return (
          <div className="flex flex-col gap-1.5 items-center justify-center">
            <button
              type="button"
              onClick={handleCopyAtoB}
              className="flex items-center justify-center bg-gray-50 border border-gray-200 hover:border-blue-400 hover:bg-blue-400 hover:text-white transition-all duration-200 rounded-lg shadow-sm cursor-pointer"
              style={{
                height: "26px",
                width: "26px",
                padding: 0,
              }}
              title="Copy Left to Right"
            >
              <FaArrowRightLong className="text-[13px]" />
            </button>
            <button
              type="button"
              onClick={handleCopyBtoA}
              className="flex items-center justify-center bg-gray-50 border border-gray-200 hover:border-blue-400 hover:bg-blue-400 hover:text-white transition-all duration-200 rounded-lg shadow-sm cursor-pointer"
              style={{
                height: "26px",
                width: "26px",
                padding: 0,
              }}
              title="Copy Right to Left"
            >
              <FaArrowLeftLong className="text-[13px]" />
            </button>
          </div>
        );
      }
    }] : []),
    {
      title: "SALE DEED",
      dataIndex: "document_b_value",
      key: "doc_b",
      render: (_: any, record: any) => {
        const checkDateValidB: boolean = record?.attribute_code == "date";
        const dateValueB: any = parseToDayjs(record?.document_b_value);

        return editMode ? (
          checkDateValidB ? (
            <Form.Item
              name={`saleDeed${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={dateValueB}
            >
              <DatePicker
                onChange={(date) => {
                  (setShowSave(true), handleChange(record, date, "doc_b"));
                }}
                format={formats}
                style={{ width: "100%" }}
              />
            </Form.Item>
          ) : (
            <Form.Item
              name={`saleDeed${record.attribute_code}`}
              style={{ margin: 0 }}
              initialValue={record.document_b_value}
            >
              <Input.TextArea
                onChange={(e) => {
                  (setShowSave(true),
                    handleChange(record, e.target.value, "doc_b"));
                }}
                autoSize={{ minRows: 1, maxRows: 10 }}
              />
            </Form.Item>
          )
        ) : (
          record.document_b_value || "-"
        );
      },
    },
    {
      title: "Status",
      dataIndex: "match_status",
      key: "status",
      width: 150,
      render: (status: string) => StatusTag(status),
    },
  ];

  const checkListSaveApi = async () => {
    // const values = await form.validateFields();
    setSaveCheckLoading(true);
    try {
      await ChecklistApi.updateChecklist(applicationId, apiPayload);
      messageApi.success("CheckList updated successfully");
      setTriggerReport((pre: any) => pre + 1)
    } catch (error) {
      messageApi.error("Failed to update");
    } finally {
      setLoading(false);
      setApiPayload([]);
      setRefreshTrigger((pre) => pre + 1);
      setShowSave(false);
      setEditMode(false);
      setSaveCheckLoading(false);
    }
  };

  return (
    <>
      {contextHolder}
      {showRun == 1 &&
        <div className="p-3 bg-yellow-100 border border-yellow-500 rounded-xl mb-2">
          <div className="flex items-center gap-2">
            <h1 className="text-yellow-800 text-[16px] "><RiErrorWarningLine size={20} /></h1>
            <h1 className="text-yellow-800 text-[16px] ">The documents have been updated. Kindly click Run Validation.</h1>
          </div>
        </div>}

      <div className="flex justify-between items-center rounded-tl-xl rounded-tr-xl bg-white p-6 sticky top-0 z-20">
        <h2 className="text-xl font-bold text-gray-800 m-0">
          Checklist Validation
        </h2>
        <div className="flex items-center gap-3">
          {showRun == 0 && <>
            {editMode ? (
              <Button
                onClick={() => {
                  setShowSave(false);
                  setEditMode(false);
                  setApiPayload([]);
                  formSL.resetFields();
                  formMODT.resetFields();
                }}
                type="text"
                className="!bg-gray-100"
              >
                <ImCancelCircle size={20} />
                Cancel Edit
              </Button>
            ) : (
              <Button
                disabled={showEdit}
                onClick={() => {
                  const slValues: any = {};
                  sl_la_data.forEach((item: any) => {
                     slValues[`sanctionLetter${item.attribute_code}`] = item.attribute_code === "date" ? parseToDayjs(item.document_a_value) : item.document_a_value;
                     slValues[`loanAgreement${item.attribute_code}`] = item.attribute_code === "date" ? parseToDayjs(item.document_b_value) : item.document_b_value;
                  });
                  formSL.setFieldsValue(slValues);

                  const modtValues: any = {};
                  modt_sd_data.forEach((item: any) => {
                     modtValues[`MODT${item.attribute_code}`] = item.attribute_code === "date" ? parseToDayjs(item.document_a_value) : item.document_a_value;
                     modtValues[`saleDeed${item.attribute_code}`] = item.attribute_code === "date" ? parseToDayjs(item.document_b_value) : item.document_b_value;
                  });
                  formMODT.setFieldsValue(modtValues);
                  
                  setEditMode(true);
                }}
                type={showEdit ? "dashed" : "primary"}
              >
                <FaEdit size={20} />
                Edit
              </Button>
            )}

            {editMode && (
              <Button
                disabled={!showSave}
                loading={saveCheckLoading}
                onClick={() => checkListSaveApi()}
                type={showSave ? "primary" : "dashed"}
              >
                {!saveCheckLoading && <FaRegSave size={20} />}Save and Re-run
              </Button>
            )}
          </>}

          {showRun == 1 && <Button
            loading={runLoading}
            onClick={() => fetchRunValidate(applicationId)}
            type={showRun == 1 ? "primary" : "dashed"}
          >
            {!runLoading && <FaRegCirclePlay size={20} />}Run Validation {runLoading && checklistProgress > 0 && `${checklistProgress}%`}
          </Button>}
        </div>

      </div>

      <div className="p-[0_24px_24px_24px] bg-white rounded-bl-xl rounded-br-xl shadow-md ">


        {/* SL_LA ACCORDION */}
        <div className="mb-6">
          <Collapse defaultActiveKey={["1"]} className="bg-gray-50 rounded-lg">
            <Panel
              header={
                <div className="flex justify-between w-full pr-4">
                  <span className="font-semibold text-gray-700">
                    Sanction Letter ↔ Loan Agreement
                  </span>

                </div>
              }
              key="1"
            >
              <Form form={formSL} preserve={false}>
                <Table
                  columns={slCols}
                  dataSource={sl_la_data}
                  rowKey="id"
                  pagination={false}
                  loading={loading}
                  bordered
                />
              </Form>
            </Panel>
          </Collapse>
        </div>

        {/* MODT_SD ACCORDION */}
        <div>
          <Collapse defaultActiveKey={["2"]} className="bg-gray-50 rounded-lg">
            <Panel
              header={
                <div className="flex justify-between w-full pr-4">
                  <span className="font-semibold text-gray-700">
                    MODT ↔ Sale Deed
                  </span>

                </div>
              }
              key="2"
            >
              <Form form={formMODT} component={false} preserve={false}>
                <Table
                  columns={modtCols}
                  dataSource={modt_sd_data}
                  rowKey="id"
                  pagination={false}
                  loading={loading}
                  bordered
                />
              </Form>
            </Panel>
          </Collapse>
        </div>
      </div>

      <CheckListEditModel
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onSuccess={() => setRefreshTrigger((prev) => prev + 1)}
        initialData={editingRecord}
      />
    </>
  );
};

export default NewChecklistContent;
