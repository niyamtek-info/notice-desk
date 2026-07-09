import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface LoginState {
    value : any;
    sessionExpired: boolean;
}

const initialState:LoginState = {
   value : {},
   sessionExpired: false
}

const loginSlice = createSlice ({
    name : "status",
    initialState,
     reducers: {
        superAdmin: (state, action: PayloadAction<any>) => {
          state.value = action.payload;
        },
        setSessionExpired: (state, action: PayloadAction<boolean>) => {
          state.sessionExpired = action.payload;
        },
    }
})

export const { superAdmin, setSessionExpired } = loginSlice.actions;

export default loginSlice.reducer;

// dispatch(superAdmin(json));

// const { status } = useSelector((state: RootState) => state.status);