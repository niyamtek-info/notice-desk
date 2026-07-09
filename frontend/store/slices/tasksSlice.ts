import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export type StatusType = "Response Received" | "Request Sent" | "Request Opt";

export interface PartyDetails {
  id: string;
  name: string;
  contact: string;
  email: string;
}

export interface Task {
  taskId: string;
  application_number: string;
  assignedBy: string;
  assignedByEmail: string;
  partyType: "lawyer" | "valuer"; 
  partyDetails: PartyDetails;
  purpose: string;
  dueDate: string;
  status: StatusType; // ✅ changed from string
}

interface TasksState {
  tasks: Task[];
}

const initialState: TasksState = {
  tasks: [],
};

export const tasksSlice = createSlice({
  name: "tasks",
  initialState,
  reducers: {
    addTask(state, action: PayloadAction<Task>) {
      state.tasks.push(action.payload);
    },
    setTasks(state, action: PayloadAction<Task[]>) {
      state.tasks = action.payload;
    },
    updateStatus(
      state,
      action: PayloadAction<{ taskId: string; status: StatusType }>
    ) {
      const { taskId, status } = action.payload;
      const task = state.tasks.find((t) => t.taskId === taskId);
      if (task) {
        task.status = status;
      }
    },
  },
});

export const { addTask, setTasks, updateStatus } = tasksSlice.actions;
export default tasksSlice.reducer;
