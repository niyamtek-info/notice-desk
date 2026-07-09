import { apiClient } from "./apiClient";

export const BankApi = {
  getBankList: async () => {
    return apiClient.get(`/client/`);
  },
  postBank:async (payload:any) => {
    return apiClient.post(`/client`,payload)
  },
  putBank:async (id:number,payload:any) => {
    return apiClient.put(`/client/${id}`,payload)
  },
  deleteBank:async (id:number) => {
    return apiClient.delete(`/client/${id}`)
  },
  getBankCodeList:async (code:string) => {
    return apiClient.get(`/client/${code}`);
  },

  postAO:async (payload:any) => {
    return apiClient.post(`/client/aos`,payload)
  },
  putAO:async (id:number,payload:any) => {
    return apiClient.put(`/client/aos/${id}`,payload)
  },
  deleteAO:async (id:number) => {
    return apiClient.delete(`/client/aos/${id}`)
  },
  
  getTemplateList:async () => {
    return apiClient.get(`/templates`)
  },
  postTemplateList:async (payload:any) => {
    return apiClient.post(`/templates`,payload)
  },
  putTemplate:async (id:any,payload:any) => {
    return apiClient.put(`/templates/${id}`,payload)

  },
  deleteTemplate:async (id:any) => {
    return apiClient.delete(`/templates/${id}`)
  },

  getTemplateType:async () => {
    return apiClient.get(`/master-template/master-template/template-types`)
  },

  masterPostTemplate:async (payload:any) => {
    return apiClient.post(`/master-template/master-template/upload`,payload)
  },

  masterPutTemplate:async (id:number,payload:any) => {
    return apiClient.put(`/master-template/${id}`,payload)
  },
  // getSingleClientTemplate:async (code:string) => {
  //       return apiClient.get(`/master-template/master-template/client/${code}`)
  // }
  getSingleClientTemplate:async (code:string) => {
        const trimmedCode = (code || "").trim();
        if (!trimmedCode) {
          return { templates: [] };
        }
        return apiClient.get(`/master-template/master-template/client/${trimmedCode}`)
  }
}

