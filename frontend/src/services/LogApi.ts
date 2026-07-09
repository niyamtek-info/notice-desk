import { apiClient } from "./apiClient";

export interface LogEntry {
    application_id: string;
    status: string;
    step_name: string;
    message: string;
    metadata?: Record<string, any>;
}

export const LogApi = {
    addLog: async (
        applicationId: string,
        status: string,
        stepName: string,
        message: string,
        metadata: Record<string, any> = {}
    ) => {
        return apiClient.post(`/logs/applications/${applicationId}/log`, {
            status,
            type: stepName,
            details: message,
        });
    },

    getLogs: async (applicationId: string) => {
        return apiClient.get<any[]>(`/logs/applications/${applicationId}/logs`);
    },
};
