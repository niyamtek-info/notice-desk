import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface CommunicationState {
  editorContent: string;
  template: string;
  structuredComponents: any;
}

const initialState: CommunicationState = {
  editorContent: "",
  template: "",
  structuredComponents: { IMAGE: [], TABLE: [] },
};

export const communicationSlice = createSlice({
  name: "communication",
  initialState,
  reducers: {
    setEditorContent(state, action: PayloadAction<string>) {
      state.editorContent = action.payload;
    },
    setTemplate(state, action: PayloadAction<string>) {
      state.template = action.payload;
    },
    setStructuredComponents(state, action: PayloadAction<any>) {
      state.structuredComponents = action.payload;
    },
  },
});

export const { setEditorContent, setTemplate, setStructuredComponents } =
  communicationSlice.actions;
export default communicationSlice.reducer;