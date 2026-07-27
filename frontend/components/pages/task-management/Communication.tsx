"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import {
  Select,
  Upload,
  Button,
  Form,
  Tooltip,
  Modal,
  Input,
  message,
  Dropdown,
  DatePicker,
  notification,
} from "antd";
import type { MenuProps } from "antd";
import {
  LoginOutlined,
  LogoutOutlined,
  UploadOutlined,
  EllipsisOutlined,
} from "@ant-design/icons";
import type { UploadFile } from "antd";
import dayjs from "dayjs";
import {
  EditorState,
  RichUtils,
  convertFromRaw,
  DraftInlineStyle,
} from "draft-js";
import "draft-js/dist/Draft.css";
import {
  FaBold,
  FaItalic,
  FaUnderline,
  FaStrikethrough,
  FaHeading,
  FaCode,
  FaQuoteRight,
  FaListUl,
  FaListOl,
  FaUndo,
  FaRedo,
  FaPaperPlane,
  FaWhatsapp,
  FaTelegram,
  FaSlack,
  FaDiscord,
  FaFilePdf,
  FaFileWord,
  FaSpinner,
} from "react-icons/fa";
import { IoIosMail } from "react-icons/io";

import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store";
import { StatusType, Task } from "@/store/slices/tasksSlice";
import {
  setEditorContent,
  setStructuredComponents,
} from "@/store/slices/communicationSlice";
import { addLog } from "@/src/utils/log";
import { addCommunicationLog } from "@/src/utils/communicationLog";
import { CommunicationApi } from "@/src/services/CommunicationApi";

import { log } from "console";
import { LuSend } from "react-icons/lu";
import { BankApi } from "@/src/services/BankApi";
import { useBank } from "@/context/BankContext";
import { saveAs } from "file-saver";
import * as htmlDocx from "html-docx-js-typescript";

// ✅ dynamically import Editor (fixes hydration error)
const Editor = dynamic(
  async () => {
    const mod = await import("draft-js");

    return function DraftEditorWithRef({
      editorRef,
      ...props
    }: React.ComponentProps<typeof mod.Editor> & {
      editorRef?: React.RefObject<any>;
    }) {
      return <mod.Editor ref={editorRef} {...props} />;
    };
  },
  {
    ssr: false,
  },
);

interface CommunicationProps {
  task?: Task;
  updateStatus?: (recordKey: string, newStatus: StatusType) => void;
  initialApplicationId?: string;
  token: string;
  bankCode: string;
  banks: any;
  banksLoading?: boolean;
  initialData: any;
}

type TemplateRenderMode = "standard" | "html" | "yaml";

const templates = [
  { id: "task", type: "Task Assignment Template" },
  { id: "13_2_notice_template", type: "SARFAESI 13(2) Notice Template" },
  { id: "S132/T/029", type: "SARFAESI 13(2) Notice (ICICI)" },
];

// Static AO code for testing; update this value to switch AO signatures.
const TEST_AO_CODE = "AO-001";

const injectSignatureHtml = (body: string, signatureHtml?: string) => {
  if (!body || !signatureHtml) return body;
  return body.replace(/\{\{\s*AO_SIGNATURE\s*\}\}/gi, signatureHtml);
};

