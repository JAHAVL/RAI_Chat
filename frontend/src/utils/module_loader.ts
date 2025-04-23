/**
 * Module Registration System for AI Assistant App
 * This system allows modules to register their React components and API endpoints
 * with the main application, enabling a truly modular architecture where modules
 * can be distributed and purchased separately.
 */

import React from 'react';
// Import the config type from stubs
import type { ModuleConfig } from '../module_stubs'; // Removed .tsx extension

// --- Type Definitions ---

// Interface for the stored module, extending the config with registration date
interface RegisteredModule extends ModuleConfig {
  registered: Date;
}

// Type for the map storing registered modules
type RegisteredModulesMap = {
  [moduleId: string]: RegisteredModule;
};

// Type for the registerModule function itself (to be exported)
export type RegisterModuleFunction = (moduleId: string, moduleConfig: ModuleConfig) => void;

// --- Module Store ---

// Store for registered modules, typed with the map type
const registeredModules: RegisteredModulesMap = {};

// --- Functions ---

/**
 * Register a module with the application
 * @param {string} moduleId - Unique identifier for the module
 * @param {ModuleConfig} moduleDefinition - Object containing module components and API info
 */
const registerModule: RegisterModuleFunction = (moduleId, moduleDefinition) => {
  if (registeredModules[moduleId]) {
    console.warn(`Module ${moduleId} is already registered. Overwriting previous registration.`);
  }

  // Ensure the definition conforms to ModuleConfig before adding registration date
  const moduleToStore: RegisteredModule = {
    ...moduleDefinition,
    registered: new Date()
  };

  registeredModules[moduleId] = moduleToStore;

  console.log(`Module ${moduleId} successfully registered:`, moduleDefinition.name);
};

/**
 * Get a registered module
 * @param {string} moduleId - ID of the module to retrieve
 * @returns {RegisteredModule | null} Module definition or null if not found
 */
const getModule = (moduleId: string): RegisteredModule | null => {
  return registeredModules[moduleId] || null;
};

/**
 * Get all registered modules
 * @returns {RegisteredModulesMap} Object containing all registered modules
 */
const getAllModules = (): RegisteredModulesMap => {
  // Return a shallow copy to prevent direct modification of the internal store
  return { ...registeredModules };
};

/**
 * Check if a module is registered
 * @param {string} moduleId - ID of the module to check
 * @returns {boolean} True if the module is registered
 */
const isModuleRegistered = (moduleId: string): boolean => {
  return !!registeredModules[moduleId];
};

/**
 * Get components from a registered module
 * @param {string} moduleId - ID of the module
 * @returns {{ [key: string]: React.ComponentType<any> }} Object containing module's React components or empty object if not found
 */
const getModuleComponents = (moduleId: string): { [key: string]: React.ComponentType<any> } => {
  const module = getModule(moduleId);
  // Revert to optional chaining - the root cause is likely the ModuleConfig import error
  // Ensure module and module.components exist before accessing
  return module?.components ? module.components : {};
};

// Ensure ES Module export
export {
  registerModule,
  getModule,
  getAllModules,
  isModuleRegistered,
  getModuleComponents
  // RegisterModuleFunction is exported via 'export type' above
};