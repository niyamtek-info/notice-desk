import { apiClient } from "./apiClient";

export const ReportApi = {
  getReport: async (applicationNumber: string) => {
    return apiClient.get(`/report/${applicationNumber}`);
  },

  getMaster: async (applicationNumber: string) => {
    return apiClient.get(`/sarfaesi/sarfaesi/application/${applicationNumber}`)
  },
  generate: async (applicationNumber: string) => {
    return apiClient.post(`/report/generate`, { application_number: applicationNumber });
  },

  updateReport: async (applicationNumber: string, data: any) => {
    return apiClient.put(`/report/${applicationNumber}`, data);
  },

  updateReportMaster: async (applicationNumber: string, data: any) => {
    return apiClient.put(`/sarfaesi/sarfaesi/application/${applicationNumber}`, data);
  },

  createReport: async (applicationNumber: string, data: any) => {
    return apiClient.post(`/report/${applicationNumber}`, data);
  },

  createSnapshot: async (applicationNumber: string) => {
    return apiClient.post(`/report/${applicationNumber}/snapshot`, {});
  },

  create: async (data: any) => {
    return apiClient.post<Blob>("/report/bulk-download", data, {
      responseType: "blob",
    });
  },

  downloadTemplate: async () => {
    return apiClient.get<Blob>(`/applications/download-template`, {
      responseType: "blob",
    });
  },

  bulkNoticeGenerate: async (payload:any) => {
    return apiClient.post<Blob>(`/mail/bulk-notice-download`,payload ,{
       responseType: "blob",
    })
  }
};
