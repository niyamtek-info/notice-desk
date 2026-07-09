"use client";

import { useEffect } from "react";
import axios from "axios";
import { shouldLogoutForAuthError } from "@/src/utils/auth";
import { useDispatch } from "react-redux";
import { AppDispatch } from "@/store";
import { setSessionExpired } from "@/store/slices/loginSlice";
import SessionExpiryModal from "../modals/SessionExpiryModal";

type AuthFetchWindow = Window &
  typeof globalThis & {
    __AUTH_FETCH_PATCHED__?: boolean;
    __AUTH_ORIGINAL_FETCH__?: typeof window.fetch;
    __AUTH_AXIOS_PATCHED__?: boolean;
  };

export default function AuthSessionManager() {
  const dispatch = useDispatch<AppDispatch>();

  useEffect(() => {
    if (typeof window === "undefined") return;

    const authWindow = window as AuthFetchWindow;

    // Patch Fetch
    if (!authWindow.__AUTH_FETCH_PATCHED__) {
      const originalFetch = window.fetch.bind(window);
      authWindow.__AUTH_FETCH_PATCHED__ = true;
      authWindow.__AUTH_ORIGINAL_FETCH__ = originalFetch;

      window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
        const response = await originalFetch(input, init);

        if (shouldLogoutForAuthError(response.status)) {
          dispatch(setSessionExpired(true));
        }

        return response;
      };
    }

    // Patch Axios
    if (!authWindow.__AUTH_AXIOS_PATCHED__) {
      authWindow.__AUTH_AXIOS_PATCHED__ = true;
      axios.interceptors.response.use(
        (response) => response,
        (error) => {
          if (shouldLogoutForAuthError(error?.response?.status)) {
            dispatch(setSessionExpired(true));
          }
          return Promise.reject(error);
        }
      );
    }
  }, [dispatch]);

  return <SessionExpiryModal />;
}
