// RAI_Chat/frontend/src/types/styled.d.ts
import 'styled-components';

// Define the structure of your theme based on the object in App.tsx
interface AppTheme {
  colors: {
    background: string;
    text: string;
    accent: string;
    hover: string;
    userMessage: string;
    assistantMessage: string;
    systemMessage: string;
    border: string;
    inputBackground: string;
    shadow: string;
    placeholder: string;
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
    full: string;
  };
  typography: {
    fontFamily: string;
    fontSize: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
    };
    fontWeight: {
      normal: number;
      medium: number;
      bold: number;
    };
    lineHeight: {
      tight: number;
      normal: number;
      relaxed: number;
    };
  };
  transitions: {
    fast: string;
    normal: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
}

// Augment the DefaultTheme interface from styled-components
declare module 'styled-components' {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  export interface DefaultTheme extends AppTheme {}
}