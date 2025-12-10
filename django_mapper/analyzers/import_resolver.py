from pathlib import Path
from typing import Dict, List, Set, Optional
import os

class ImportResolver:
    """Resolve imports and track dependencies between modules"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.module_map = {}  # Map of module names to file paths
        self.dependency_graph = {}  # Map of files to their dependencies
        
    def build_module_map(self):
        """Build a map of all Python modules in the project"""
        for py_file in self.project_path.rglob('*.py'):
            if self._is_project_file(py_file):
                module_name = self._file_to_module(py_file)
                self.module_map[module_name] = py_file
    
    def resolve_imports(self, file_path: Path, imports: List[Dict]) -> Dict:
        """Resolve where imports come from"""
        resolved = {
            'internal': [],  # Imports from project
            'external': [],  # Imports from packages
            'dependencies': []  # List of project files this depends on
        }
        
        for imp in imports:
            resolution = self._resolve_import(file_path, imp)
            
            if resolution['source'] == 'internal':
                resolved['internal'].append(resolution)
                if resolution['file_path']:
                    resolved['dependencies'].append(resolution['file_path'])
            else:
                resolved['external'].append(resolution)
        
        return resolved
    
    def _resolve_import(self, current_file: Path, import_info: Dict) -> Dict:
        """Resolve a single import statement"""
        
        if import_info['type'] == 'import':
            module = import_info['module']
        else:  # from_import
            module = import_info['module']
            name = import_info['name']
        
        # Check if it's a relative import
        if module and module.startswith('.'):
            return self._resolve_relative_import(current_file, import_info)
        
        # Check if it's an internal project module
        resolved_path = self._find_module_path(module)
        
        if resolved_path:
            return {
                'source': 'internal',
                'module': module,
                'file_path': str(resolved_path.relative_to(self.project_path)),
                'import_info': import_info
            }
        else:
            return {
                'source': 'external',
                'module': module,
                'file_path': None,
                'import_info': import_info,
                'package': self._extract_package_name(module)
            }
    
    def _resolve_relative_import(self, current_file: Path, import_info: Dict) -> Dict:
        """Resolve relative imports (from . import x, from .. import y)"""
        
        module = import_info['module']
        current_dir = current_file.parent
        
        # Count levels up
        level = 0
        while module and module[0] == '.':
            level += 1
            module = module[1:]
        
        # Go up the directory tree
        target_dir = current_dir
        for _ in range(level - 1):
            target_dir = target_dir.parent
        
        # Build the target module path
        if module:
            module_parts = module.split('.')
            for part in module_parts:
                target_dir = target_dir / part
        
        # Try to find the file
        possible_paths = [
            target_dir / '__init__.py',
            target_dir.with_suffix('.py'),
        ]
        
        for path in possible_paths:
            if path.exists() and self._is_project_file(path):
                return {
                    'source': 'internal',
                    'module': module or '.',
                    'file_path': str(path.relative_to(self.project_path)),
                    'import_info': import_info,
                    'relative': True
                }
        
        return {
            'source': 'internal',
            'module': module or '.',
            'file_path': None,
            'import_info': import_info,
            'relative': True,
            'unresolved': True
        }
    
    def _find_module_path(self, module_name: str) -> Optional[Path]:
        """Find the file path for a module"""
        
        # Direct lookup
        if module_name in self.module_map:
            return self.module_map[module_name]
        
        # Try to construct path
        parts = module_name.split('.')
        
        # Try as package
        package_path = self.project_path / '/'.join(parts) / '__init__.py'
        if package_path.exists() and self._is_project_file(package_path):
            return package_path
        
        # Try as module
        module_path = self.project_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
        if module_path.exists() and self._is_project_file(module_path):
            return module_path
        
        return None
    
    def _file_to_module(self, file_path: Path) -> str:
        """Convert file path to module name"""
        try:
            rel_path = file_path.relative_to(self.project_path)
        except ValueError:
            return ''
        
        # Remove .py extension
        if rel_path.name == '__init__.py':
            parts = rel_path.parent.parts
        else:
            parts = rel_path.with_suffix('').parts
        
        return '.'.join(parts)
    
    def _extract_package_name(self, module: str) -> str:
        """Extract the top-level package name"""
        if not module:
            return 'unknown'
        return module.split('.')[0]
    
    def _is_project_file(self, file_path: Path) -> bool:
        """Check if file is part of the actual project"""
        
        file_str = str(file_path)
        
        # Exclude patterns
        exclude_patterns = [
            'site-packages',
            'venv',
            'env',
            '.venv',
            'virtualenv',
            'migrations',
            '__pycache__',
            '.git',
        ]
        
        for pattern in exclude_patterns:
            if pattern in file_str:
                return False
        
        try:
            file_path.relative_to(self.project_path)
            return True
        except ValueError:
            return False
    
    def build_dependency_graph(self, all_files: Dict[str, Dict]) -> Dict:
        """Build a dependency graph for all files"""
        
        graph = {}
        
        for file_path, file_info in all_files.items():
            dependencies = []
            
            # Get internal imports
            imports = file_info.get('imports', [])
            for imp in imports:
                resolved = self._resolve_import(
                    self.project_path / file_path,
                    imp
                )
                
                if resolved['source'] == 'internal' and resolved['file_path']:
                    dependencies.append(resolved['file_path'])
            
            graph[file_path] = {
                'depends_on': list(set(dependencies)),
                'external_packages': self._get_external_packages(file_info)
            }
        
        # Add reverse dependencies (what depends on this file)
        for file_path, deps in graph.items():
            deps['dependents'] = []
        
        for file_path, deps in graph.items():
            for dependency in deps['depends_on']:
                if dependency in graph:
                    graph[dependency]['dependents'].append(file_path)
        
        return graph
    
    def _get_external_packages(self, file_info: Dict) -> List[str]:
        """Get list of external packages used"""
        packages = set()
        
        for imp in file_info.get('imports', []):
            module = imp.get('module', '')
            if module:
                # Check if it's a known external package
                if self._is_external_package(module):
                    packages.add(self._extract_package_name(module))
        
        return list(packages)
    
    def _is_external_package(self, module: str) -> bool:
        """Check if module is an external package"""
        
        # Common Django/Python packages
        known_packages = [
            'django', 'rest_framework', 'celery', 'redis',
            'requests', 'numpy', 'pandas', 'pytest',
            'selenium', 'bs4', 'scrapy', 'flask'
        ]
        
        base_module = module.split('.')[0]
        
        # Check if it's a known package
        if base_module in known_packages:
            return True
        
        # Check if it's not in our project
        if not self._find_module_path(module):
            return True
        
        return False
    
    def find_circular_dependencies(self, dependency_graph: Dict) -> List[List[str]]:
        """Find circular dependencies in the project"""
        
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependency_graph.get(node, {}).get('depends_on', []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)
            
            rec_stack.remove(node)
        
        for node in dependency_graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def get_dependency_tree(self, file_path: str, dependency_graph: Dict, max_depth: int = 3) -> Dict:
        """Get dependency tree for a specific file"""
        
        def build_tree(node, depth, visited):
            if depth > max_depth or node in visited:
                return None
            
            visited.add(node)
            
            deps = dependency_graph.get(node, {}).get('depends_on', [])
            
            return {
                'file': node,
                'dependencies': [
                    build_tree(dep, depth + 1, visited.copy())
                    for dep in deps
                    if build_tree(dep, depth + 1, visited.copy()) is not None
                ]
            }
        
        return build_tree(file_path, 0, set())