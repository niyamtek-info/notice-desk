"use client";

import React, { useState } from "react";
import {
  Modal,
  Table,
  Form,
  Input,
  Button,
  Select,
  Tooltip,
  Dropdown,
} from "antd";
import { MoreOutlined } from "@ant-design/icons";
import { FaPlus } from "react-icons/fa6";
import { useAppNoContext } from "@/context/AppNoContext";

interface ObservationData {
  key: string;
  id?: number; // Added optional ID
  observation: string;
  made_by: string;
  severity: string;
  status: "Processing" | "Success" | "Failed";
  comments: string;
  review_by: string;
}

interface ObservationProps {
  token: string;
}

const statusColors: Record<ObservationData["status"], string> = {
  Processing: "bg-blue-100 text-blue-800",
  Success: "bg-green-100 text-green-800",
  Failed: "bg-red-100 text-red-800",
};

export default function Observation({ token }: ObservationProps) {
  const { applicationNumber } = useAppNoContext();
  const [data, setData] = useState<ObservationData[]>([]);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    if (!applicationNumber) return;

    const fetchObservations = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/observations/${applicationNumber}`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (!res.ok) throw new Error("Failed to fetch observations");
        const json = await res.json();

        const mapped: ObservationData[] = (
          json.recommended_documents || []
        ).map((doc: Record<string, unknown>, idx: number) => ({
          key: idx.toString(),
          id: doc.id as number,
          observation:
            (doc.title as string) ||
            (doc.explanation as string) ||
            (doc.observation as string),
          made_by: (doc.made_by as string) || "AI",
          severity: (doc.severity as string) || "Medium",
          status: (doc.status as string) || "Processing",
          comments: (doc.comments as string) || "",
          review_by: (doc.review_by as string) || "System",
        }));
        setData(mapped);
      } catch (err) {
        console.error("Error fetching observations:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchObservations();
  }, [applicationNumber]);

  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [modal, setModal] = useState<"view" | "edit" | "create" | null>(null);
  const [currentIdx, setCurrentIdx] = useState<number | null>(null);
  const [form] = Form.useForm();
  const [viewRecord, setViewRecord] = useState<ObservationData | null>(null);

  // Table Columns
  const columns = [
    {
      title: "Observation",
      dataIndex: "observation",
      width: "350px",
    },
    {
      title: "Made by",
      dataIndex: "made_by",
    },
    {
      title: "Severity",
      dataIndex: "severity",
      render: (text: string) => {
        let colorClass = "border-gray-500 bg-gray-100 text-gray-700";
        if (text === "High")
          colorClass = "border-red-500 bg-red-100 text-red-500";
        else if (text === "Medium")
          colorClass = "border-orange-500 bg-orange-100 text-orange-600"; // Orange doesn't have 500 text in all palettes, using 600 or just 500
        else if (text === "Low")
          colorClass = "border-green-500 bg-green-100 text-green-500";

        return (
          <span
            className={`border ${colorClass} text-[12px] px-2.5 py-1 rounded-[7px] text-center mx-auto block w-fit`}
          >
            {text || "-"}
          </span>
        );
      },
    },
    {
      title: "Status",
      dataIndex: "status",
      render: (_: string, record: ObservationData) => {
        let colorClass = "border-gray-500 bg-gray-100 text-gray-700";
        if (record.status === "Success")
          colorClass = "border-green-500 bg-green-100 text-green-500";
        else if (record.status === "Failed")
          colorClass = "border-red-500 bg-red-100 text-red-500";
        else if (record.status === "Processing")
          colorClass = "border-blue-500 bg-blue-100 text-blue-500";

        return (
          <span
            className={`border ${colorClass} text-[12px] px-2.5 py-1 rounded-[7px] text-center mx-auto block w-fit`}
          >
            {record.status}
          </span>
        );
      },
    },
    {
      title: "Review by",
      dataIndex: "review_by",
    },
    {
      title: "Comments",
      dataIndex: "comments",
      render: (text: string) => {
        const truncated = text.length > 50 ? text.slice(0, 50) + "..." : text;
        return (
          <Tooltip title={text}>
            <span>{truncated ? truncated : "-"}</span>
          </Tooltip>
        );
      },
    },
    {
      title: "Action",
      render: (_: unknown, record: ObservationData, idx: number) => (
        <Dropdown
          menu={{
            items: [
              {
                key: "view",
                label: (
                  <button
                    onClick={() => {
                      setModal("view");
                      setViewRecord(record);
                    }}
                  >
                    View
                  </button>
                ),
              },
              {
                key: "edit",
                label: (
                  <button
                    onClick={() => {
                      setModal("edit");
                      setCurrentIdx(idx);
                      form.setFieldsValue(record);
                    }}
                  >
                    Edit
                  </button>
                ),
              },
            ],
          }}
          trigger={["click"]}
        >
          <MoreOutlined style={{ cursor: "pointer", fontSize: 18 }} />
        </Dropdown>
      ),
    },
  ];

  // Create New
  function handleNew() {
    setModal("create");
    form.resetFields();
  }

  // Form Submit
  async function handleFinish(values: Record<string, unknown>) {
    let updated = [...data];
    if (modal === "edit" && currentIdx !== null) {
      updated[currentIdx] = {
        ...updated[currentIdx],
        ...(values as unknown as ObservationData),
      };
    } else if (modal === "create") {
      updated = [
        ...data,
        {
          ...(values as unknown as ObservationData),
          key: (data.length + 1).toString(),
        },
      ];
    }

    // Call API to save
    try {
      setLoading(true);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/observations/${applicationNumber}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            application_id: applicationNumber,
            recommended_documents: updated,
          }),
        },
      );

      if (!res.ok) throw new Error("Failed to save observations");

      // Reload from server to get generated IDs and timestamps
      const reloadRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/observations/${applicationNumber}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (reloadRes.ok) {
        const json = await reloadRes.json();
        const mapped: ObservationData[] = (
          json.recommended_documents || []
        ).map((doc: Record<string, unknown>, idx: number) => ({
          key: idx.toString(),
          id: doc.id as number,
          observation:
            (doc.title as string) ||
            (doc.explanation as string) ||
            (doc.observation as string),
          made_by: (doc.made_by as string) || "AI",
          severity: (doc.severity as string) || "Medium",
          status: (doc.status as string) || "Processing",
          comments: (doc.comments as string) || "",
          review_by: (doc.review_by as string) || "System",
        }));
        setData(mapped);
      } else {
        setData(updated);
      }

      setModal(null);
      setCurrentIdx(null);
      form.resetFields();
    } catch (err) {
      console.error("Error saving observations:", err);
    } finally {
      setLoading(false);
    }
  }

  // Modal Cancel
  function handleCancel() {
    setModal(null);
    setCurrentIdx(null);
    setViewRecord(null);
    form.resetFields();
  }

  return (
    <div className="py-4 pt-0">
      <div className="flex justify-between items-center mb-6 mt-1">
        <h1 className="text-[20px] font-bold text-stone-800 mb-0">
          Observation Table
        </h1>
        <button
          className="flex items-center !text-gray-50 !bg-primary-500 hover:bg-blue-800 focus:ring-1 focus:ring-primary-500 font-medium rounded-lg text-sm px-4 py-2 me-2 mb-2 cursor-pointer"
          onClick={handleNew}
        >
          <FaPlus className="mr-1.5" /> New Observation
        </button>
      </div>
      <Table
        loading={loading}
        rowSelection={{
          selectedRowKeys,
          onChange: (newSelectedRowKeys) =>
            setSelectedRowKeys(newSelectedRowKeys),
        }}
        columns={columns}
        dataSource={data}
        scroll={{ x: "max-content" }}
        bordered
      />

      {/* View Modal as Table */}
      <Modal
        title="Observation Details"
        open={modal === "view"}
        onCancel={handleCancel}
        footer={null}
        centered
      >
        {viewRecord && (
          <Table
            showHeader={false}
            pagination={false}
            dataSource={[
              { label: "Observation", value: viewRecord.observation },
              { label: "Made by", value: viewRecord.made_by },
              { label: "Severity", value: viewRecord.severity },
              { label: "Status", value: viewRecord.status },
              { label: "Comments", value: viewRecord.comments },
              { label: "Review by", value: viewRecord.review_by },
            ]}
            columns={[
              { title: "Field", dataIndex: "label", key: "label", width: 120 },
              { title: "Value", dataIndex: "value", key: "value" },
            ]}
            rowKey="label"
            bordered
          />
        )}
      </Modal>

      {/* Edit & Create Modal */}
      <Modal
        title={
          modal === "edit" ? (
            <h2 className="text-[18px] font-bold mb-5">Edit Observation</h2>
          ) : (
            <h2 className="text-[18px] font-bold mb-5">New Observation</h2>
          )
        }
        open={modal === "edit" || modal === "create"}
        width={800}
        onCancel={handleCancel}
        footer={null}
        centered
      >
        <Form
          form={form}
          name="observation"
          layout="vertical"
          onFinish={handleFinish}
          className="grid grid-cols-2 gap-x-4"
        >
          <Form.Item
            label="Observation"
            className="col-span-2"
            name="observation"
            rules={[{ required: true, message: "Required" }]}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            label="Severity"
            name="severity"
            rules={[{ required: true, message: "Required" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Made by"
            name="made_by"
            rules={[{ required: true, message: "Required" }]}
          >
            <Input />
          </Form.Item>

          <Form.Item label="Review by" name="review_by">
            <Input />
          </Form.Item>
          <Form.Item
            label="Status"
            name="status"
            rules={[{ required: true, message: "Required" }]}
          >
            <Select
              options={[
                { value: "Processing", label: "Processing" },
                { value: "Success", label: "Success" },
                { value: "Failed", label: "Failed" },
              ]}
            />
          </Form.Item>

          <Form.Item label="Comments" name="comments" className="col-span-2">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item className="flex justify-end !mt-5 !mb-0 col-span-2">
            <Button htmlType="submit" type="primary">
              {modal === "edit" ? "Save" : "Submit"}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
