import { LogApi } from "../services/LogApi";

export async function addLog(applicationNumber: string, status: string, type: string, details: string) {
  try {
    return await LogApi.addLog(applicationNumber, status, type, details);
  } catch (err) {
    console.error("Log API Error:", err);
  }
}
