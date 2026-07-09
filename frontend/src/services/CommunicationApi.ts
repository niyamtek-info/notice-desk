import { apiClient } from "./apiClient";

export const CommunicationApi = {
    sendEmail: async (data: any) => {
        return apiClient.post("/communication/email", data);
    },

    getHistory: async (applicationId: string) => {
        return apiClient.get(`/communication/history/${applicationId}`);
    },


    downloadPdf: async (data: any, initialData: any, templateNameVal: any) => {
        const blob = await apiClient.post<Blob>(
            "/mail/generate-pdf",
            data,
            { responseType: "blob" }
        );

        const url = window.URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = `${initialData?.loan_account_number}-${initialData?.borrower_name}-${templateNameVal?.template_type}.pdf`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        window.URL.revokeObjectURL(url);
    }

};