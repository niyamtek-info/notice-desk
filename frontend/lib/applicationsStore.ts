export interface Application {
    id: number | string;
    [key: string]: unknown;
}

// 📝 in-memory store (replace with DB in real app)
export const applications: Application[] = [];
