import { apiClient } from "./apiClient";

export interface TranslationApplyResponse {
    status: "applied";
    record_id?: string;
    language?: string;
    application_number?: string | null;
    doc_type?: string | null;
}

export const TranslateApi = {
    /**
     * Persist a translated extraction payload into the document's extracted_*
     * tables (same write path as the Edit Data save, minus the sale-deed English
     * normalization) and mark the checklist for re-run. Validation is NOT
     * triggered — the user runs it from the checklist "Run Validation" button.
     */
    applyTranslation: async (payload: {
        record_id: string;
        target_language: string;
        translated_data?: Record<string, unknown>;
    }) => {
        // NOTE: no `keepalive` — the translated_data body routinely exceeds the
        // browser's 64KB keepalive limit and the request would be rejected.
        return apiClient.post<TranslationApplyResponse>(`/translate/apply`, payload);
    },
};
