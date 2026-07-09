"use client";

export const SIGN_IN_PATH = "/sign-in";

let logoutInProgress = false;

export function hasStoredToken(): boolean {
  if (typeof window === "undefined") {
    return false;
  }

  return Boolean(window.localStorage.getItem("token"));
}

export function shouldLogoutForAuthError(status: number): boolean {
  return status === 401 && hasStoredToken();
}

export function logoutUser(shouldRedirect: boolean = true): void {
  if (typeof window === "undefined" || logoutInProgress) {
    return;
  }

  logoutInProgress = true;
  window.localStorage.removeItem("token");
  localStorage.removeItem("notice_editor_draft");

  if (shouldRedirect && window.location.pathname !== SIGN_IN_PATH) {
    window.location.replace(SIGN_IN_PATH);
    return;
  }

  logoutInProgress = false;
}
