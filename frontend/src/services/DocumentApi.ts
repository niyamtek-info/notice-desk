import { apiClient } from "./apiClient";

export interface ExtractDocument {
  file_id: string;
  doc_type?: string;
  document_url: string;
  original_document_url: string;
  document_name: string;
  ai_parsed_output?: Record<string, unknown>;
  json?: Record<string, unknown>;
  error_message?: string;
}

export interface ActiveDocument {
  doc_type: string;
  progress: number;
  stage: string;
  status?: string;
  error?: string;
  filename?: string;
}

export type ActiveDocsResponse = Record<string, ActiveDocument>;

export interface ExtractionProgressResponse {
  file_id: string;
  progress: number;
  stage: string;
  status: string;
  task_id?: string;
  application_number?: string;
  doc_type?: string;
  filename?: string;
}

export const DocumentApi = {
  getDocuments: async (
    applicationNumber: string,
  ): Promise<{
    docs: ExtractDocument[];
    activeDocs: ActiveDocsResponse;
  }> => {
    const [docsRes, activeDocsRes] = await Promise.all([
      apiClient.get<ExtractDocument[]>(
        `/extract/?application_number=${applicationNumber}`,
      ),
      apiClient.get<ActiveDocsResponse>(`/extract/active/${applicationNumber}`),
    ]);

    return {
      docs: docsRes,
      activeDocs: activeDocsRes,
    };
  },

  documentPutApi: async (selectedDocId: string, values: any) => {
    return apiClient.put(`/extract/${selectedDocId}`, values);
  },

  documentProgressGetApi: async (
    fileId: string,
  ): Promise<ExtractionProgressResponse> => {
    return apiClient.get<ExtractionProgressResponse>(
      `/extract/progress/${fileId}`,
    );
  },

  documentRecommentation: async (applicationNumber: string) => {
    return apiClient.get(`/extract/recommendations/${applicationNumber}`);
  },

  documentDeleteApi: async (id: string) => {
    return apiClient.delete(`/extract/${id}`);
  },

  compareDocuments: async (
    applicationNumber: string,
    file1: string,
    file2: string,
    mode: string,
  ) => {
    const res = await apiClient.post("/compare/", {
      application_number: applicationNumber,
      file1,
      file2,
      mode,
    });

    return res;
  },

  uploadDocument: async (formData: FormData) => {
    return apiClient.post(`/extract/process`, formData);
  },
};
