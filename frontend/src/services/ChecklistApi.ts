import { apiClient } from "./apiClient";

export interface ChecklistItem {
    id: number;
    application_number: string;
    pair_code: string;
    document_a: string;
    document_b: string;
    attribute_code: string;
    attribute_label: string;
    document_a_value?: string;
    document_b_value?: string;
    match_status: 'MATCH' | 'MISMATCH' | 'NOT_AVAILABLE';
    confidence: 'HIGH' | 'MEDIUM' | 'LOW';
    remarks?: string;
    created_at: string;
    updated_at?: string;
    rerun_validation?: number | string;
}

export interface ChecklistStatusResponse {
    status?: string;
    message?: string;
    application_number?: string;
    documents_uploaded?: boolean;
    rerun_validation?: number | string;
    items?: ChecklistItem[];
}

export const ChecklistApi = {
    getChecklist: async (applicationId: string) => {
        return apiClient.get<ChecklistItem[] | ChecklistStatusResponse>(`/checklist/${applicationId}`);
    },
    triggerMatching: async (applicationId: string) => {
        return apiClient.post<ChecklistItem[]>(`/checklist/${applicationId}/match`, {});
    },
    updateChecklist: async (applicationId: string, payload: any) => {
        return apiClient.put<ChecklistItem[]>(`/checklist/${applicationId}`, payload)
    },
    getRunValidate: async (payload : any) => {
         return apiClient.post<ChecklistItem[]>(`/checklist/run_validation`, payload, { keepalive: true })
    },
    getActiveTask: async (applicationId: string, taskType: "checklist_validation" | "checklist_match" = "checklist_validation") => {
        return apiClient.get<any>(`/checklist/active/${applicationId}`, { params: { task_type: taskType } });
    },
    getTaskStatus: async (taskId: string) => {
        return apiClient.get<any>(`/checklist/task/${taskId}`);
    },
    getProgress: async (processId: string) => {
        return apiClient.get<any>(`/checklist/progress/${processId}`);
    },
};