import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface Application {
  type_of_work: string;
  record_id: string;
  application_no: string;
  loan_account_number?: string | null;
  borrower_name?: string | null;
  bank_name?: string | null;
  state?: string | null;
  location?: string | null;
  assigned_date?: string | null;
  process_status?: string | null;
  report_status?: string | null;
  loan_amount?: number | null;
  created_at?: string;
  batch_code?: string | null;
}

interface ApplicationsState {
  list: Application[];
}

const initialState: ApplicationsState = {
  list: [],
};

const applicationsSlice = createSlice({
  name: "applications",
  initialState,
  reducers: {
    addApplication: (state, action: PayloadAction<Application>) => {
      state.list = [action.payload, ...state.list];
    },
    setApplications: (state, action: PayloadAction<Application[]>) => {
      state.list = action.payload;
    },
    removeApplication: (state, action: PayloadAction<string>) => {
      state.list = state.list.filter((app) => app.record_id !== action.payload);
    },
  },
});

export const { addApplication, setApplications, removeApplication } =
  applicationsSlice.actions;
export default applicationsSlice.reducer;
