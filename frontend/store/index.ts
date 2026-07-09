"use client";
import { configureStore } from "@reduxjs/toolkit";
import applicationsReducer from "./slices/applicationsSlice";
import { localStorageMiddleware } from "./localStorageMiddleware";
import { PartiesSlice } from "./slices/partySlice";
import { tasksSlice } from "./slices/tasksSlice";
import { communicationSlice } from "./slices/communicationSlice";
import loginSlice from "./slices/loginSlice";

export const store = configureStore({
  reducer: {
    applications: applicationsReducer,
    parties: PartiesSlice.reducer,
    tasks: tasksSlice.reducer,
    communication: communicationSlice.reducer,
    login:loginSlice
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(localStorageMiddleware)
});

// 🔹 Infer RootState & AppDispatch types
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
