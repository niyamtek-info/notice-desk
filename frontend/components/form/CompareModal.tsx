import React from "react";
import { Modal, Tabs, Typography, Card } from "antd";
import type { TabsProps } from "antd";

const { Title } = Typography;

interface CompareModelProps {
  open: boolean;
  onClose: () => void;
  diffData?: {
    oldText?: string;
    newText?: string;
  };
}

// ---------------- UTILS ----------------

// Parse JSON-like string → object
const parseToObject = (raw: string) => {
  if (!raw) return {};
  try {
    const clean = raw.replace(/^[-+]\s*/, "").trim();
    const fixed = clean.replace(/'/g, '"');
    return JSON.parse(fixed);
  } catch (err) {
    console.error("JSON parse failed:", err, raw);
    return {};
  }
};

// Flatten nested JSON → dot notation
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const flattenObject = (obj: Record<string, any>, parent = "", res: Record<string, any> = {}) => {
  for (const key in obj) {
    const newKey = parent ? `${parent}.${key}` : key;
    if (typeof obj[key] === "object" && obj[key] !== null) {
      flattenObject(obj[key], newKey, res);
    } else {
      res[newKey] = obj[key];
    }
  }
  return res;
};

// Highlight differences row by row
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const highlightDiff = (oldObj: Record<string, any>, newObj: Record<string, any>) => {
  const rows: React.ReactNode[] = [];
  const allKeys = Array.from(new Set([...Object.keys(oldObj), ...Object.keys(newObj)]));

  allKeys.forEach((key) => {
    const oldVal = String(oldObj[key] ?? "-");
    const newVal = String(newObj[key] ?? "-");
    const isDifferent = oldVal !== newVal;

    rows.push(
      <tr key={key}>
        <td style={{ border: "1px solid #eee", padding: "6px", fontWeight: "bold" }}>{key}</td>
        <td
          style={{
            border: "1px solid #eee",
            padding: "6px",
            background: isDifferent ? "#ffeaea" : "#f9f9f9",
            color: isDifferent ? "red" : "black",
          }}
        >
          {oldVal ?? ""}
        </td>
        <td
          style={{
            border: "1px solid #eee",
            padding: "6px",
            background: isDifferent ? "#eaffea" : "#f9f9f9",
            color: isDifferent ? "green" : "black",
          }}
        >
          {newVal ?? ""}
        </td>
      </tr>
    );
  });

  return rows;
};

const CompareModel: React.FC<CompareModelProps> = ({ open, onClose, diffData }) => {
  const [oldObj, newObj] = [
    flattenObject(parseToObject(diffData?.oldText || "")),
    flattenObject(parseToObject(diffData?.newText || ""))
  ];

  return (
    <Modal
      title={<Title level={4}>Side by Side Comparison</Title>}
      open={open}
      onCancel={onClose}
      footer={null}
      width={900}
      centered
    >
      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "18px" }}>
        <thead>
          <tr style={{ background: "#fafafa" }}>
            <th style={{ border: "1px solid #eee", padding: "6px" }}>Field</th>
            <th style={{ border: "1px solid #eee", padding: "6px" }}>Old File</th>
            <th style={{ border: "1px solid #eee", padding: "6px" }}>New File</th>
          </tr>
        </thead>
        <tbody>{highlightDiff(oldObj, newObj)}</tbody>
      </table>
    </Modal>
  );
};

export default CompareModel;
