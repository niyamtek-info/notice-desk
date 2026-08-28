"use client";

import React, { useEffect, useState } from "react";
import {
  Form,
  Input,
  DatePicker,
  Card,
  Typography,
  Divider,
  Button,
  Segmented,
  ConfigProvider,
  message,
  Select,
  Modal,
} from "antd";
import { useAppNoContext } from "@/context/AppNoContext";
import {
  DownloadOutlined,
  SaveOutlined,
  CloseOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";
import * as XLSX from "xlsx";
import { ReportApi } from "@/src/services/ReportApi";
import dayjs, { Dayjs } from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";
import { IoMdRefresh } from "react-icons/io";
import { BankApi } from "@/src/services/BankApi";
import { IoDocumentTextOutline } from "react-icons/io5";
import TiptapEditor from "@/components/form/TipEditor";

const { Text } = Typography;
const { TextArea } = Input;

interface LoanApplicationProps {
  applicationId: string;
  recordId: string;
  setUpdate: any;
  initialData: any;
  activeItem: string;
  triggerReport: any;
}

const ReportsContent: React.FC<LoanApplicationProps> = ({
  applicationId,
  recordId,
  setUpdate,
  initialData,
  activeItem,
  triggerReport,
}) => {
  const { applicationNumber } = useAppNoContext();
  const [form] = Form.useForm();
  const [isChanged, setIsChanged] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [generatingReport, setGeneratingReport] = React.useState(false);
  const [showGenerateButton, setShowGenerateButton] = useState(0);
  const [trigger, setTrigger] = useState<number>(0);
  const [messageApi, contextHolder] = message.useMessage();
  const [banks, setBanks] = useState<any[]>([]);
  const [confirmVisible, setConfirmVisible] = useState<boolean>(false);

  const { Option } = Select;

  const fetchBanks = async () => {
    try {
      // Fetch banks data - replace with actual API call
      const bankData: any = await BankApi.getBankList(); // Using existing method
      setBanks(bankData || []);
    } catch (error) {
      console.error("Failed to fetch banks:", error);
      setBanks([]); // Fallback to empty array
    }
  };

  useEffect(() => {
    fetchBanks();
  }, []);

  useEffect(() => {
    if (!activeItem) return;

    const sectionMap: any = {
      "Loan Details": "loan-details",
      "13.2 Details": "13.2-details",
      "13.4 Details": "13.4-details",
      "Symbolic Vacation": "symbolic-vacation",
      "CJM Details": "cjm-details",
      "Physical Possession": "physical-possession",
      "Auction Notice": "auction-notice",
      "Auction Portal": "auction-portal",
      "Post Sale Details": "post-sale-details",
      "Sale Certificate": "sale-certificate",
      "Niyamtek Remarks": "niyamtek-remarks",
    };

    const elementId = sectionMap[activeItem];

    // Small delay to ensure element is rendered
    setTimeout(() => {
      const element = document.getElementById(elementId);
      if (element) {
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - 220;

        window.scrollTo({
          top: offsetPosition,
          behavior: "smooth",
        });
      }
    }, 100);
  }, [activeItem]);

  dayjs.extend(customParseFormat);

  const parseToDayjs = (
    date: string | Dayjs | null | undefined,
  ): Dayjs | null => {
    if (!date) return null;

    const formats = [
      "DD/MM/YYYY",
      "DD-MM-YYYY",
      "DD/MM/YY",
      "DD-MM-YY",
      "YYYY/MM/DD",
      "YYYY-MM-DD",
      "YY/MM/DD",
      "YY-MM-DD",
    ];

    // ✅ Case 1: Already Dayjs
    if (dayjs.isDayjs(date)) {
      if (date.isValid()) return date;

      // 🔥 Try to recover invalid Dayjs
      const raw = date.format("DD-MM-YYYY");
      for (const format of formats) {
        const parsed = dayjs(raw, format, true);
        if (parsed.isValid()) return parsed;
      }

      return null;
    }

    // ✅ Case 2: String
    if (typeof date === "string") {
      if (date.includes("T")) {
        const parsed = dayjs(date);
        return parsed.isValid() ? parsed : null;
      }

      for (const format of formats) {
        const parsed = dayjs(date, format, true);
        if (parsed.isValid()) return parsed;
      }
    }

    return null;
  };

  useEffect(() => {
    if (applicationNumber) {
      fetchReportData();
    }
  }, [applicationNumber, trigger, triggerReport]);

  const fetchReportData = async () => {
    try {
      const data: any = await ReportApi.getMaster(applicationNumber);
      if (data) {
        // Determine whether to show generate button based on the SARFAESI report flag.
        setShowGenerateButton(data?.rerun_report || 0);

        // Format dates for Form
        const formattedData = {
          ...data,
          propertyDescription: data?.loan_details?.property_description ?? data?.loan_details?.description_of_schedule_property,

          appNumber: data?.loan_details?.application_number,
          aoName: data?.loan_details?.ao_name,
          borrowerAddress: data?.loan_details?.borrower_address,
          borrowerAddressAlt: data?.loan_details?.borrower_address_alt,
          borrowerName: data?.loan_details?.borrower_name,
          branch: data?.loan_details?.branch,
          chequeBounceCharges: data?.loan_details?.cheque_bounce_charges,
          clientCode: data?.loan_details?.client_code,
          companyName: data?.loan_details?.company_name,
          batchCode: data?.loan_details?.batch_code,
          propertyAddress: data?.loan_details?.property_address,
          trustNumber: data?.loan_details?.trust_number,
          assignmentAgreementDate: data?.loan_details?.assignment_agreement_date
            ? parseToDayjs(data?.loan_details?.assignment_agreement_date)
            : null,
          disbursalAmount: data?.loan_details?.disbursal_amount,
          disbursalDate: data?.loan_details?.disbursal_date
            ? parseToDayjs(data?.loan_details?.disbursal_date)
            : null,
          disbursementType: data?.loan_details?.disbursement_type,
          dpd: data?.loan_details?.dpd,
          fclAsOnDate: data?.loan_details?.fcl_as_on_date ? parseToDayjs(data?.loan_details?.fcl_as_on_date) : null,
          foreClosureCharges: data?.loan_details?.foreclosure_charges,
          futurePrincipal: data?.loan_details?.future_principal,
          instalmentOverdue: data?.loan_details?.instalment_overdue,
          interestOnTermination: data?.loan_details?.interest_on_termination,
          latePaymentPenalty: data?.loan_details?.late_payment_penalty,
          loanAccountNo: data?.loan_details?.loan_account_no,
          loanAgreementDate: data?.loan_details?.loan_agreement_date
            ? parseToDayjs(data?.loan_details?.loan_agreement_date)
            : null,
          loanAmount: data?.loan_details?.loan_amount,
          loanAmountWords: data?.loan_details?.loan_amount_words,
          niyamtekUser: data?.loan_details?.niyamtek_user,
          npaDate: data?.loan_details?.npa_date
            ? parseToDayjs(data?.loan_details?.npa_date)
            : null,
          otherAmount: data?.loan_details?.other_amount,
          principalOutstanding: data?.loan_details?.principal_outstanding,
          region: data?.loan_details?.region,
          state: data?.loan_details?.state,
          totalOutstanding: data?.loan_details?.total_outstanding,
          totalOutstandingWords: data?.loan_details?.total_outstanding_words,
          coBorrowerName1: data?.loan_details?.co_borrower_1_name,
          coBorrowerAddress1: data?.loan_details?.co_borrower_1_address,
          coBorrowerAddressAlt1: data?.loan_details?.co_borrower_1_address_alt,
          coBorrowerName2: data?.loan_details?.co_borrower_2_name,
          coBorrowerAddress2: data?.loan_details?.co_borrower_2_address,
          coBorrowerAddress2Alt: data?.loan_details?.co_borrower_2_address_alt,
          coBorrowerName3: data?.loan_details?.co_borrower_3_name,
          coBorrowerAddress3: data?.loan_details?.co_borrower_3_address,
          coBorrowerAddress3Alt: data?.loan_details?.co_borrower_3_address_alt,
          coBorrowerName4: data?.loan_details?.co_borrower_4_name,
          coBorrowerAddress4: data?.loan_details?.co_borrower_4_address,
          coBorrowerAddress4Alt: data?.loan_details?.co_borrower_4_address_alt,
          coBorrowerName5: data?.loan_details?.co_borrower_5_name,
          coBorrowerAddress5: data?.loan_details?.co_borrower_5_address,
          coBorrowerAddress5Alt: data?.loan_details?.co_borrower_5_address_alt,
          coBorrowerName6: data?.loan_details?.co_borrower_6_name,
          coBorrowerAddress6: data?.loan_details?.co_borrower_6_address,
          guarantorName1: data?.loan_details?.guarantor_1_name,
          guarantorAddress1: data?.loan_details?.guarantor_1_address,
          guarantorName2: data?.loan_details?.guarantor_2_name,
          guarantorAddress2: data?.loan_details?.guarantor_2_address,
          // --- Newly added fields ---
          cifNo: data?.loan_details?.cif_no,
          borrowerEmail: data?.loan_details?.borrower_email,
          borrowerNumber: data?.loan_details?.borrower_number,
          borrowerRange: data?.loan_details?.borrower_range,
          coBorrowerEmail: data?.loan_details?.co_borrower_email,
          coBorrowerNumber: data?.loan_details?.co_borrower_number,
          coBorrowerRange: data?.loan_details?.co_borrower_range,
          reportSource: data?.loan_details?.report_source,
          hasDocument: data?.loan_details?.has_document,
          pos: data?.loan_details?.pos,
          sarfaesiCategory: data?.loan_details?.sarfaesi_category,
          caseStatus: data?.loan_details?.case_status,
          sanctionDate: data?.loan_details?.sanction_date
            ? parseToDayjs(data?.loan_details?.sanction_date)
            : null,
          sanctionDateWords: data?.loan_details?.sanction_date_words,
          sanctionAmount: data?.loan_details?.sanction_amount,
          pendingEmi: data?.loan_details?.pending_emi,
          interestForTheMonth: data?.loan_details?.interest_for_the_month,
          lrnDate: data?.loan_details?.lrn_date
            ? parseToDayjs(data?.loan_details?.lrn_date)
            : null,
          lrnDateWords: data?.loan_details?.lrn_date_words,
          lrnDispatchDate: data?.loan_details?.lrn_dispatch_date
            ? parseToDayjs(data?.loan_details?.lrn_dispatch_date)
            : null,
          preSarfeasiDate: data?.loan_details?.pre_sarfeasi_date
            ? parseToDayjs(data?.loan_details?.pre_sarfeasi_date)
            : null,
          preSarfeasiDateWords: data?.loan_details?.pre_sarfeasi_date_words,
          preSarfeasiDispatchDate: data?.loan_details?.pre_sarfeasi_dispatch_date
            ? parseToDayjs(data?.loan_details?.pre_sarfeasi_dispatch_date)
            : null,
          mortagerName1: data?.loan_details?.mortager_name_1,
          mortagerAddress1: data?.loan_details?.mortager_address_1,
          mortagerName2: data?.loan_details?.mortager_name_2,
          mortagerAddress2: data?.loan_details?.mortager_address_2,
          collateralPropertyDescription: data?.loan_details?.collateral_property_description,
          modelOfMachinery: data?.loan_details?.model_of_machinery,
          manufacturer: data?.loan_details?.manufacturer,
          categoryOfMachinery: data?.loan_details?.category_of_machinery,
          dealerName: data?.loan_details?.dealer_name,
          typeOfMachine: data?.loan_details?.type_of_machine,
          propertyName: data?.loan_details?.property_name,
          deliveredAddress: data?.["13_2_details"]?.delivered_address,
          deliveryStatus: data?.["13_2_details"]?.delivery_status,
          deliveryStatusDate: data?.["13_2_details"]?.delivery_status_date ? parseToDayjs(data?.["13_2_details"]?.delivery_status_date) : null,
          notice132Amount: data?.["13_2_details"]?.notice_13_2_amount,
          notice132Date: data?.["13_2_details"]?.notice_13_2_date
            ? parseToDayjs(data?.["13_2_details"]?.notice_13_2_date)
            : null,
          noticeDispatchDate: data?.["13_2_details"]?.notice_dispatch_date
            ? parseToDayjs(data?.["13_2_details"]?.notice_dispatch_date)
            : null,
          noticePastingDate: data?.["13_2_details"]?.notice_pasting_date
            ? parseToDayjs(data?.["13_2_details"]?.notice_pasting_date)
            : null,
          publicationDate: data?.["13_2_details"]?.publication_date
            ? parseToDayjs(data?.["13_2_details"]?.publication_date)
            : null,
          publicationEnglish: data?.["13_2_details"]?.publication_english,
          publicationLocal: data?.["13_2_details"]?.publication_local,
          totalAddress: data?.["13_2_details"]?.total_address,
          undeliveredAddress: data?.["13_2_details"]?.undelivered_address,

          symbolicDeliveryStatus:
            data?.["13_4_details"]?.symbolic_delivery_status,
          symbolicDeliveryStatusDate: data?.["13_4_details"]?.symbolic_delivery_status_date ? parseToDayjs(data?.["13_4_details"]?.symbolic_delivery_status_date) : null,
          symbolicDispatchDate: data?.["13_4_details"]?.symbolic_dispatch_date
            ? parseToDayjs(data?.["13_4_details"]?.symbolic_dispatch_date)
            : null,
          symbolicPhoto: data?.["13_4_details"]?.symbolic_photo,
          symbolicPossessionDate: data?.["13_4_details"]
            ?.symbolic_possession_date
            ? parseToDayjs(data?.["13_4_details"]?.symbolic_possession_date)
            : null,
          symbolicPubEnglish: data?.["13_4_details"]?.symbolic_pub_english,
          symbolicPubLocal: data?.["13_4_details"]?.symbolic_pub_local,
          symbolicPublicationDate: data?.["13_4_details"]
            ?.symbolic_publication_date
            ? parseToDayjs(data?.["13_4_details"]?.symbolic_publication_date)
            : null,
          maturedDate13_4: data?.["13_4_details"]?.matured_date_13_4
            ? parseToDayjs(data?.["13_4_details"]?.matured_date_13_4)
            : null,
          symbolicVacationNoticeMoveable: data?.symbolic_vacation_notice_details?.vacation_notice_moveable,
          symbolicVacationNoticeImmoveable: data?.symbolic_vacation_notice_details?.vacation_notice_immoveable,
          cjmFilingDate: (data?.cjm_details?.cjm_filing_date || data?.cjm_details?.cjm_date) ? parseToDayjs(data?.cjm_details?.cjm_filing_date || data?.cjm_details?.cjm_date) : null,
          courtName: data?.cjm_details?.court_name,
          caseNumber: data?.cjm_details?.case_number,
          crmPLDate: data?.cjm_details?.crm_pl_date ? parseToDayjs(data?.cjm_details?.crm_pl_date) : null,
          crmPLNo: data?.cjm_details?.crm_pl_no,
          nextHearingDate: data?.cjm_details?.next_hearing_date ? parseToDayjs(data?.cjm_details?.next_hearing_date) : null,
          ovDate: data?.cjm_details?.ov_date ? parseToDayjs(data?.cjm_details?.ov_date) : null,
          orderDate: data?.cjm_details?.order_date ? parseToDayjs(data?.cjm_details?.order_date) : null,
          courtAOName: data?.cjm_details?.court_ao_name,
          advocateDetails: data?.cjm_details?.advocate_details,
          advComName: data?.cjm_details?.adv_com_name,
          inventoryStatus: data?.cjm_details?.inventory_status,

          physicalPossessionDate: data?.physical_possession_details?.physical_possession_date ? parseToDayjs(data?.physical_possession_details?.physical_possession_date) : null,
          physicalDispatchDate: data?.physical_possession_details?.physical_dispatch_date ? parseToDayjs(data?.physical_possession_details?.physical_dispatch_date) : null,
          physicalDeliveryStatus: data?.physical_possession_details?.physical_delivery_status,
          physicalDeliveryStatusDate: data?.physical_possession_details?.physical_delivery_status_date ? parseToDayjs(data?.physical_possession_details?.physical_delivery_status_date) : null,
          physicalPhoto: data?.physical_possession_details?.physical_photo,
          physicalPublicationDate: data?.physical_possession_details?.physical_publication_date ? parseToDayjs(data?.physical_possession_details?.physical_publication_date) : null,
          physicalPubEnglish: data?.physical_possession_details?.physical_pub_english,
          physicalPubLocal: data?.physical_possession_details?.physical_pub_local,
          physicalPossessionVacationNoticeMoveable: data?.physical_possession_details?.vacation_notice_moveable,
          physicalPossessionVacationNoticeImmoveable: data?.physical_possession_details?.vacation_notice_immoveable,

          auctionNoticeDate: data?.auction_notice_details?.auction_notice_date ? parseToDayjs(data?.auction_notice_details?.auction_notice_date) : null,
          auctionDate: data?.auction_notice_details?.auction_date ? parseToDayjs(data?.auction_notice_details?.auction_date) : null,
          auctionPublicationDate: data?.auction_notice_details?.auction_publication_date ? parseToDayjs(data?.auction_notice_details?.auction_publication_date) : null,
          auctionPubEnglish: data?.auction_notice_details?.auction_pub_english,
          auctionPubLocal: data?.auction_notice_details?.auction_pub_local,
          reservePrice: data?.auction_notice_details?.reserve_price,

          auctionDatePortal: data?.auction_portal_details?.auction_date ? parseToDayjs(data?.auction_portal_details?.auction_date) : null,
          reservePricePortal: data?.auction_portal_details?.reserve_price,
          soldPricePortal: data?.auction_portal_details?.sold_price,
          auctionStatusPortal: data?.auction_portal_details?.auction_status,
          inspectionStartPortal: data?.auction_portal_details?.inspection_start ? parseToDayjs(data?.auction_portal_details?.inspection_start) : null,
          inspectionEndPortal: data?.auction_portal_details?.inspection_end ? parseToDayjs(data?.auction_portal_details?.inspection_end) : null,
          emdLastDatePortal: data?.auction_portal_details?.emd_last_date ? parseToDayjs(data?.auction_portal_details?.emd_last_date) : null,
          auctionStartPortal: data?.auction_portal_details?.auction_start ? parseToDayjs(data?.auction_portal_details?.auction_start) : null,
          auctionEndPortal: data?.auction_portal_details?.auction_end ? parseToDayjs(data?.auction_portal_details?.auction_end) : null,
          bidExtensionTimePortal: data?.auction_portal_details?.bid_extension_time,
          totalExtensionsPortal: data?.auction_portal_details?.total_extensions,
          outstandingAmountPortal: data?.auction_portal_details?.outstanding_amount,
          emdAmountPortal: data?.auction_portal_details?.emd_amount,
          bidIncrementPortal: data?.auction_portal_details?.bid_increment,
          totalBidCountPortal: data?.auction_portal_details?.total_bid_count,
          authorisedOfficerPortal: data?.auction_portal_details?.authorised_officer,

          postSaleNotice: data?.post_sale_details?.post_sale_notice,
          soldPrice: data?.post_sale_details?.sold_price,
          soldRegDate: data?.post_sale_details?.sold_reg_date ? parseToDayjs(data?.post_sale_details?.sold_reg_date) : null,

          saleConfirmationDate: data?.sale_certificate_details?.sale_confirmation_date ? parseToDayjs(data?.sale_certificate_details?.sale_confirmation_date) : null,
          saleCertificateDate: data?.sale_certificate_details?.sale_certificate_date ? parseToDayjs(data?.sale_certificate_details?.sale_certificate_date) : null,

          availableDocumentsNiyamtek: data?.niyamtek_remarks_details?.available_documents || data?.niyamtek_remarks?.available_documents,
          nonAvailableDocumentsNiyamtek: data?.niyamtek_remarks_details?.non_available_documents || data?.niyamtek_remarks?.non_available_documents,
          discrepancyDocNiyamtek: data?.niyamtek_remarks_details?.discrepancy_doc || data?.niyamtek_remarks?.discrepancy_doc,
          discrepancyReasonNiyamtek: data?.niyamtek_remarks_details?.discrepancy_reason || data?.niyamtek_remarks?.discrepancy_reason,
          nextActionableStageNiyamtek: data?.niyamtek_remarks_details?.next_actionable_stage || data?.niyamtek_remarks?.next_actionable_stage,
          nextStepRecommendedNiyamtek: data?.niyamtek_remarks_details?.next_step_recommended || data?.niyamtek_remarks?.next_step_recommended,
        };
        form.setFieldsValue(formattedData);
      }
    } catch (error: any) {
      messageApi.error(
        error?.response?.data?.detail || "Failed to fetch report data",
      );
    } finally {
    }
  };

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      await ReportApi.generate(applicationNumber);
      messageApi.success("Report generated successfully");
      setTrigger((pre) => pre + 1);
    } catch (error) {
      console.error("Failed to generate report:", error);
      const key = "generate-report-error";
      messageApi.warning({
        key,
        content: (
          <span
            style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}
          >
            Failed to generate report please resolve all "Mismatch" in the
            checklist before generation
            <CloseOutlined
              onClick={() => messageApi.destroy(key)}
              style={{ cursor: "pointer", fontSize: "14px" }}
            />
          </span>
        ),
        duration: 0,
      });
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleSave = async () => {
    console.log("click")
    // try {
    //   await form.validateFields();
    // } catch (info) {
    //   console.log(info, 'info');
    // }

    const values = form.getFieldsValue();
    setLoading(true);
    setConfirmVisible(false);
    try {
      const payload = {
        loan_details: {
          ao_name: values?.aoName,
          borrower_address: values?.borrowerAddress,
          borrower_address_alt: values?.borrowerAddressAlt,
          borrower_name: values?.borrowerName,
          branch: values?.branch,
          cheque_bounce_charges: values?.chequeBounceCharges,
          client_code: values?.clientCode,
          company_name: values?.companyName,
          batch_code: values?.batchCode,
          property_description: values?.propertyDescription,
          property_address: values?.propertyAddress,
          trust_number: values?.trustNumber,
          assignment_agreement_date: values?.assignmentAgreementDate?.format("YYYY-MM-DD") || null,
          disbursal_amount: values?.disbursalAmount,
          disbursal_date: values?.disbursalDate?.format("YYYY-MM-DD") || null,
          disbursement_type: values?.disbursementType,
          dpd: values?.dpd,
          fcl_as_on_date: values?.fclAsOnDate?.format("YYYY-MM-DD") || null,
          foreclosure_charges: values?.foreClosureCharges,
          future_principal: values?.futurePrincipal,
          instalment_overdue: values?.instalmentOverdue,
          interest_on_termination: values?.interestOnTermination,
          late_payment_penalty: values?.latePaymentPenalty,
          loan_account_no: values?.loanAccountNo,
          loan_agreement_date: values?.loanAgreementDate?.format("YYYY-MM-DD") || null,
          loan_amount: values?.loanAmount,
          loan_amount_words: values?.loanAmountWords,
          niyamtek_user: values?.niyamtekUser,
          npa_date: values?.npaDate?.format("YYYY-MM-DD") || null,
          other_amount: values?.otherAmount,
          principal_outstanding: values?.principalOutstanding,
          region: values?.region,
          state: values?.state,
          total_outstanding: values?.totalOutstanding,
          total_outstanding_words: values?.totalOutstandingWords,
          co_borrower_1_name: values?.coBorrowerName1,
          co_borrower_1_address: values?.coBorrowerAddress1,
          co_borrower_1_address_alt: values?.coBorrowerAddressAlt1,
          co_borrower_2_name: values?.coBorrowerName2,
          co_borrower_2_address: values?.coBorrowerAddress2,
          co_borrower_2_address_alt: values?.coBorrowerAddress2Alt,
          co_borrower_3_name: values?.coBorrowerName3,
          co_borrower_3_address: values?.coBorrowerAddress3,
          co_borrower_3_address_alt: values?.coBorrowerAddress3Alt,
          co_borrower_4_name: values?.coBorrowerName4,
          co_borrower_4_address: values?.coBorrowerAddress4,
          co_borrower_4_address_alt: values?.coBorrowerAddress4Alt,
          co_borrower_5_name: values?.coBorrowerName5,
          co_borrower_5_address: values?.coBorrowerAddress5,
          co_borrower_5_address_alt: values?.coBorrowerAddress5Alt,
          co_borrower_6_name: values?.coBorrowerName6,
          co_borrower_6_address: values?.coBorrowerAddress6,
          guarantor_1_name: values?.guarantorName1,
          guarantor_1_address: values?.guarantorAddress1,
          guarantor_2_name: values?.guarantorName2,
          guarantor_2_address: values?.guarantorAddress2,
          // --- Newly added fields ---
          cif_no: values?.cifNo,
          borrower_email: values?.borrowerEmail,
          borrower_number: values?.borrowerNumber,
          borrower_range: values?.borrowerRange,
          co_borrower_email: values?.coBorrowerEmail,
          co_borrower_number: values?.coBorrowerNumber,
          co_borrower_range: values?.coBorrowerRange,
          report_source: values?.reportSource,
          has_document: values?.hasDocument,
          pos: values?.pos,
          sarfaesi_category: values?.sarfaesiCategory,
          case_status: values?.caseStatus,
          sanction_date: values?.sanctionDate?.format("YYYY-MM-DD") || null,
          sanction_date_words: values?.sanctionDateWords,
          sanction_amount: values?.sanctionAmount,
          pending_emi: values?.pendingEmi,
          interest_for_the_month: values?.interestForTheMonth,
          lrn_date: values?.lrnDate?.format("YYYY-MM-DD") || null,
          lrn_date_words: values?.lrnDateWords,
          lrn_dispatch_date: values?.lrnDispatchDate?.format("YYYY-MM-DD") || null,
          pre_sarfeasi_date: values?.preSarfeasiDate?.format("YYYY-MM-DD") || null,
          pre_sarfeasi_date_words: values?.preSarfeasiDateWords,
          pre_sarfeasi_dispatch_date: values?.preSarfeasiDispatchDate?.format("YYYY-MM-DD") || null,
          mortager_name_1: values?.mortagerName1,
          mortager_address_1: values?.mortagerAddress1,
          mortager_name_2: values?.mortagerName2,
          mortager_address_2: values?.mortagerAddress2,
          collateral_property_description: values?.collateralPropertyDescription,
          model_of_machinery: values?.modelOfMachinery,
          manufacturer: values?.manufacturer,
          category_of_machinery: values?.categoryOfMachinery,
          dealer_name: values?.dealerName,
          type_of_machine: values?.typeOfMachine,
          property_name: values?.propertyName,
        },
        ["13_2_details"]: {
          delivered_address: values?.deliveredAddress,
          delivery_status: values?.deliveryStatus,
          delivery_status_date: values?.deliveryStatusDate?.format("YYYY-MM-DD") || null,
          notice_13_2_amount: values?.notice132Amount,
          notice_13_2_date: values?.notice132Date?.format("YYYY-MM-DD") || null,
          notice_dispatch_date:
            values?.noticeDispatchDate?.format("YYYY-MM-DD") || null,
          notice_pasting_date:
            values?.noticePastingDate?.format("YYYY-MM-DD") || null,
          publication_date_13_2: values?.publicationDate?.format("YYYY-MM-DD") || null,
          publication_english_13_2: values?.publicationEnglish,
          publication_local_13_2: values?.publicationLocal,
          total_address: values?.totalAddress,
          undelivered_address: values?.undeliveredAddress,
        },
        ["13_4_details"]: {
          symbolic_delivery_status_13_4: values?.symbolicDeliveryStatus,
          symbolic_delivery_status_date_13_4: values?.symbolicDeliveryStatusDate?.format("YYYY-MM-DD") || null,
          symbolic_dispatch_date_13_4:
            values?.symbolicDispatchDate?.format("YYYY-MM-DD") || null,
          symbolic_photo_13_4: values?.symbolicPhoto,
          symbolic_possession_date_13_4:
            values?.symbolicPossessionDate?.format("YYYY-MM-DD") || null,
          symbolic_pub_english_13_4: values?.symbolicPubEnglish,
          symbolic_pub_local_13_4: values?.symbolicPubLocal,
          symbolic_publication_date_13_4:
            values?.symbolicPublicationDate?.format("YYYY-MM-DD") || null,
          matured_date_13_4: values?.maturedDate13_4?.format("YYYY-MM-DD") || null,
        },
        symbolic_vacation_notice_details: {
          vacation_notice_moveable: values?.symbolicVacationNoticeMoveable,
          vacation_notice_immoveable: values?.symbolicVacationNoticeImmoveable,
        },
        cjm_details: {
          cjm_filing_date: values?.cjmFilingDate?.format("YYYY-MM-DD") || null,
          court_name: values?.courtName,
          case_number: values?.caseNumber,
          crm_pl_date: values?.crmPLDate?.format("YYYY-MM-DD") || null,
          crm_pl_no: values?.crmPLNo,
          next_hearing_date: values?.nextHearingDate?.format("YYYY-MM-DD") || null,
          ov_date: values?.ovDate?.format("YYYY-MM-DD") || null,
          order_date: values?.orderDate?.format("YYYY-MM-DD") || null,
          court_ao_name: values?.courtAOName,
          advocate_details: values?.advocateDetails,
          adv_com_name: values?.advComName,
          inventory_status: values?.inventoryStatus,
        },
        physical_possession_details: {
          physical_possession_date: values?.physicalPossessionDate?.format("YYYY-MM-DD") || null,
          physical_dispatch_date: values?.physicalDispatchDate?.format("YYYY-MM-DD") || null,
          physical_delivery_status: values?.physicalDeliveryStatus,
          physical_delivery_status_date: values?.physicalDeliveryStatusDate?.format("YYYY-MM-DD") || null,
          physical_photo: values?.physicalPhoto,
          physical_publication_date: values?.physicalPublicationDate?.format("YYYY-MM-DD") || null,
          physical_pub_english: values?.physicalPubEnglish,
          physical_pub_local: values?.physicalPubLocal,
          vacation_notice_moveable: values?.physicalPossessionVacationNoticeMoveable,
          vacation_notice_immoveable: values?.physicalPossessionVacationNoticeImmoveable,
        },

        auction_notice_details: {
          auction_notice_date: values?.auctionNoticeDate?.format("YYYY-MM-DD") || null,
          auction_date: values?.auctionDate?.format("YYYY-MM-DD") || null,
          auction_publication_date: values?.auctionPublicationDate?.format("YYYY-MM-DD") || null,
          auction_pub_english: values?.auctionPubEnglish,
          auction_pub_local: values?.auctionPubLocal,
          reserve_price: values?.reservePrice,
        },

        auction_portal_details: {
          auction_date: values?.auctionDatePortal?.format("YYYY-MM-DD") || null,
          reserve_price: values?.reservePricePortal,
          sold_price: values?.soldPricePortal,
          auction_status: values?.auctionStatusPortal,
          inspection_start: values?.inspectionStartPortal?.format("YYYY-MM-DD") || null,
          inspection_end: values?.inspectionEndPortal?.format("YYYY-MM-DD") || null,
          emd_last_date: values?.emdLastDatePortal?.format("YYYY-MM-DD") || null,
          auction_start: values?.auctionStartPortal?.format("YYYY-MM-DD") || null,
          auction_end: values?.auctionEndPortal?.format("YYYY-MM-DD") || null,
          bid_extension_time: values?.bidExtensionTimePortal,
          total_extensions: values?.totalExtensionsPortal,
          outstanding_amount: values?.outstandingAmountPortal,
          emd_amount: values?.emdAmountPortal,
          bid_increment: values?.bidIncrementPortal,
          total_bid_count: values?.totalBidCountPortal,
          authorised_officer: values?.authorisedOfficerPortal,
        },

        post_sale_details: {
          post_sale_notice: values?.postSaleNotice,
          sold_price: values?.soldPrice,
          sold_reg_date: values?.soldRegDate?.format("YYYY-MM-DD") || null,
        },

        sale_certificate_details: {
          sale_confirmation_date: values?.saleConfirmationDate?.format("YYYY-MM-DD") || null,
          sale_certificate_date: values?.saleCertificateDate?.format("YYYY-MM-DD") || null,
        },

        niyamtek_remarks_details: {
          available_documents: values?.availableDocumentsNiyamtek,
          non_available_documents: values?.nonAvailableDocumentsNiyamtek,
          discrepancy_doc: values?.discrepancyDocNiyamtek,
          discrepancy_reason: values?.discrepancyReasonNiyamtek,
          next_actionable_stage: values?.nextActionableStageNiyamtek,
          next_step_recommended: values?.nextStepRecommendedNiyamtek,
        }
      };
      console.log(payload, 'payload')
      await ReportApi.updateReportMaster(applicationNumber, payload);
      setIsChanged(false);
      setTrigger((pre) => pre + 1);
      messageApi.success("Changes saved successfully");
    } catch (error) {
      console.error("Failed to save report data:", error);
      messageApi.error("Failed to save changes");
    } finally {
      setLoading(false);
    }
  };


  const loanDetails: any = [
    { name: "niyamtekUser", label: "Niyamtek User Name", type: "text", edit: true },
    { name: "clientCode", label: "Client ID", type: "text", edit: true },
    { name: "companyName", label: "Company Name", type: "text", edit: true },
    { name: "loanAccountNo", label: "Loan Account No", type: "text", required: true },
    { name: "trustNumber", label: "Trust Number", type: "text" },
    {
      name: "assignmentAgreementDate",
      label: "Assignment Agreement Date",
      type: "date",
    },
    { name: "aoName", label: "AO Name", type: "text" },
    { name: "branch", label: "Branch", type: "text" },
    { name: "state", label: "State", type: "text" },
    { name: "region", label: "Region", type: "text" },
    {
      name: "disbursementType",
      label: "Disbursement Type ",
      type: "text",
    },
    { name: "disbursalDate", label: "Disbursal Date", type: "date" },
    { name: "disbursalAmount", label: "Disbursal Amount", type: "number" },
    { name: "loanAgreementDate", label: "Loan Agreement Date", type: "date", required: true },
    { name: "loanAmount", label: "Loan Amount", type: "number", required: true },
    { name: "loanAmountWords", label: "Loan Amount in Words", type: "text", required: true },
    { name: "npaDate", label: "Date of NPA", type: "date", required: true },
    { name: "dpd", label: "DPD as on Notice", type: "number" },
    { name: "futurePrincipal", label: "Future Principle", type: "number", required: true },
    {
      name: "principalOutstanding",
      label: "Principal Outstanding",
      type: "number",
      required: true
    },
    {
      name: "instalmentOverdue",
      label: "Instalment Overdue Amount",
      type: "number",
      required: true
    },
    {
      name: "interestOnTermination",
      label: "Interest on Termination",
      type: "number",
      required: true
    },
    {
      name: "latePaymentPenalty",
      label: "Late Payment Penalty",
      type: "number",
      required: true
    },
    {
      name: "chequeBounceCharges",
      label: "Cheque Bounce Charges",
      type: "number",
      required: true
    },
    { name: "otherAmount", label: "Other Amount", type: "number", required: true },
    {
      name: "foreClosureCharges",
      label: "Foreclosure Charges",
      type: "number",
      required: true
    },
    { name: "totalOutstanding", label: "Total Outstanding", type: "number", required: true },
    { name: "fclAsOnDate", label: "FCL (As on Date)", type: "date", required: true },
    {
      name: "totalOutstandingWords",
      label: "Total Outstanding in words",
      type: "text",
      required: true
    },

    { name: "batchCode", label: "Batch Code", type: "text" },
    { name: "propertyAddress", label: "Property Address", type: "longtext", required: true },

  ];

  const borrowerAdd: any = [
    { name: "borrowerName", label: "Name  Of Borrower", type: "text", required: true },
    { name: "borrowerAddress", label: "Borrower Address", type: "text", required: true },
    {
      name: "borrowerAddressAlt",
      label: "Borrower Address (Also At)",
      type: "text",
    },
  ];

  const CoborrowerAdd: any = [
    { name: "coBorrowerName1", label: "Co-Borrower Name 1", type: "text", required: true },
    {
      name: "coBorrowerAddress1",
      label: "Co-Borrower Address 1",
      type: "text", required: true
    },
    {
      name: "coBorrowerAddressAlt1",
      label: "Co-Borrower Address1 (Also At)",
      type: "text",
    },

    { name: "coBorrowerName2", label: "Co-Borrower Name 2", type: "text" },
    {
      name: "coBorrowerAddress2",
      label: "Co-Borrower Address 2",
      type: "text",
    },
    {
      name: "coBorrowerAddress2Alt",
      label: "Co-Borrower Address 2 (Also At)",
      type: "text",
    },

    { name: "coBorrowerName3", label: "Co-Borrower Name 3", type: "text" },
    {
      name: "coBorrowerAddress3",
      label: "Co-Borrower Address 3",
      type: "text",
    },
    {
      name: "coBorrowerAddress3Alt",
      label: "Co-Borrower Address 3 (Also At)",
      type: "text",
    },

    { name: "coBorrowerName4", label: "Co-Borrower Name 4", type: "text" },
    {
      name: "coBorrowerAddress4",
      label: "Co-Borrower Address 4",
      type: "text",
    },
    {
      name: "coBorrowerAddress4Alt",
      label: "Co-Borrower Address 4 (Also At)",
      type: "text",
    },

    { name: "coBorrowerName5", label: "Co-Borrower Name 5", type: "text" },
    {
      name: "coBorrowerAddress5",
      label: "Co-Borrower Address 5",
      type: "text",
    },
    {
      name: "coBorrowerAddress5Alt",
      label: "Co-Borrower Address 5 (Also At)",
      type: "text",
    },

    { name: "coBorrowerName6", label: "Co-Borrower Name 6", type: "text" },
    {
      name: "coBorrowerAddress6",
      label: "Co-Borrower Address 6",
      type: "text",
    },
    { name: "coBorrowerEmail", label: "Co-Borrower Email", type: "text" },
    { name: "coBorrowerNumber", label: "Co-Borrower Number", type: "text" },
    { name: "coBorrowerRange", label: "Co-Borrower Range", type: "text" },
  ];

  const GuarantorAdd: any = [
    { name: "guarantorName1", label: "Guarantor Name 1", type: "text" },
    { name: "guarantorAddress1", label: "Guarantor Address 1", type: "text" },
    { name: "guarantorName2", label: "Guarantor Name 2", type: "text" },
    { name: "guarantorAddress2", label: "Guarantor Address 2", type: "text" },
  ];

  const guarantorGroups = [GuarantorAdd.slice(0, 2), GuarantorAdd.slice(2, 4)];

  const formFields132: any = [
    {
      name: "notice132Amount",
      label: "13 (2) Notice Amount",
      type: "number",
    },
    {
      name: "notice132Date",
      label: "13 (2) Demand Notice (date)",
      type: "date",
    },
    { name: "noticeDispatchDate", label: "Dispatch Date", type: "date" },
    {
      name: "noticePastingDate",
      label: "Pasting Date",
      type: "date",
    },
    {
      name: "deliveryStatus",
      label: "Delivered Status",
      type: "text",
    },
    {
      name: "deliveryStatusDate",
      label: "Delivered Status Date",
      type: "date",
    },
    { name: "deliveredAddress", label: "Delivered address", type: "text" },
    { name: "undeliveredAddress", label: "Undelivered address", type: "text" },
    { name: "totalAddress", label: "Total address", type: "text" },
    {
      name: "publicationDate",
      label: "13 (2) Date of Publication",
      type: "date",
    },
    {
      name: "publicationEnglish",
      label: "Publication Details (English)",
      type: "text",
    },
    {
      name: "publicationLocal",
      label: "Publication Details (Vernacular)",
      type: "text",
    },
  ];

  const formFields134: any = [
    {
      name: "symbolicDeliveryStatus",
      label: "Symbolic Delivery Status",
      type: "text",
    },
    {
      name: "symbolicDeliveryStatusDate",
      label: "Symbolic Delivery Status Date",
      type: "date",
    },
    {
      name: "symbolicDispatchDate",
      label: "Symbolic Dispatch Date",
      type: "date",
    },

    { name: "symbolicPhoto", label: "Symbolic Photo", type: "text" },

    {
      name: "symbolicPossessionDate",
      label: "Symbolic Possession Date",
      type: "date",
    },

    {
      name: "symbolicPubEnglish",
      label: "Symbolic Publication English",
      type: "text",
    },

    {
      name: "symbolicPubLocal",
      label: "Symbolic Publication Local",
      type: "text",
    },

    {
      name: "symbolicPublicationDate",
      label: "Symbolic Publication Date",
      type: "date",
    },

    {
      name: "maturedDate13_4",
      label: "Matured Date 13 (4)",
      type: "date",
    }
  ];

  const formFieldsSymbolic: any = [
    {
      name: "symbolicVacationNoticeMoveable",
      label: "Vacation Notice (Moveable)",
      type: "text",
    },
    {
      name: "symbolicVacationNoticeImmoveable",
      label: "Vacation Notice (Immoveable)",
      type: "text",
    },
  ];

  const formFieldsCMJ: any = [
    {
      name: "cjmFilingDate",
      label: "CJM Filing Date",
      type: "date",
    },
    {
      name: "courtName",
      label: "Court Name",
      type: "text",
    },
    {
      name: "caseNumber",
      label: "Case Number",
      type: "text",
    },
    {
      name: "crmPLDate",
      label: "CRM PL Date",
      type: "date",
    },
    {
      name: "crmPLNo",
      label: "CRM PL No",
      type: "text",
    },
    {
      name: "nextHearingDate",
      label: "Next Hearing Date",
      type: "date",
    },
    {
      name: "ovDate",
      label: "OV Date",
      type: "date",
    },
    {
      name: "orderDate",
      label: "Order Date",
      type: "date",
    },
    {
      name: "courtAOName",
      label: "Court AO Name",
      type: "text",
    },
    {
      name: "advocateDetails",
      label: "Advocate Details",
      type: "text",
    },
    {
      name: "advComName",
      label: "Advocate Company Name",
      type: "text",
    },
    {
      name: "inventoryStatus",
      label: "Inventory Status",
      type: "text",
    }
  ]

  const formFieldPhysicalPossession: any = [
    {
      name: "physicalPossessionDate",
      label: "Physical Possession Date",
      type: "date",
    },

    {
      name: "physicalDispatchDate",
      label: "Physical Dispatch Date",
      type: "date",
    },
    {
      name: "physicalDeliveryStatus",
      label: "Physical Delivery Status",
      type: "text",
    },
    {
      name: "physicalDeliveryStatusDate",
      label: "Physical Delivery Status Date",
      type: "date",
    },
    {
      name: "physicalPhoto",
      label: "Physical Photo",
      type: "text",
    },
    {
      name: "physicalPublicationDate",
      label: "Physical Publication Date",
      type: "date",
    },
    {
      name: "physicalPubEnglish",
      label: "Physical Publication English",
      type: "text",
    },
    {
      name: "physicalPubLocal",
      label: "Physical Publication Local",
      type: "text",
    },
    {
      name: "physicalPossessionVacationNoticeMoveable",
      label: "Vacation Notice (Moveable)",
      type: "text",
    },
    {
      name: "physicalPossessionVacationNoticeImmoveable",
      label: "Vacation Notice (Immoveable)",
      type: "text",
    }
  ]

  const formFieldAuctionNotice: any = [
    {
      name: "auctionNoticeDate",
      label: "Auction Notice Date",
      type: "date",
    },
    {
      name: "auctionDate",
      label: "Auction Date",
      type: "date",
    },
    {
      name: "auctionPublicationDate",
      label: "Auction Publication Date",
      type: "date",
    },
    {
      name: "auctionPubEnglish",
      label: "Auction Publication English",
      type: "text",
    },
    {
      name: "auctionPubLocal",
      label: "Auction Publication Local",
      type: "text",
    },
    {
      name: "reservePrice",
      label: "Reserve Price",
      type: "number",
    }
  ]

  const formFieldAuctionPortal: any = [
    {
      name: "auctionDatePortal",
      label: "Auction Date",
      type: "date",
    },
    {
      name: "reservePricePortal",
      label: "Reserve Price",
      type: "number",
    },
    {
      name: "soldPricePortal",
      label: "Sold Price",
      type: "number",
    },
    {
      name: "auctionStatusPortal",
      label: "Auction Status",
      type: "text",
    },
    {
      name: "inspectionStartPortal",
      label: "Inspection Start",
      type: "date",
    },
    {
      name: "inspectionEndPortal",
      label: "Inspection End",
      type: "date",
    },
    {
      name: "emdLastDatePortal",
      label: "EMD Last Date",
      type: "date",
    },
    {
      name: "auctionStartPortal",
      label: "Auction Start",
      type: "date",
    },
    {
      name: "auctionEndPortal",
      label: "Auction End",
      type: "date",
    },
    {
      name: "bidExtensionTimePortal",
      label: "Bid Extension Time",
      type: "text",
    },
    {
      name: "totalExtensionsPortal",
      label: "Total Extensions",
      type: "text",
    },
    {
      name: "outstandingAmountPortal",
      label: "Outstanding Amount",
      type: "number",
    },
    {
      name: "emdAmountPortal",
      label: "EMD Amount",
      type: "number",
    },
    {
      name: "bidIncrementPortal",
      label: "Bid Increment",
      type: "number",
    },
    {
      name: "totalBidCountPortal",
      label: "Total Bid Count",
      type: "int",
    },
    {
      name: "authorisedOfficerPortal",
      label: "Authorised Officer",
      type: "text",
    }
  ]

  const formFieldPostSale: any = [
    {
      name: "postSaleNotice",
      label: "Post Sale Notice",
      type: "text",
    },
    {
      name: "soldPrice",
      label: "Sold Price",
      type: "number",
    },
    {
      name: "soldRegDate",
      label: "Sold Registration Date",
      type: "date",
    }
  ]

  const formFieldSaleCertificate: any = [
    {
      name: "saleConfirmationDate",
      label: "Sale Confirmation Date",
      type: "date",
    },
    {
      name: "saleCertificateDate",
      label: "Sale Certificate Date",
      type: "date",
    }
  ]

  const formFieldNiyamtekRemarks: any = [
    {
      name: "availableDocumentsNiyamtek",
      label: "Available Documents",
      type: "text",
    },
    {
      name: "nonAvailableDocumentsNiyamtek",
      label: "Non Available Documents",
      type: "text",
    },
    {
      name: "discrepancyDocNiyamtek",
      label: "Discrepancy Doc",
      type: "text",
    },
    {
      name: "discrepancyReasonNiyamtek",
      label: "Discrepancy Reason",
      type: "text",
    },
    {
      name: "nextActionableStageNiyamtek",
      label: "Next Actionable Stage",
      type: "text",
    },
    {
      name: "nextStepRecommendedNiyamtek",
      label: "Next Step Recommended",
      type: "text",
    }
  ]

  const handleConfirmCancel = () => {
    setConfirmVisible(false);
  };

  return (
    <>
      <div className="bg-transparent h-full">
        {contextHolder}
        <Card
          className=" border-gray-100 h-full"
          styles={{
            header: {
              position: "sticky",
              zIndex: 10,
              background: "white",
              top: 75,
            },
          }}
          title={
            <div className="flex flex-col gap-3 py-4 sticky top-0 md:top-[95px] z-10 bg-white w-full">
              <div className="flex justify-between items-center w-full">
                <span className="text-[20px] font-bold text-stone-800 mb-0">
                  Loan Applications
                </span>
                <div className="flex items-center gap-3">
                  {showGenerateButton == 1 ? (
                    <Button
                      type="primary"
                      icon={<IoMdRefresh className="!text-[21px] mt-1" />}
                      onClick={() => handleGenerateReport()}
                      loading={generatingReport}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      Generate Report
                    </Button>
                  ) : (
                    <Button
                      type="primary"
                      icon={<SaveOutlined />}
                      onClick={() => setConfirmVisible(true)}
                      loading={loading}
                      disabled={!isChanged}
                      className={`${!isChanged ? "opacity-75" : ""} bg-blue-600 !text-white hover:bg-blue-700`}
                    >
                      Save Changes
                    </Button>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 bg-[#e6f4ff] border-l-[4px] border-[#1677ff] rounded-r-md text-[14px] text-[#0958d9] w-full">
                <InfoCircleOutlined className="text-[#1677ff] text-[16px] flex-shrink-0" />
                <span className="font-normal text-[#0958d9] whitespace-normal">
                  <strong className="font-bold">Note:</strong> Please ensure that all required fields are filled before generating the notice.
                </span>
              </div>
            </div>
          }
        >
          <ConfigProvider theme={{ token: { colorTextDisabled: "#4B5563" } }}>
            <Form
              form={form}
              layout="vertical"
              disabled={showGenerateButton == 1}
              onValuesChange={() => {
                if (!isChanged) setIsChanged(true);
              }}
            >
              {/* Loan Details start */}

              <div id="loan-details" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span>
                    <IoDocumentTextOutline size={20} />
                  </span>
                  <span>Loan Details</span>
                </div>
              </div>
              {/* Loan Information Section */}
              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Loan Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  <Form.Item label="Application No" name="appNumber">
                    <Input
                      placeholder="Enter Application No"
                      readOnly
                      className="!bg-gray-20 cursor-not-allowed"
                    />
                  </Form.Item>

                  {loanDetails.map((field: any) => (
                    <Form.Item
                      key={field.name}
                      name={field.name}
                      label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) =>
                          e.target.value.replace(/^\s+/, ""),
                      })}
                      rules={field?.required ? [{ required: true, message: `` }] : []}
                    >
                      {field.type === "date" ? (
                        <DatePicker
                          className={`w-full w-full h-[40px] rounded-md ${field?.edit ? "!bg-gray-20 cursor-not-allowed" : ""}`}
                          format="DD-MM-YYYY"
                        />
                      ) : field.type == "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value });
                          }}
                          placeholder={`Enter ${field.label}`}
                          readOnly={field?.edit}
                          className={`${field?.edit ? "!bg-gray-20 cursor-not-allowed" : ""}`}
                        />
                      ) : field.type == "longtext" ? (
                        <Input.TextArea
                          placeholder={`Enter ${field.label}`}
                          rows={2}
                          readOnly={field?.edit}
                          className={`${field?.edit ? "!bg-gray-20 cursor-not-allowed" : ""}`}
                        />
                      ) : (
                        <Input placeholder={`Enter ${field.label}`}
                          readOnly={field?.edit}
                          className={`${field?.edit ? "!bg-gray-20 cursor-not-allowed" : ""}`}
                        />
                      )}
                    </Form.Item>
                  ))}
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Property Information
                </Text>
                <div className="grid grid-cols-1 gap-6 !p-4 !pt-0">
                  <div className="md:col-span-3 z-0">
                    <Form.Item
                      label="Description of Schedule Property"
                      name="propertyDescription"
                      required
                    >
                      {showGenerateButton == 1 ?
                        <div
                          style={{
                            height: "200px",
                            border: "1px solid #d9d9d9",
                            padding: "8px",
                            borderRadius: "6px",
                            background: "#f5f5f5",
                            overflowY: "auto"
                          }}
                          dangerouslySetInnerHTML={{
                            __html: form.getFieldValue("propertyDescription") || ""
                          }}
                        />
                        :
                        <TiptapEditor
                          value={(
                            form.getFieldValue(
                              "propertyDescription",
                            ) ?? ""
                          )
                            .replace(/<ins[^>]*>/g, "<u>")
                            .replace(/<\/ins>/g, "</u>")}
                          onChange={(value) =>
                            form.setFieldsValue({
                              propertyDescription: value,
                            })
                          }
                        />}
                    </Form.Item>
                  </div>
                </div>
              </div>

              {/* Borrower Information Section */}
              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Borrower Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 !p-4 !pt-0">
                  {borrowerAdd?.map((add: any) => (
                    <>
                      <Form.Item
                        key={add?.name}
                        label={add?.label}
                        name={add?.name}
                        getValueFromEvent={(e) =>
                          e.target.value.replace(/^\s+/, "")
                        }
                        rules={add?.required ? [{ required: true, message: `` }] : []}

                      >
                        <TextArea
                          rows={2}
                          placeholder={`Enter ${add?.label}`}
                        />
                      </Form.Item>
                    </>
                  ))}
                </div>
              </div>

              {/* Co-Borrower Information Section */}
              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Co-Borrower Information
                </Text>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 !p-4 !pt-0">
                  {CoborrowerAdd?.map((add: any) => (
                    <>
                      <Form.Item
                        key={add?.name}
                        label={add?.label}
                        name={add?.name}
                        getValueFromEvent={(e) =>
                          e.target.value.replace(/^\s+/, "")
                        }
                        rules={add?.required ? [{ required: true, message: `` }] : []}
                      >
                        <TextArea
                          rows={2}
                          placeholder={`Enter ${add?.label}`}
                        />
                      </Form.Item>
                    </>
                  ))}
                </div>
              </div>

              {/* Guarantor Information Section */}
              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Guarantor Information
                </Text>

                <div className="flex flex-col gap-4 !p-4 !pt-0">
                  {guarantorGroups.map((group, groupIndex) => (
                    <div
                      key={groupIndex}
                      className="grid grid-cols-1 md:grid-cols-2 gap-4"
                    >
                      {group.map((add: any) => (
                        <Form.Item
                          key={add?.name}
                          label={add?.label}
                          name={add?.name}
                          getValueFromEvent={(e) =>
                            e.target.value.replace(/^\s+/, "")
                          }
                        >
                          <TextArea
                            rows={2}
                            placeholder={`Enter ${add?.label}`}
                          />
                        </Form.Item>
                      ))}
                    </div>
                  ))}
                </div>
              </div>

              {/* Loan Details End */}

              {/* 13.2 Details Start */}
              <div
                id="13.2-details"
                className="mb-4 border border-gray-100 !rounded-lg"
              >
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span>
                    <IoDocumentTextOutline size={20} />
                  </span>
                  <span>13.2 Details</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  13.2 Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFields132.map((field: any) => (
                    <Form.Item
                      key={field.name}
                      name={field.name}
                      label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) =>
                          e.target.value.replace(/^\s+/, ""),
                      })}
                    >
                      {field.type === "date" ? (
                        <DatePicker
                          className="w-full w-full h-[40px] rounded-md"
                          format="DD-MM-YYYY"
                        />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value });
                          }}
                          placeholder={`Enter ${field.label}`}
                        />
                      ) : (
                        <Input placeholder={`Enter ${field.label}`} />
                      )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* 13.2 Details End */}

              {/* 13.4 Details Start */}
              <div id="13.4-details" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>13.4 Details</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  13.4 Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFields134.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* 13.4 Details End */}


              {/* Symbolic Vacation */}
              <div id="symbolic-vacation" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Symbolic Vacation</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Symbolic Vacation Notice Details
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldsSymbolic.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* Symbolic Vacation End */}

              {/* CJM Details */}
              <div id="cjm-details" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>CJM Details </span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  CJM Details Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldsCMJ.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* CJM Details End*/}

              {/* Physical possession_details Start*/}
              <div id="physical-possession" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Physical Possession Details</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Physical Possession Details Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldPhysicalPossession.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* Physical possession_details End*/}

              {/* Auction Notice */}

              <div id="auction-notice" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Auction Notice</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Auction Notice Details Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldAuctionNotice.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>

              {/* Auction Portal Details */}

              <div id="auction-portal" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Auction Portal</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Auction Portal Details Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldAuctionPortal.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" || field.type === "int" ? (
                        <Input
                          prefix={field.type === "number" ? "₹" : ""}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* Auction Portal Details End */}

              {/* Post Sale Notice */}
              <div id="post-sale-details" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Post Sale Notice</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Post Sale Notice Details Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldPostSale.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* Post Sale Notice */}

              {/* Sale Certificate */}
              <div id="sale-certificate" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Sale Certificate</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Sale Certificate Details Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldSaleCertificate.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"₹"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* Sale Certificate */}

              {/* Niyamtek Remarks */}

              <div id="niyamtek-remarks" className="mb-4">
                <div className="font-semibold text-[14px] flex items-center gap-1 bg-[#4e82f1] text-white rounded-lg p-2">
                  <span><IoDocumentTextOutline size={20} /></span>
                  <span>Niyamtek Remarks</span>
                </div>
              </div>

              <div className="mb-6 border border-gray-100 !rounded-lg">
                <Text
                  strong
                  className="!text-gray-800 !p-3 !text-[17px] !font-bold !block !mb-5 border-b border-gray-100 bg-gray-20"
                >
                  Niyamtek Remarks Information
                </Text>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 !p-4 !pt-0">
                  {formFieldNiyamtekRemarks.map((field: any) => (
                    <Form.Item key={field.name} name={field.name} label={field.label}
                      {...(field.type !== "date" && {
                        getValueFromEvent: (e) => e.target.value.replace(/^\s+/, ""),
                      })}>
                      {field.type === "date" ? (
                        <DatePicker className="w-full w-full h-[40px] rounded-md" format="DD-MM-YYYY" />
                      ) : field.type === "number" ? (
                        <Input
                          prefix={"{field.prefix}"}
                          onChange={(e) => {
                            const value = e.target.value.replace(/[^0-9.,]/g, "");
                            form.setFieldsValue({ [field.name]: value })
                          }}
                          placeholder={`Enter ${field.label}`} />
                      )
                        : (
                          <Input placeholder={`Enter ${field.label}`} />
                        )}
                    </Form.Item>
                  ))}
                </div>
              </div>
              {/* Niyamtek Remarks */}
            </Form>
          </ConfigProvider>
        </Card>
      </div>
      {/* Confirmation Modal */}
      <Modal
        open={confirmVisible}
        onOk={() => {
          handleSave();
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

export default ReportsContent;
