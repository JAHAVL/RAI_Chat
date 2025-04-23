"""
Path Finder utility for AI Assistant App.
Identifies hardcoded paths in the codebase that may need to be updated
for cross-platform and server compatibility.
"""
import os
import re
import glob
import json
from pathlib import Path

def find_hardcoded_paths(directory, output_file=None):
    """
    Find potential hardcoded paths in Python files.
    
    Args:
        directory: Root directory to search
        output_file: Optional file to save results
        
    Returns:
        Dictionary of files and their hardcoded paths
    """
    # Pattern to match absolute paths (macOS/Unix style)
    path_pattern = re.compile(r'[\'\"](/[^\'"]+)[\'"]')
    
    # Find all Python files
    python_files = glob.glob(f"{directory}/**/*.py", recursive=True)
    results = {}
    
    print(f"Scanning {len(python_files)} Python files for hardcoded paths...")
    
    for file_path in python_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            try:
                content = file.read()
                matches = path_pattern.findall(content)
                
                # Filter to likely real paths (not regex patterns, etc)
                real_paths = [
                    path for path in matches 
                    if os.path.exists(path) or 
                    ('/' in path and not path.startswith('/('))
                ]
                
                if real_paths:
                    # Store relative path to make output more readable
                    rel_path = os.path.relpath(file_path, directory)
                    results[rel_path] = real_paths
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
    
    # Save results if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_file}")
    
    return results

def print_results(results):
    """Print the results in a readable format"""
    total_paths = sum(len(paths) for paths in results.values())
    total_files = len(results)
    
    print(f"\nFound {total_paths} potential hardcoded paths in {total_files} files:\n")
    
    for file, paths in results.items():
        print(f"\n{file}:")
        for path in paths:
            print(f"  - {path}")
            
    print("\nThese paths should be replaced with AppConfig.get_path() calls")
    print("Example:")
    print('  Before: video_path = "/Users/username/app/data/videos/sample.mp4"')
    print('  After:  video_path = AppConfig.get_path("video/sample.mp4")')

def suggest_replacements(results):
    """Suggest replacements for common patterns"""
    suggestions = {}
    
    for file, paths in results.items():
        file_suggestions = []
        
        for path in paths:
            suggestion = None
            
            # Try to identify common patterns
            if '/videos/' in path or '/video/' in path:
                rel_path = path.split('/videos/')[-1] if '/videos/' in path else path.split('/video/')[-1]
                suggestion = f'AppConfig.get_path("video/{rel_path}")'
            elif '/memory/' in path:
                rel_path = path.split('/memory/')[-1]
                suggestion = f'AppConfig.get_path("memory/{rel_path}")'
            elif '/temp/' in path or '/tmp/' in path:
                rel_path = path.split('/temp/')[-1] if '/temp/' in path else path.split('/tmp/')[-1]
                suggestion = f'AppConfig.get_path("temp/{rel_path}")'
            elif '/sessions/' in path:
                rel_path = path.split('/sessions/')[-1]
                suggestion = f'AppConfig.get_path("session/{rel_path}")'
            
            if suggestion:
                file_suggestions.append((path, suggestion))
        
        if file_suggestions:
            suggestions[file] = file_suggestions
    
    return suggestions

if __name__ == "__main__":
    # Use the current directory as the root
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find hardcoded paths
    results = find_hardcoded_paths(root_dir, "hardcoded_paths.json")
    
    # Print results
    print_results(results)
    
    # Generate suggestions
    suggestions = suggest_replacements(results)
    
    # Save suggestions
    with open("path_suggestions.json", 'w') as f:
        json.dump(suggestions, f, indent=2)
    
    print("\nSuggestions for replacements saved to path_suggestions.json")
