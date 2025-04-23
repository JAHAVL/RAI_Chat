/**
 * Module Discovery System
 * This file handles the dynamic discovery and loading of modules
 * It scans module directories and loads modules that are installed
 */
import { registerModule } from './module_loader'; // Keep function import
// Placeholder type for RegisterModuleFunction until module_loader is converted
import type { ModuleConfig } from '../module_stubs'; // Removed .tsx extension
type RegisterModuleFunction = (moduleId: string, moduleConfig: ModuleConfig) => void;
// Assuming module_stubs.tsx exports the ModuleDefinition type or define it here
import { videoModule, codeEditorModule } from '../module_stubs'; // Removed .tsx extension
import type { ModuleDefinition } from '../module_stubs'; // Removed .tsx extension

// Import Node.js types if not automatically available
import * as fs from 'fs';
import * as path from 'path';

// --- Type Definitions ---
// (ModuleDefinition imported above, RegisterModuleFunction defined locally as placeholder)


// --- Module Discovery ---

// Root directory for modules - This path might need adjustment depending on where the Electron app runs from
// Assuming it runs from the project root where 'modules' directory exists
const MODULES_DIR: string = path.resolve(process.cwd(), 'modules'); // Use process.cwd() for potentially better path resolution

/**
 * Discover and load available modules
 * @returns {Promise<ModuleDefinition[]>} Array of loaded module definitions
 */
const discoverModules = async (): Promise<ModuleDefinition[]> => {
  // Type the array explicitly
  const loadedModules: ModuleDefinition[] = [];

  try {
    // First, register our stub modules
    // Ensure the stubs conform to ModuleDefinition
    loadedModules.push(videoModule.register(registerModule));
    loadedModules.push(codeEditorModule.register(registerModule));

    // Check if MODULES_DIR exists before trying to read it
    if (!fs.existsSync(MODULES_DIR)) {
      console.warn(`Modules directory not found: ${MODULES_DIR}`);
      return loadedModules; // Return only stub modules if directory doesn't exist
    }

    // Get all module directories, but skip video and code_editor since we've stubbed them
    const moduleDirs: string[] = fs.readdirSync(MODULES_DIR)
      .filter(dir => fs.statSync(path.join(MODULES_DIR, dir)).isDirectory() && // Ensure it's a directory
              dir.endsWith('_module') &&
              dir !== 'video_module' &&
              dir !== 'code_editor_module')
      .map(dir => path.join(MODULES_DIR, dir));

    // For each module directory, check if it has a UI/React folder with a module.js file
    for (const moduleDir of moduleDirs) {
      // Look for module.ts or module.js (prefer .ts if converting)
      const moduleTsPath = path.join(moduleDir, 'ui', 'react', 'module.ts');
      const moduleJsPath = path.join(moduleDir, 'ui', 'react', 'module.js');
      let modulePathToLoad: string | null = null;

      if (fs.existsSync(moduleTsPath)) {
          modulePathToLoad = moduleTsPath;
      } else if (fs.existsSync(moduleJsPath)) {
          modulePathToLoad = moduleJsPath;
      }

      if (modulePathToLoad) {
        try {
          // Use a safer way to require the module
          const moduleFullPath = path.resolve(modulePathToLoad);
          // eslint-disable-next-line @typescript-eslint/no-var-requires, import/no-dynamic-require
          const moduleDefinition = require(moduleFullPath); // Dynamic require might still be needed here

          // Basic check if it looks like our module definition
          if (moduleDefinition && typeof moduleDefinition.register === 'function' && typeof moduleDefinition.MODULE_ID === 'string') {
            // Cast to ModuleDefinition for type safety, though dynamic require limits this
            const typedModuleDefinition = moduleDefinition as ModuleDefinition;
            const loadedModule = typedModuleDefinition.register(registerModule);
            loadedModules.push(loadedModule);
            console.log(`Loaded module: ${typedModuleDefinition.MODULE_ID}`);
          } else {
            console.warn(`Module at ${modulePathToLoad} does not have a valid structure (missing register function or MODULE_ID)`);
          }
        } catch (error: any) { // Catch as any
          console.error(`Error loading module at ${modulePathToLoad}:`, error.message || error);
        }
      }
    }

    console.log(`Discovered and loaded ${loadedModules.length} modules`);
    return loadedModules;
  } catch (error: any) { // Catch as any
    console.error('Error discovering modules:', error.message || error);
    return loadedModules; // Return potentially only stub modules on error
  }
};

/**
 * Initialize the module system and load all available modules
 * @returns {Promise<ModuleDefinition[]>} Array of loaded module definitions
 */
const initializeModuleSystem = async (): Promise<ModuleDefinition[]> => {
  console.log('Initializing module system...');
  const modules = await discoverModules();
  console.log(`Module system initialized with ${modules.length} modules`);
  return modules;
};

export {
  discoverModules,
  initializeModuleSystem
};