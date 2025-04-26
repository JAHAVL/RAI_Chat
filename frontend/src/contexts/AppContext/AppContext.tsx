import React, { createContext, useContext, useReducer } from 'react';

// --- Type Definitions ---
export interface AppState {
  activeModule: string | null;
  loading: boolean;
}

export type AppAction =
  | { type: 'SET_ACTIVE_MODULE'; payload: string | null }
  | { type: 'SET_LOADING'; payload: boolean };

export interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  setActiveModule: (moduleId: string | null) => void;
  setLoading: (isLoading: boolean) => void;
}

// --- Initial State ---
const initialState: AppState = {
  activeModule: null,
  loading: false
};

// --- Reducer Function ---
function appReducer(state: AppState, action: AppAction): AppState {
  console.log(`AppReducer Action: ${action.type}`);

  switch (action.type) {
    case 'SET_ACTIVE_MODULE':
      return { ...state, activeModule: action.payload };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    default:
      console.log(`AppReducer Action: Unknown type ${(action as any)?.type}`);
      return state;
  }
}

// --- Context Setup ---
const defaultAppContextValue: AppContextType = {
  state: initialState,
  dispatch: () => null,
  setActiveModule: () => null,
  setLoading: () => null
};

const AppContext = createContext<AppContextType>(defaultAppContextValue);

// --- Hook for Components ---
export function useApp(): AppContextType {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

// --- Provider Component ---
interface AppProviderProps {
  children: React.ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  console.log("--- AppProvider Render ---");
  const [state, dispatch] = useReducer(appReducer, initialState);
  
  // Action creators
  const setActiveModule = (moduleId: string | null) => {
    dispatch({ type: 'SET_ACTIVE_MODULE', payload: moduleId });
  };
  
  const setLoading = (isLoading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: isLoading });
  };
  
  return (
    <AppContext.Provider 
      value={{ 
        state, 
        dispatch, 
        setActiveModule, 
        setLoading 
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export default AppContext;
