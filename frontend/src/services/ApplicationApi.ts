import { apiClient, BASE_URL } from "./apiClient";

export const ApplicationApi = {
  create: async (payload: any) => {
    return apiClient.post("/applications/manual", payload);
  },

  //    upload: async (file: File) => {
  //     const formData = new FormData();
  //     formData.append("file", file);

  //     return apiClient.post("/applications/upload", formData);
  //    },

  upload: async (file: File): Promise<Blob> => {
    const formData = new FormData();
    formData.append("file", file);

    const response = await apiClient.post<Blob>(
      "/applications/upload",
      formData,
      { responseType: "blob" },
    );

    return response;
  },

  getUploadUrl: () => `${BASE_URL}/applications/upload`,

  getAll: async (params?: any) => {
    return apiClient.get("/applications", { params });
  },

  getById: async (id: string) => {
    return apiClient.get(`/applications/${id}`);
  },

  update: async (id: string, data: any) => {
    return apiClient.put(`/applications/${id}`, data);
  },
  deleteApplicationApi: async (id: string) => {
    return apiClient.delete(`/applications/${id}`);
  },
};
