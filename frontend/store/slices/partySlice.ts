import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface Lawyer {
  id?: string;
  key: string;
  firstName: string;
  lastName: string;
  dob: string;
  contact: string;
  email: string;
  address: string;
  barCouncilCode: string;
  barCouncilState: string;
  empanelmentDate?: string;
  empanelmentStatus: string;
  empaneledBranch: string;
  regionalOffice: string;
  zonalOffice: string;
}

export interface Valuer {
  id?: string;
  key: string;
  firstName: string;
  lastName: string;
  authorizationDate: string;
  authorizationBranch: string;
  registrationDetails: string;
  empanelStatus: string;
  empaneledBranch: string;
  regionalOffice: string;
  zonalOffice: string;
  contact: string;
  email: string;
  address: string;
}

export interface CA {
  id?: string;
  key: string;
  firstName: string;
  lastName: string;
  contact: string;
  email: string;
  address: string;
  caRegNumber: string;
}

// Slice state
interface PartiesState {
  lawyers: Lawyer[];
  valuers: Valuer[];
  cas: CA[];
}

const initialState: PartiesState = {
  lawyers: [],
  valuers: [],
  cas: [],
};

export const PartiesSlice = createSlice({
  name: "parties",
  initialState,
  reducers: {
    addLawyer: (state, action: PayloadAction<Lawyer>) => {
      state.lawyers.push(action.payload);
    },
    addValuer: (state, action: PayloadAction<Valuer>) => {
      state.valuers.push(action.payload);
    },
    addCA: (state, action: PayloadAction<CA>) => {
      state.cas.push(action.payload);
    },
    setLawyers: (state, action: PayloadAction<Lawyer[]>) => {
      state.lawyers = action.payload;
    },
    setValuers: (state, action: PayloadAction<Valuer[]>) => {
      state.valuers = action.payload;
    },
    setCAs: (state, action: PayloadAction<CA[]>) => {
      state.cas = action.payload;
    },
  },
});

export const { 
  addLawyer, 
  addValuer, 
  addCA, 
  setLawyers, 
  setValuers, 
  setCAs 
} = PartiesSlice.actions;

export default PartiesSlice.reducer;