export default function Communication({
  task,
  updateStatus,
  initialApplicationId,
  token,
  bankCode,
  banks,
  banksLoading,
  initialData
}: CommunicationProps) {
  const dispatch = useDispatch();
  const { editorContent, structuredComponents } = useSelector(
    (state: RootState) => state.communication,
  );

  const [editorState, setEditorState] = useState(() =>
    EditorState.createEmpty(),
  );
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [form] = Form.useForm();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [wordLoading, setWordLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [templateRenderMode, setTemplateRenderMode] =
    useState<TemplateRenderMode>("standard");
  const [htmlPreview, setHtmlPreview] = useState("");
  const [signatureHtml, setSignatureHtml] = useState("");
  const [templatesType, setTemplatesType] = useState([])
  const [clientSelectLoading, setClientSelectLoading] = useState<any>({
    template: false,
    aoCode: false
  });
  const [messageApi, contextHolder] = message.useMessage();
  const [notificationApi, notificationContextHolder] = notification.useNotification();
  const editorRef = useRef<any>(null);
  const htmlEditorRef = useRef<HTMLIFrameElement>(null);
  const { Option } = Select;
  const { selectedBank } = useBank();

  const focusEditor = () => {
    if (editorRef.current) {
      editorRef.current.focus();
    }
  };

  const [fetchedAos, setFetchedAos] = useState<any[]>([]);

  const handleFetchTemplate = async () => {
    const code = bankCode || selectedBank;
    if (!code || code === 'all') return;
    try {
      setClientSelectLoading((pre: any) => ({ ...pre, template: true }));
      let response: any = await BankApi.getSingleClientTemplate(code);
      setTemplatesType(response?.templates || []);
    } catch (error) { 
    } finally {
      setClientSelectLoading((pre: any) => ({ ...pre, template: false }));
    }
  }

  const handleFetchAOs = async () => {
    const code = bankCode || selectedBank;
    if (!code || code === 'all') return;
    try {
      setClientSelectLoading((pre: any) => ({ ...pre, aoCode: true }));
      let response: any = await BankApi.getBankCodeList(code);
      setFetchedAos(response?.aos || []);
    } catch (error) {
    } finally {
      setClientSelectLoading((pre: any) => ({ ...pre, aoCode: false }));
    }
  };

  const aoData = useMemo(() => {
    if (fetchedAos && fetchedAos.length > 0) return fetchedAos;
    let result = banks?.find((res: any) => res?.client_code == (bankCode || selectedBank))?.aos || []
    return result
  }, [banks, bankCode, selectedBank, fetchedAos])


  // Handle dropdown open change
  const handleDropdownOpenChange = (open: boolean, type: string) => {
    if (open) {
      if (type === 'aoCode') {
        handleFetchAOs();
      } else if (type === 'template') {
        handleFetchTemplate();
      } else {
        setClientSelectLoading((pre: any) => ({ ...pre, [type]: true }));
        setTimeout(() => {
          setClientSelectLoading((pre: any) => ({ ...pre, [type]: false }));
        }, 500);
      }
    }
  };


  useEffect(() => {
    if (initialApplicationId) {
      form.setFieldsValue({ applicationId: initialApplicationId });
    }
  }, [initialApplicationId, form]);

  useEffect(() => {
    setMounted(true); // ✅ only render Editor after hydration
  }, []);

  // 🔹 helper for rendering images & tables in Draft.js
  const mediaBlockRenderer = (block: any) => {
    if (block.getType() === "atomic") {
      return {
        component: (props: any) => {
          const entity = props.contentState.getEntity(
            props.block.getEntityAt(0),
          );
          const { src, rows, headers, title } = entity.getData();
          const type = entity.getType();

          if (type === "IMAGE" || type === "image") {
            return (
              <img
                src={src}
                alt="Logo"
                style={{
                  maxHeight: "60px",
                  margin: "10px 0",
                  display: "block",
                }}
              />
            );
          }

          if (type === "TABLE") {
            return (
              <div
                style={{
                  margin: "20px 0",
                  border: "1px solid #e2e8f0",
                  padding: "16px",
                  borderRadius: "8px",
                  backgroundColor: "#fff",
                }}
              >
                {title && (
                  <h4 className="text-sm font-bold mb-3 underline uppercase text-gray-700">
                    {title}
                  </h4>
                )}
                <div style={{ overflowX: "auto" }}>
                  <table
                    style={{
                      width: "100%",
                      borderCollapse: "collapse",
                      border: "1px solid #111",
                    }}
                  >
                    {headers && headers.length > 0 && (
                      <thead style={{ backgroundColor: "#f8fafc" }}>
                        <tr>
                          {headers.map((h: string, i: number) => (
                            <th
                              key={i}
                              style={{
                                border: "1px solid #111",
                                padding: "10px",
                                textAlign: "left",
                                fontSize: "13px",
                              }}
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                    )}
                    <tbody>
                      {rows.map((row: string[], ri: number) => (
                        <tr key={ri}>
                          {row.map((cell: string, ci: number) => (
                            <td
                              key={ci}
                              style={{
                                border: "1px solid #111",
                                padding: "10px",
                                fontSize: "13px",
                              }}
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          }
          return null;
        },
        editable: false,
      };
    }
    return null;
  };

  // 🔹 helper to update Draft.js + redux
  const setTemplateInEditor = (resData: any) => {
    // resData shape: { body, subject, structuredComponents: { IMAGE: [], TABLE: [] }, render_mode }
    const { body, structuredComponents, render_mode } = resData || {
      body: "",
      structuredComponents: { IMAGE: [], TABLE: [] },
      render_mode: "standard",
    };
    const previewSignatureHtml = resData?.signature_html || "";
    setSignatureHtml(previewSignatureHtml);

    const {
      convertFromHTML,
      ContentState,
      EditorState,
      AtomicBlockUtils,
      SelectionState,
    } = require("draft-js");

    let contentState;
    const rawBody = typeof body === "string" ? body : "";
    const isHtmlLike =
      render_mode === "advanced" ||
      render_mode === "word" ||
      render_mode === "html" ||
      /<\/?[a-z][\s\S]*>/i.test(rawBody) ||
      rawBody.trim().startsWith("<!doctype html") ||
      rawBody.trim().startsWith("<html");


    const normalizedBody = injectSignatureHtml(rawBody, previewSignatureHtml);

    if (isHtmlLike) {
      setTemplateRenderMode("html");
      setHtmlPreview(normalizedBody);
      dispatch(setEditorContent(normalizedBody));
      contentState = ContentState.createFromText("");
    } else if (render_mode === "yaml") {
      setTemplateRenderMode("yaml");
      setHtmlPreview("");
      contentState = ContentState.createFromText(normalizedBody);
    } else {
      setTemplateRenderMode("standard");
      setHtmlPreview("");
      // 2. Load as plain text to preserve structure (newlines, spaces) for standard templates
      contentState = ContentState.createFromText(normalizedBody);
    }

    let currentEditorState = EditorState.createWithContent(contentState);

    // 3. Scan and Replace Placeholders (only if advanced rendering is active)
    if (render_mode === "advanced") {
      const blockMap = currentEditorState.getCurrentContent().getBlockMap();
      const blocks = blockMap.toArray();

      for (let i = blocks.length - 1; i >= 0; i--) {
        const block = blocks[i];
        const text = block.getText().trim();
        const match = text.match(
          /\[STRUCTURED_COMPONENT:(IMAGE|TABLE):(\d+)\]/,
        );

        if (match) {
          const type = match[1];
          const index = parseInt(match[2]);
          const data = structuredComponents?.[type]?.[index];

          if (data) {
            const content = currentEditorState.getCurrentContent();
            const contentWithEntity = content.createEntity(
              type,
              "IMMUTABLE",
              data,
            );
            const entityKey = contentWithEntity.getLastCreatedEntityKey();

            const selection = SelectionState.createEmpty(block.getKey()).merge({
              anchorOffset: 0,
              focusOffset: block.getText().length,
            });

            currentEditorState = EditorState.forceSelection(
              currentEditorState,
              selection,
            );
            currentEditorState = AtomicBlockUtils.insertAtomicBlock(
              currentEditorState,
              entityKey,
              " ",
            );
          }
        }
      }
    }

    // 4. Update local state
    setEditorState(currentEditorState);
    dispatch(setEditorContent(normalizedBody));
    dispatch(setStructuredComponents(structuredComponents));
  };

  console.log(editorState, 'frfeqwee2342')

  // 🔹 fetch real template from backend
  const fetchMailTemplate = async () => {

    try {

      const applicationNumber = form.getFieldValue("applicationId")?.trimEnd();
      const email = form.getFieldValue("to")?.trimEnd() || "";
      const contact = form.getFieldValue("contact")?.trimEnd() || "";
      const sender = form.getFieldValue("from")?.trimEnd() || "";
      const aoCode = form.getFieldValue("aoCode")?.trimEnd() || "";
      const template = form.getFieldValue("template")?.trimEnd() || "";
      const date = form.getFieldValue("date");
      const dateString = date ? date.format("YYYY-MM-DD") : "";

      if (!applicationNumber) {
        messageApi.error("Please enter Application Number");
        return;
      }
      setLoading(true);

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/mail/generate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            application_number: applicationNumber,
            template_name: template,
            ao_code: aoCode,
            email,
            contact,
            sender,
            date: dateString,
          }),
        },
      );

      const data = await res.json();
      if (!res.ok) {
        const detailStr = data.detail || "Failed to generate mail";
        if (detailStr.includes("Missing required fields:")) {
          const [mainStr, fieldsStr] = detailStr.split("Missing required fields:");
          const fields = fieldsStr.split(",").map((f: string) => f.trim()).filter(Boolean);
          
          notificationApi.error({
            message: "Action Required",
            placement: "top",
            description: (
              <div>
                <div style={{ marginBottom: 8 }}>{mainStr.trim()} Missing required fields:</div>
                <ul style={{ paddingLeft: 20, margin: 0, listStyleType: "disc" }}>
                  {fields.map((f: string, i: number) => <li key={i}>{f}</li>)}
                </ul>
              </div>
            ),
            duration: 0,
          });
        } else {
          messageApi.error(detailStr);
        }
        return;
      }


      // ✅ load into editor + subject
      setTemplateInEditor(data);

      form.setFieldsValue({
        subject: data.subject,
        to: email,
      });
    } catch (error) {
      console.error("Error fetching mail template:", error);
      messageApi.error(String(error));
    }
    finally {
      setLoading(false);
    }
  };

  const handleStyleClick = (style: string) => {
    setEditorState(RichUtils.toggleInlineStyle(editorState, style));
  };

  const handleBlockClick = (block: string) => {
    setEditorState(RichUtils.toggleBlockType(editorState, block));
  };

  const handleUploadChange = ({ fileList }: { fileList: UploadFile[] }) => {
    setFileList(fileList);
  };

  const currentStyle: DraftInlineStyle = editorState.getCurrentInlineStyle();
  const blockType = RichUtils.getCurrentBlockType(editorState);

  const handleSendVia = async (service: string) => {
    const applicationNumber = Number(form.getFieldValue("applicationId")); // ✅ define outside try/catch
    const recipientEmail = form.getFieldValue("to") || "dummy@example.com";

    if (!applicationNumber) {
      messageApi.error("Please enter Application Number before sending.");
      return;
    }

    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // ✅ Removed if (task) so both logs always run
      await addLog(
        String(applicationNumber),
        "success",
        service,
        `Message sent via ${service} to ${recipientEmail}`,
      );

      await addCommunicationLog(
        String(applicationNumber),
        service,
        recipientEmail,
        `Message sent via ${service}`,
        "success",
      );

      messageApi.error(
        `✅ Dummy ${service} sent successfully to ${recipientEmail} (not real)`,
      );
    } catch (error) {
      console.error("❌ Error in handleSendVia:", error);

      // ✅ Log failure to BOTH logs even if request fails
      await addLog(
        String(applicationNumber),
        "error",
        service,
        `Failed to send via ${service}`,
      );

      await addCommunicationLog(
        String(applicationNumber),
        service,
        recipientEmail,
        `Failed to send via ${service}`,
        "error",
      );

      messageApi.error(`❌ Error sending via ${service}`);
    }
  };

  const handleSendEmail = async () => {
    const applicationId = form.getFieldValue("applicationId");
    const recipientEmail = form.getFieldValue("to");
    const subject = form.getFieldValue("subject");
    const templateName = form.getFieldValue("template");
    const sender = form.getFieldValue("from");
    const date = form.getFieldValue("date");
    const dateString = date ? date.format("YYYY-MM-DD") : "";

    const iframeDoc =
      htmlEditorRef.current?.contentDocument ||
      htmlEditorRef.current?.contentWindow?.document;
    // Preserve HTML templates as HTML so formatting is not lost.
    const content =
      templateRenderMode === "html"
        ? iframeDoc?.documentElement?.outerHTML || htmlPreview
        : editorState.getCurrentContent().getPlainText();

    setEmailLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/mail/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          application_number: String(applicationId),
          type: "email",
          status: "sent",
          template_name: templateName,
          subject: subject,
          content: content,
          recipient: recipientEmail,
          sender: sender,
          date: dateString,
          meta_data: {
            sent_at: new Date().toISOString(),
          },
        }),
      });

      if (!res.ok) throw new Error("Failed to save communication");

      messageApi.success("Email sent and recorded successfully");

      // Clear fields but keep Application ID
      const appId = form.getFieldValue("applicationId");
      form.resetFields();
      form.setFieldsValue({ applicationId: appId });

      // Clear editor and file list
      setEditorState(EditorState.createEmpty());
      dispatch(setEditorContent(""));
      setFileList([]);
      setTemplateRenderMode("standard");
      setHtmlPreview("");
      setSignatureHtml("");
    } catch (err) {
      console.error("Error sending email:", err);
      messageApi.error("Failed to send/record email");
    } finally {
      setEmailLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    const applicationId = form.getFieldValue("applicationId");
    const subject = form.getFieldValue("subject");
    const templateName = form.getFieldValue("template");
    const aoCode = form.getFieldValue("aoCode") || "";
    const date = form.getFieldValue("date");
    const dateString = date ? date.format("YYYY-MM-DD") : "";

    const getEditableHtml = () => {
      const iframeDoc =
        htmlEditorRef.current?.contentDocument ||
        htmlEditorRef.current?.contentWindow?.document;
      if (templateRenderMode === "html" && iframeDoc?.documentElement) {
        return iframeDoc.documentElement.outerHTML;
      }
      return htmlPreview || editorContent || "";
    };

    const reconstructedText =
      templateRenderMode === "html"
        ? getEditableHtml()
        : (() => {
          const contentState = editorState.getCurrentContent();
          const blocks = contentState.getBlockMap();
          let textOut = "";

          blocks.forEach((block: any) => {
            const text = block.getText();
            if (block.getType() === "atomic") {
              const entityKey = block.getEntityAt(0);
              if (entityKey) {
                const entity = contentState.getEntity(entityKey);
                const entityData = entity.getData();
                const entityType = entity.getType();

                const type = entityType.toUpperCase();
                const components = structuredComponents?.[type] || [];
                const index = components.findIndex((c: any) =>
                  type === "IMAGE"
                    ? c.src === entityData.src
                    : c.title === entityData.title,
                );

                if (index !== -1) {
                  textOut += `[STRUCTURED_COMPONENT:${type}:${index}]\n`;
                }
              }
            } else {
              textOut += text + "\n";
            }
          });

          return textOut;
        })();

    const finalReconstructedText = injectSignatureHtml(
      reconstructedText,
      signatureHtml,
    );
    const templateNameVal = templatesType?.find((t: any) => templateName.includes(t.service_code));

    try {
      setPdfLoading(true);
      await CommunicationApi.downloadPdf({
        application_number: String(applicationId),
        template_name: templateName,
        ao_code: aoCode,
        subject: subject,
        content: finalReconstructedText,
        structuredComponents: structuredComponents,
        date: dateString,
      }, initialData, templateNameVal);
      messageApi.success("PDF Downloaded successfully");
    } catch (err) {
      console.error("Error downloading PDF:", err);
      messageApi.error("Failed to download PDF");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleDownloadHtml = () => {
    const applicationId = form.getFieldValue("applicationId");
    const iframeDoc =
      htmlEditorRef.current?.contentDocument ||
      htmlEditorRef.current?.contentWindow?.document;
    const htmlContent =
      templateRenderMode === "html" && iframeDoc?.documentElement
        ? iframeDoc.documentElement.outerHTML
        : htmlPreview || editorContent || "";
    const blob = new Blob([htmlContent], { type: "text/html;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `communication_${applicationId || "draft"}.html`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleDownloadWord = async () => {
    const applicationId = form.getFieldValue("applicationId");
    const templateName = form.getFieldValue("template");
    const templateNameVal: any = templatesType?.find((t: any) => templateName.includes(t.service_code));

    const getEditableHtml = () => {
      const iframeDoc =
        htmlEditorRef.current?.contentDocument ||
        htmlEditorRef.current?.contentWindow?.document;
      if (templateRenderMode === "html" && iframeDoc?.documentElement) {
        return iframeDoc.documentElement.outerHTML;
      }
      return htmlPreview || editorContent || "";
    };

    const reconstructedText =
      templateRenderMode === "html"
        ? getEditableHtml()
        : (() => {
          const contentState = editorState.getCurrentContent();
          const blocks = contentState.getBlockMap();
          let textOut = "";

          blocks.forEach((block: any) => {
            const text = block.getText();
            if (block.getType() === "atomic") {
              const entityKey = block.getEntityAt(0);
              if (entityKey) {
                const entity = contentState.getEntity(entityKey);
                const entityData = entity.getData();
                const entityType = entity.getType();

                const type = entityType.toUpperCase();
                const components = structuredComponents?.[type] || [];
                const index = components.findIndex((c: any) =>
                  type === "IMAGE"
                    ? c.src === entityData.src
                    : c.title === entityData.title,
                );

                if (index !== -1) {
                  textOut += `[STRUCTURED_COMPONENT:${type}:${index}]\n`;
                }
              }
            } else {
              textOut += text + "\n";
            }
          });

          return textOut;
        })();

    const finalReconstructedText = injectSignatureHtml(
      reconstructedText,
      signatureHtml,
    );

    try {
      setWordLoading(true);
      let htmlContent = "";
      if (templateRenderMode === "html") {
        htmlContent = finalReconstructedText;
      } else {
        htmlContent = `<!DOCTYPE html>
          <html>
          <head>
            <meta charset="UTF-8">
            <style>
              body { font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.6; }
              table { border-collapse: collapse; width: 100%; }
              th, td { border: 1px solid #999; padding: 3px 5px; }
              table p { margin: 0; }
            </style>
          </head>
          <body>${finalReconstructedText.replace(/\n/g, "<br/>")}</body>
          </html>`;
      }

      const blob = await htmlDocx.asBlob(htmlContent);
      saveAs(blob as unknown as Blob, `${initialData?.loan_account_number}-${initialData?.borrower_name}-${templateNameVal?.template_type}.docx`);
      messageApi.success("Word Document Downloaded successfully");
    } catch (err) {
      console.error("Error downloading Word document:", err);
      messageApi.error("Failed to download Word document");
    } finally {
      setWordLoading(false);
    }
  };

  const handleHtmlEditorLoad = () => {
    const iframe = htmlEditorRef.current;
    const doc = iframe?.contentDocument || iframe?.contentWindow?.document;
    if (!doc?.body) return;

    doc.designMode = "on";
    doc.body.contentEditable = "true";
    doc.body.style.outline = "none";
    doc.body.style.minHeight = "100%";

    const ensureAddressStyles = () => {
      const existing = doc.getElementById("communication-address-style");
      if (existing) return;

      const style = doc.createElement("style");
      style.id = "communication-address-style";
      style.textContent = `
        .address-block {
          display: inline-block !important;
          white-space: normal !important;
          line-height: 1.55 !important;
          margin: 4px 0 !important;
        }

        .address-block .address-line {
          display: block !important;
          margin: 0 0 4px 0 !important;
          line-height: 1.55 !important;
        }

        .address-block .address-line:last-child {
          margin-bottom: 0 !important;
        }
      `;
      doc.head?.appendChild(style);
    };

    ensureAddressStyles();

    const sync = () => {
      if (doc.documentElement) {
        dispatch(setEditorContent(doc.documentElement.outerHTML));
      }
    };

    doc.body.addEventListener("input", sync);
    doc.body.addEventListener("keyup", sync);
    doc.body.addEventListener("paste", () => setTimeout(sync, 0));
    sync();
  };

  return (
    <>
      {contextHolder}
      {notificationContextHolder}

      <div className="text-gray-800 mt-0  shadow-md rounded-lg bg-white">
        <Form
          form={form}
          layout="vertical"
          onFinish={() => fetchMailTemplate()}
          scrollToFirstError={{ behavior: "smooth", block: "nearest" }}
        >
          <div className="grid grid-cols-12 gap-6">
            {/* Left side */}
            <div className="col-span-12 md:col-span-3 flex flex-col justify-between border rounded-lg border-gray-200 bg-[#f5f5f5] md:sticky md:top-5 md:h-[80vh] md:max-h-[80vh]">
              {/* Scrollable fields wrapper */}
              <div className="flex-1 overflow-y-auto p-5 space-y-5">
                <Form.Item
                  label="Application ID"
                  name="applicationId"
                  rules={[
                    { required: true, message: "Please enter Application ID" },
                  ]}
                >
                  <Input readOnly className="cursor-not-allowed" placeholder="Enter Application ID" />
                </Form.Item>

                <Form.Item
                  label="Recipient Email"
                  name="to"
                  rules={[
                    { required: true, message: "Please enter recipient email" },
                    { type: "email", message: "Please enter a valid email" },
                  ]}
                  getValueFromEvent={(e) => e.target.value.replace(/^\s+/, "")}
                >
                  <Input placeholder="Enter recipient email" />
                </Form.Item>

                <Form.Item
                  label="Recipient Contact"
                  name="contact"
                  rules={[
                    { required: true, message: "Please enter recipient contact" },
                  ]}
                >
                  <Input placeholder="Enter recipient contact number" />
                </Form.Item>

                <Form.Item
                  label="Select Template"
                  name="template"
                  rules={[
                    { required: true, message: "Please select a template" },
                  ]}
                >
                  <Select placeholder="Choose a template"
                    onOpenChange={(open) => handleDropdownOpenChange(open, 'template')}
                    popupRender={(menu) => (
                      clientSelectLoading?.template ? (
                        <div className="p-4 flex justify-center items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                          <span className="ml-2 text-gray-600">Loading...</span>
                        </div>
                      ) : menu
                    )}>
                    {templatesType.map((template: any) => (
                      <Select.Option key={template.id} value={template?.template_code}>
                        <div className="flex items-center gap-2">
                          <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                            {template?.template_code}
                          </span>
                          <span>{template?.template_type}</span>
                        </div>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  name="aoCode"
                  label="Select AO"
                  rules={[{ required: true, message: "Please select an AO" }]}
                >
                  <Select
                    placeholder="Select AO"
                    className="h-[40px] custom-select-height"
                    showSearch
                    allowClear
                    onOpenChange={(open) => handleDropdownOpenChange(open, 'aoCode')}
                    notFoundContent={
                      clientSelectLoading?.aoCode ? (
                        <div className="p-4 flex justify-center items-center">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                          <span className="ml-2 text-gray-600">Loading...</span>
                        </div>
                      ) : (
                        "No data"
                      )
                    }
                  >
                    {aoData?.map((ao: any, index: number) => (
                      <Option key={ao?.ao_code} value={ao?.ao_code}>
                        <div className="flex items-center gap-2">
                          <span className="bg-blue-100 text-blue-700 px-2 py-[2px] rounded text-xs font-medium">
                            {ao?.ao_code}
                          </span>
                          <span>{ao?.ao_name}</span>
                        </div>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  label="Date"
                  name="date"
                  rules={[{ required: true, message: "Please select a Date" }]}
                >
                  <DatePicker
                    placeholder="Select Date"
                    className="w-full h-[40px]"
                    format="DD/MM/YYYY"
                  />
                </Form.Item>
              </div>

              {/* 🔹 Start Draft Button */}
              <div className="p-5 pt-3 border-t border-gray-200 bg-[#f5f5f5] rounded-b-lg">
                <Button
                  type="primary"
                  htmlType="submit"
                  block
                  loading={loading}
                >
                  Start Draft
                </Button>
              </div>
            </div>

            {/* Right side */}
            <div className="col-span-12 md:col-span-9 flex flex-col md:sticky md:top-5 md:h-[80vh] min-h-0">
              {/* Header */}
              <div className="flex flex-col gap-4 flex-grow min-h-0">
                <div className="flex flex-col gap-1 flex-shrink-0">
                  <div className="flex justify-between items-center gap-2">
                    <label className="font-semibold text-gray-700">
                      Subject / Title
                    </label>

                  </div>
                  <Form.Item name="subject" noStyle>
                    <Input
                      placeholder="Subject"
                      className="!rounded-md border-gray-300 focus:!border-blue-500 transition"
                    />
                  </Form.Item>
                </div>

                {/* Editor Container */}
                <div className="border border-gray-200 rounded-lg overflow-hidden mt-2 flex flex-col flex-grow min-h-0">
                  <>
                    {/* Toolbar & Actions Row */}
                    <div className="flex flex-wrap justify-between items-center bg-gray-50 border-b border-gray-200 p-2 gap-2 flex-shrink-0">
                      {/* Toolbar Icons */}

                      <div>
                        <p className="font-semibold">Notice</p>
                      </div>

                      {/* Right Actions: Attach & Send */}
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={handleDownloadPDF}
                          disabled={htmlPreview == "" || pdfLoading}
                          className={`${(htmlPreview == "" || pdfLoading) ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors`}
                        >
                          {pdfLoading ? <FaSpinner className="animate-spin" /> : <FaFilePdf />}
                          <span>{pdfLoading ? "Downloading..." : "Download PDF"}</span>
                        </button>

                        <button
                          type="button"
                          onClick={handleDownloadWord}
                          disabled={htmlPreview == "" || wordLoading}
                          className={`${(htmlPreview == "" || wordLoading) ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} flex items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors`}
                        >
                          {wordLoading ? <FaSpinner className="animate-spin" /> : <FaFileWord />}
                          <span>{wordLoading ? "Downloading..." : "Download DOCX"}</span>
                        </button>

                        {/* <Dropdown
                          menu={{
                            items: [
                              {
                                key: "send",
                                label: "Send Email",
                                disabled: signatureHtml == "",
                                icon: <FaPaperPlane />,
                                onClick: handleSendEmail,
                              },
                              {
                                key: "save_pdf",
                                label: "Download PDF",
                                disabled: signatureHtml == "",
                                // icon: <FaFilePdf />,
                                onClick: handleDownloadPDF,
                              },
                              // {
                              //   key: "save_html",
                              //   label: "Download HTML",
                              //   disabled: signatureHtml == "",
                              //   onClick: handleDownloadHtml,
                              // },
                              {
                                key: "save_word",
                                label: "Download Word",
                                disabled: signatureHtml == "",
                                onClick: handleDownloadWord,
                              }
                            ],
                          }}
                          trigger={["click"]}
                        >
                          <Button shape="circle" icon={<LuSend />} />
                        </Dropdown> */}
                      </div>
                    </div>

                    {templateRenderMode === "html" ? (
                      <div className="bg-white p-4 flex-grow min-h-0 flex flex-col">
                        <iframe
                          ref={htmlEditorRef}
                          title="Template editor"
                          className="w-full flex-grow border-0 rounded-md bg-white"
                          srcDoc={htmlPreview}
                          onLoad={handleHtmlEditorLoad}
                        />
                      </div>
                    ) : (
                      <div
                        className="p-5 flex-grow overflow-y-auto bg-white cursor-text min-h-0"
                        onClick={focusEditor}
                      >
                        {mounted ? (
                          <Editor
                            editorRef={editorRef}
                            editorState={editorState}
                            onChange={setEditorState}
                            blockRendererFn={mediaBlockRenderer}
                            placeholder="Type or select a template..."
                          />
                        ) : (
                          <div className="text-gray-400">Loading editor...</div>
                        )}
                      </div>
                    )}
                  </>
                </div>
              </div>
            </div>
          </div>
          {/* Removed bottom action bar as requested by UI design */}
        </Form>

        {/* Modal */}
        <Modal
          title="Send via"
          open={isModalOpen}
          onCancel={() => setIsModalOpen(false)}
          footer={null}
        >
          <div className="grid grid-cols-4 sm:grid-cols-3 gap-8 text-center">
            {[
              {
                icon: FaWhatsapp,
                label: "WhatsApp",
                color: "text-green-600",
                bg: "bg-green-100",
                service: "whatsapp",
              },
              {
                icon: FaTelegram,
                label: "Telegram",
                color: "text-sky-500",
                bg: "bg-sky-100",
                service: "telegram",
              },
              {
                icon: FaSlack,
                label: "Slack",
                color: "text-pink-600",
                bg: "bg-pink-100",
                service: "slack",
              },
              {
                icon: FaDiscord,
                label: "Discord",
                color: "text-indigo-600",
                bg: "bg-indigo-100",
                service: "discord",
              },
              {
                icon: IoIosMail,
                label: "Email",
                color: "text-blue-500",
                bg: "bg-blue-100",
                service: "email",
              },
            ].map((item, idx) => (
              <button
                key={idx}
                onClick={() => handleSendVia(item.service)}
                className="flex flex-col items-center gap-2 p-2 rounded-lg hover:scale-110 transition-transform"
              >
                <div
                  className={`p-3 rounded-lg ${item.bg} flex items-center justify-center`}
                >
                  <item.icon className={`text-3xl ${item.color}`} />
                </div>
                <span className="text-xs font-medium">{item.label}</span>
              </button>
            ))}
          </div>
        </Modal>
      </div>
    </>
  );
}