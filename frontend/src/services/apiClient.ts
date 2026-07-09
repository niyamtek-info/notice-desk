/**
 * Base API Client wrapper around fetch
 */

import { logoutUser, shouldLogoutForAuthError } from "@/src/utils/auth";

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

interface RequestOptions extends RequestInit {
    headers?: Record<string, string>;
    params?: Record<string, any>;
    responseType?: 'json' | 'blob' | 'text';
}

export class ApiError extends Error {
    response: {
        status: number;
        data: any;
    };

    constructor(message: string, status: number, data: any) {
        super(message);
        this.response = { status, data };
    }
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    let url = `${BASE_URL}${endpoint}`;

    if (options.params) {
        const query = new URLSearchParams(options.params).toString();
        if (query) {
            url += `?${query}`;
        }
    }

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

    // Don't set Content-Type for FormData, let the browser set it
    const isFormData = options.body instanceof FormData;
    const headers = {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
    };

    const config: RequestInit = {
        cache: options.cache ?? "no-store",
        ...options,
        headers,
    };

    const response = await fetch(url, config);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (shouldLogoutForAuthError(response.status)) {
            logoutUser(false);
        }
        throw new ApiError(errorData.detail || `Request failed with status ${response.status}`, response.status, errorData);
    }

    // Some endpoints might return empty body (204)
    if (response.status === 204) {
        return {} as T;
    }

    if (options.responseType === 'blob') {
        return response.blob() as unknown as T;
    } else if (options.responseType === 'text') {
        return response.text() as unknown as T;
    } else {
        return response.json();
    }
}

export const apiClient = {
    get: <T>(endpoint: string, options?: RequestOptions) => request<T>(endpoint, { ...options, method: "GET" }),
    post: <T>(endpoint: string, body: any, options?: RequestOptions) => request<T>(endpoint, { ...options, method: "POST", body: body instanceof FormData ? body : JSON.stringify(body) }),
    put: <T>(endpoint: string, body: any, options?: RequestOptions) => request<T>(endpoint, { ...options, method: "PUT", body: body instanceof FormData ? body : JSON.stringify(body) }),
    delete: <T>(endpoint: string, options?: RequestOptions) => request<T>(endpoint, { ...options, method: "DELETE" }),
    // Useful for file uploads or non-JSON bodies
    request,
};
