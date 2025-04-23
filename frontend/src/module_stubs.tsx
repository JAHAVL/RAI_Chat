/**
 * Module Stubs
 * This file provides placeholder definitions for modules that are visually represented
 * in the UI but don't have full functionality implemented.
 */

import React from 'react';
import styled from 'styled-components';

// --- Type Definitions ---

// Type for the registerModule function passed to the register method
type RegisterModuleFunction = (moduleId: string, moduleConfig: ModuleConfig) => void;

// Interface for the module configuration passed to registerModule
export interface ModuleConfig { // Export the interface
  name: string;
  description: string;
  icon: string;
  components: { [key: string]: React.ComponentType<any> }; // Allow any component type
}

// Interface for the module definition object
export interface ModuleDefinition { // Export the interface
  MODULE_ID: string;
  name: string;
  icon: string;
  description: string;
  components: { [key: string]: React.ComponentType<any> };
  register: (registerModule: RegisterModuleFunction) => ModuleDefinition; // Return type is the module itself
}

// --- Styled Components ---
const ModulePlaceholder = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem;
  background-color: #1e1e1e;
  color: #a0a0a0;
  text-align: center;
`;

const PlaceholderIcon = styled.div`
  font-size: 3rem;
  margin-bottom: 1rem;
`;

const PlaceholderTitle = styled.h3`
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #e0e0e0;
`;

const PlaceholderDescription = styled.p`
  font-size: 1rem;
  line-height: 1.5;
`;

// --- Placeholder Components ---

// Video Module Placeholder Component
const VideoModulePlaceholder: React.FC = () => (
  <ModulePlaceholder>
    <PlaceholderIcon>🎥</PlaceholderIcon>
    <PlaceholderTitle>Video Module</PlaceholderTitle>
    <PlaceholderDescription>
      The video functionality has been temporarily disabled in this version.
      The module UI elements are preserved for consistency.
    </PlaceholderDescription>
  </ModulePlaceholder>
);

// Code Editor Module Placeholder Component
const CodeEditorModulePlaceholder: React.FC = () => (
  <ModulePlaceholder>
    <PlaceholderIcon>💻</PlaceholderIcon>
    <PlaceholderTitle>Code Editor Module</PlaceholderTitle>
    <PlaceholderDescription>
      The code editing functionality has been temporarily disabled in this version.
      The module UI elements are preserved for consistency.
    </PlaceholderDescription>
  </ModulePlaceholder>
);

// --- Stub Module Definitions ---

// Apply the ModuleDefinition type
const videoModule: ModuleDefinition = {
  MODULE_ID: 'video',
  name: 'Video',
  icon: '🎥',
  description: 'Video functionality (disabled)',
  components: {
    VideoModule: VideoModulePlaceholder
  },
  // Type the registerModule parameter
  register: function(registerModule: RegisterModuleFunction) {
    registerModule(this.MODULE_ID, {
      name: this.name,
      description: this.description,
      icon: this.icon,
      components: this.components
    });
    return this;
  }
};

// Apply the ModuleDefinition type
const codeEditorModule: ModuleDefinition = {
  MODULE_ID: 'code_editor',
  name: 'Code Editor',
  icon: '💻',
  description: 'Code editing functionality (disabled)',
  components: {
    CodeEditor: CodeEditorModulePlaceholder
  },
  // Type the registerModule parameter
  register: function(registerModule: RegisterModuleFunction) {
    registerModule(this.MODULE_ID, {
      name: this.name,
      description: this.description,
      icon: this.icon,
      components: this.components
    });
    return this;
  }
};

// Use ES Module export
export {
  videoModule,
  codeEditorModule
};