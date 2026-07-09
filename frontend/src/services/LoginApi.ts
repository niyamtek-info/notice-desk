import { apiClient } from "./apiClient";

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export const LoginApi = {
    login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
        return apiClient.post<LoginResponse>("/auth/login", credentials);
    },
};
