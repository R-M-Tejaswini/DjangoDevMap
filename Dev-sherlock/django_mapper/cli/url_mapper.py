import ast
import re
from pathlib import Path
from typing import List, Dict

class URLMapper:
    """Extract and map URL patterns from Django URLconf"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.url_patterns = []
        
    def extract_urls(self, root_urlconf: str = None) -> List[Dict]:
        """Extract all URL patterns from the project"""
        
        # Find the root urls.py
        if not root_urlconf:
            root_urlconf = self._find_root_urlconf()
        
        if not root_urlconf:
            return []
        
        # Parse root urls.py
        self._parse_urlconf(root_urlconf, prefix='')
        
        return self.url_patterns
    
    def _find_root_urlconf(self) -> Path:
        """Find the root urls.py file"""
        
        # Look for urls.py in common locations
        candidates = list(self.project_path.rglob('urls.py'))
        
        # Filter to find the root one (usually in a directory with settings.py)
        for candidate in candidates:
            parent_dir = candidate.parent
            if (parent_dir / 'settings.py').exists() or (parent_dir / 'settings').exists():
                return candidate
        
        # Return first urls.py found as fallback
        return candidates[0] if candidates else None
    
    def _parse_urlconf(self, urlconf_path: Path, prefix: str):
        """Parse a URLs configuration file"""
        
        try:
            with open(urlconf_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
        except Exception as e:
            print(f"Error parsing {urlconf_path}: {e}")
            return
        
        # Look for urlpatterns variable
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'urlpatterns':
                        self._extract_patterns(node.value, prefix, urlconf_path.parent)
    
    def _extract_patterns(self, node, prefix: str, base_path: Path):
        """Extract URL patterns from urlpatterns list"""
        
        if not isinstance(node, ast.List):
            return
        
        for element in node.elts:
            if isinstance(element, ast.Call):
                func_name = self._get_function_name(element.func)
                
                if func_name in ('path', 're_path', 'url'):
                    self._extract_single_pattern(element, prefix, base_path)
                elif func_name == 'include':
                    self._extract_include_pattern(element, prefix, base_path)
    
    def _extract_single_pattern(self, call_node, prefix: str, base_path: Path):
        """Extract a single URL pattern"""
        
        if not call_node.args:
            return
        
        # Get the URL pattern
        pattern_node = call_node.args[0]
        pattern = self._extract_string_value(pattern_node)
        
        if not pattern:
            return
        
        full_pattern = prefix + pattern
        
        # Get the view
        view_info = self._extract_view_info(call_node, base_path)
        
        # Get name if provided
        name = None
        for keyword in call_node.keywords:
            if keyword.arg == 'name':
                name = self._extract_string_value(keyword.value)
        
        self.url_patterns.append({
            'pattern': full_pattern,
            'view_name': view_info.get('name'),
            'view_type': view_info.get('type'),
            'view_module': view_info.get('module'),
            'name': name,
            'methods': view_info.get('methods', []),
        })
    
    def _extract_include_pattern(self, call_node, prefix: str, base_path: Path):
        """Extract included URL patterns"""
        
        if not call_node.args:
            return
        
        # Get the prefix pattern
        pattern_node = call_node.args[0]
        pattern = self._extract_string_value(pattern_node)
        
        if not pattern:
            pattern = ''
        
        new_prefix = prefix + pattern
        
        # Get the included module
        if len(call_node.args) > 1:
            include_arg = call_node.args[1]
            included_module = self._extract_string_value(include_arg)
            
            if included_module:
                # Try to find the included urls.py
                included_path = self._resolve_include_path(included_module, base_path)
                if included_path:
                    self._parse_urlconf(included_path, new_prefix)
    
    def _extract_view_info(self, call_node, base_path: Path) -> Dict:
        """Extract information about the view function/class"""
        
        if len(call_node.args) < 2:
            return {}
        
        view_node = call_node.args[1]
        
        # Check if it's a direct function reference
        if isinstance(view_node, ast.Name):
            return {
                'name': view_node.id,
                'type': 'function',
                'module': None
            }
        
        # Check if it's an attribute (module.view)
        if isinstance(view_node, ast.Attribute):
            module = self._get_attribute_path(view_node.value)
            return {
                'name': f"{module}.{view_node.attr}",
                'type': 'function',
                'module': module
            }
        
        # Check if it's a .as_view() call (class-based view)
        if isinstance(view_node, ast.Call):
            if isinstance(view_node.func, ast.Attribute) and view_node.func.attr == 'as_view':
                view_class = self._get_attribute_path(view_node.func.value)
                return {
                    'name': view_class,
                    'type': 'class',
                    'module': None
                }
        
        return {}
    
    def _resolve_include_path(self, module_str: str, base_path: Path) -> Path:
        """Resolve included URL module to file path"""
        
        # Convert module path to file path
        parts = module_str.split('.')
        
        # Try relative to base_path first
        potential_path = base_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
        if potential_path.exists():
            return potential_path
        
        # Try from project root
        potential_path = self.project_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
        if potential_path.exists():
            return potential_path
        
        return None
    
    def _get_function_name(self, node) -> str:
        """Get function name from Call node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ''
    
    def _get_attribute_path(self, node) -> str:
        """Get full attribute path (e.g., views.MyView)"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_attribute_path(node.value)
            return f"{base}.{node.attr}"
        return ''
    
    def _extract_string_value(self, node) -> str:
        """Extract string value from AST node"""
        if isinstance(node, ast.Constant):
            return str(node.value) if node.value else ''
        elif isinstance(node, ast.Str):  # Python 3.7 compatibility
            return node.s
        return ''