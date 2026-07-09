import partyData from "@/data/parties.json";
import { apiClient } from "./apiClient";

export const MasterApi = {
    getParties: async (applicationId: string) => {
        return apiClient.get(`/parties/${applicationId}`);
    },

    getPartiesByType: async (type: string) => {
        const normalizedType = type.toLowerCase();

        if (normalizedType === "lawyer") {
            return partyData.lawyers;
        }

        if (normalizedType === "valuer") {
            return partyData.valuers;
        }

        if (normalizedType === "ca") {
            return partyData.cas;
        }

        throw new Error("Invalid type. Use lawyer, valuer, or ca");
    },
};
