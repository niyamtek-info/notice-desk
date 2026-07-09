// store/localStorageMiddleware.ts
import { Middleware } from "@reduxjs/toolkit";

export const localStorageMiddleware: Middleware = (store) => (next) => (action) => {
  const result = next(action);
  if (typeof window !== "undefined") {
    const state = store.getState();
    localStorage.setItem("applications", JSON.stringify(state.applications.list));
  }
  return result;
};
