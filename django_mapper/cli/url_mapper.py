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
        
        if not root_urlconf:
            root_urlconf_path = self._find_root_urlconf()
        else:
            root_urlconf_path = self.project_path / root_urlconf.replace('.', '/') + '.py'
        
        if not root_urlconf_path:
            return []
        
        # Parse root URLconf
        self._parse_urlconf(root_urlconf_path, '')
        
        # Also scan for all urls.py files in the project
        for urls_file in self.project_path.rglob('*urls.py'):
            if 'site-packages' not in str(urls_file) and 'venv' not in str(urls_file):
                if urls_file != root_urlconf_path:
                    # Parse each urls.py
                    self._parse_urlconf(urls_file, '')
        
        # Post-process to deduplicate and add view types
        unique_patterns = {}
        for pattern in self.url_patterns:
            key = f"{pattern['pattern']}{pattern['view_name']}"
            if key not in unique_patterns:
                unique_patterns[key] = pattern
        
        return list(unique_patterns.values())
        
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
    
    def _parse_urlconf(self, urlconf_path: Path, prefix: str = '') -> None:
        """Enhanced URL parsing with DRF router support"""
        try:
            content = urlconf_path.read_text(encoding='utf-8')
            
            # Parse Django URL patterns
            self._parse_django_patterns(content, prefix)
            
            # Parse DRF Router patterns
            self._parse_drf_routers(content, prefix, urlconf_path)  # Pass urlconf_path here
            
        except Exception as e:
            print(f"Error parsing {urlconf_path}: {e}")
    
    def _parse_django_patterns(self, content: str, prefix: str) -> None:
        """Parse standard Django URL patterns"""
        
        # Find include patterns (these reference other URL files)
        include_pattern = r'path\([\'"]([^\'"]*)[\'"],\s*include\([\'"]([^\'"]+)[\'"]'
        include_matches = re.findall(include_pattern, content)
        
        for url_prefix, include_module in include_matches:
            # Find the included URLs file
            include_path = self.project_path
            for part in include_module.split('.'):
                include_path = include_path / part
            include_path = include_path.with_suffix('.py')
            
            if include_path.exists():
                self._parse_urlconf(include_path, prefix + url_prefix)
        
        # Find direct path patterns
        pattern_matches = re.finditer(r'path\([\'"]([^\'"]*)[\'"],\s*([^,\)]+)', content)
        
        for match in pattern_matches:
            url_pattern = match.group(1)
            view_ref = match.group(2).strip()
            
            # Skip include() patterns (already handled above)
            if 'include(' in view_ref:
                continue
            
            # Extract view name and determine type
            view_name = view_ref
            view_type = 'function'
            
            if '.as_view()' in view_ref:
                view_name = view_ref.replace('.as_view()', '')
                view_type = 'class'
            elif 'ViewSet' in view_ref:
                view_type = 'viewset'
            
            full_pattern = f"{prefix}{url_pattern}"
            
            self.url_patterns.append({
                'pattern': full_pattern,
                'view_name': view_name,
                'view_type': view_type,
                'name': self._extract_url_name(match.group(0)),
                'methods': ['GET', 'POST', 'PUT', 'DELETE'],  # Default for ViewSets
            })
    
    def _extract_url_name(self, pattern_str: str) -> str:
        """Extract URL name from pattern string"""
        name_match = re.search(r'name=[\'"]([^\'"]+)[\'"]', pattern_str)
        return name_match.group(1) if name_match else ''
    
    def _parse_drf_routers(self, content: str, prefix: str, url_file: Path) -> None:  # Change parameter name
        """Parse Django REST Framework router patterns"""
        
        # Find router creation
        router_pattern = r'(\w+)\s*=\s*DefaultRouter\(\)'
        routers = re.findall(router_pattern, content)
        
        for router_name in routers:
            # Find router registrations
            register_pattern = rf'{router_name}\.register\([\'"]([^\'"]+)[\'"],\s*(\w+)(?:,\s*basename=[\'"]([^\'"]+)[\'"])?\)'
            registrations = re.findall(register_pattern, content)
            
            for reg in registrations:
                url_prefix, viewset_name, basename = reg
                full_prefix = f"{prefix}{url_prefix}/"
                
                # Generate standard ViewSet URLs
                viewset_urls = [
                    {
                        'pattern': full_prefix,
                        'view_name': f"views.{viewset_name}",
                        'view_type': 'viewset',
                        'view_module': self._get_module_name(url_file),  # Use url_file instead
                        'name': f"{basename or url_prefix}-list" ,
                        'methods': ['GET', 'POST'],
                        'action': 'list/create'
                    },
                    {
                        'pattern': f"{full_prefix}{{id}}/",
                        'view_name': f"views.{viewset_name}",
                        'view_type': 'viewset',
                        'view_module': self._get_module_name(url_file),  # Use url_file instead
                        'name': f"{basename or url_prefix}-detail",
                        'methods': ['GET', 'PUT', 'PATCH', 'DELETE'],
                        'action': 'retrieve/update/delete'
                    }
                ]
                
                # Look for custom actions
                try:
                    # Try to find the ViewSet file to get custom actions
                    view_file = self._find_viewset_file(viewset_name, url_file)  # Use url_file instead
                    if view_file:
                        view_content = view_file.read_text(encoding='utf-8')
                        action_pattern = r'@action.*\n\s*def\s+(\w+)'
                        custom_actions = re.findall(action_pattern, view_content)
                        
                        for action_name in custom_actions:
                            viewset_urls.append({
                                'pattern': f"{full_prefix}{{id}}/{action_name}/",
                                'view_name': f"views.{viewset_name}",
                                'view_type': 'viewset',
                                'view_module': self._get_module_name(url_file),  # Use url_file instead
                                'name': f"{basename or url_prefix}-{action_name}",
                                'methods': ['GET', 'POST'],
                                'action': action_name
                            })
                except Exception as e:
                    print(f"Error parsing ViewSet {viewset_name}: {e}")
                    pass  # Continue without custom actions
                
                self.url_patterns.extend(viewset_urls)
    
    def _find_viewset_file(self, viewset_name: str, url_file: Path) -> Path:  # Change parameter name
        """Find the file containing the ViewSet"""
        # Look in the same directory first
        views_file = url_file.parent / 'views.py'  # Use url_file instead
        if views_file.exists():
            content = views_file.read_text(encoding='utf-8')
            if f'class {viewset_name}' in content:
                return views_file
        
        # Look for views directory
        views_dir = url_file.parent / 'views'  # Use url_file instead
        if views_dir.is_dir():
            for py_file in views_dir.glob('*.py'):
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if f'class {viewset_name}' in content:
                        return py_file
                except:
                    continue
        
        return None
        
    def _get_module_name(self, url_file: Path) -> str:  # Change parameter name
        """Get module name from file path"""
        try:
            # Convert file path to module path
            parts = url_file.parts  # Use url_file instead
            # Find where the Django project starts (look for manage.py)
            start_idx = 0
            for i, part in enumerate(parts):
                parent_dir = Path(*parts[:i+1])
                if (parent_dir / 'manage.py').exists():
                    start_idx = i
                    break
            
            module_parts = parts[start_idx:-1]  # Exclude filename
            return '.'.join(module_parts) if module_parts else 'root'
        except:
            return 'unknown'
    
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