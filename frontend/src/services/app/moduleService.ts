/**
 * Module Service
 * Handles operations related to application modules
 * This service separates business logic from UI components.
 */

/**
 * Module Service class to handle all module-related operations
 */
class ModuleService {
  /**
   * Change the active module
   * @param moduleId The ID of the module to activate, or null to deactivate all modules
   * @param dispatch Function to dispatch state updates
   */
  changeActiveModule(
    moduleId: string | null,
    dispatch: (action: any) => void
  ): void {
    console.log(`ModuleService: Changing active module to: ${moduleId || 'none'}`);
    
    dispatch({ 
      type: 'SET_ACTIVE_MODULE', 
      payload: moduleId 
    });
  }
  
  /**
   * Get available modules configuration
   * @returns Array of module configurations
   */
  getAvailableModules(): Array<{ id: string; title: string; }> {
    // This could be expanded to fetch from an API or configuration file
    return [
      { id: 'code', title: 'Code Editor' },
      { id: 'video', title: 'Video Editor' }
      // Add more modules as needed
    ];
  }
}

// Export singleton instance
const moduleService = new ModuleService();
export default moduleService;
