import ast
from pathlib import Path
from typing import Dict, List

class ViewAnalyzer:
    """Analyze Django views and their dependencies"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        
    def analyze_views(self, url_patterns: List[Dict]) -> Dict:
        """Analyze all views referenced in URL patterns"""
        views = {}
        
        for url in url_patterns:
            view_name = url.get('view_name')
            if not view_name:
                continue
            
            # Find and analyze the view
            view_info = self._find_and_analyze_view(view_name, url.get('view_module'))
            if view_info:
                views[view_name] = view_info
        
        return views
    
    def _find_and_analyze_view(self, view_name: str, module_hint: str = None) -> Dict:
        """Find and analyze a specific view"""
        
        # Try to find the view file
        view_file = self._find_view_file(view_name, module_hint)
        
        if not view_file:
            return {
                'name': view_name,
                'found': False,
                'file': None
            }
        
        # Parse the view file
        try:
            with open(view_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
        except Exception as e:
            return {
                'name': view_name,
                'found': False,
                'error': str(e)
            }
        
        # Find the view definition
        view_node = self._find_view_definition(tree, view_name)
        
        if not view_node:
            return {
                'name': view_name,
                'found': False,
                'file': str(view_file)
            }
        
        # Analyze the view
        return self._analyze_view_node(view_node, view_file, tree)
    
    def _find_view_file(self, view_name: str, module_hint: str = None) -> Path:
        """Find the file containing the view"""
        
        # Extract just the view name if it includes module path
        if '.' in view_name:
            parts = view_name.split('.')
            view_name = parts[-1]
            if not module_hint:
                module_hint = '.'.join(parts[:-1])
        
        # Search for views.py files
        for views_file in self.project_path.rglob('views.py'):
            # Skip if in venv or site-packages
            if 'site-packages' in str(views_file) or 'venv' in str(views_file):
                continue
            
            # Check if view is in this file
            if self._view_in_file(views_file, view_name):
                return views_file
        
        # Also check views/ directories
        for views_dir in self.project_path.rglob('views'):
            if views_dir.is_dir():
                for py_file in views_dir.glob('*.py'):
                    if self._view_in_file(py_file, view_name):
                        return py_file
        
        return None
    
    def _view_in_file(self, file_path: Path, view_name: str) -> bool:
        """Check if a view is defined in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
        except:
            return False
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if node.name == view_name:
                    return True
        
        return False
    
    def _find_view_definition(self, tree, view_name: str):
        """Find the view definition in AST"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if node.name == view_name:
                    return node
        return None
    
    def _analyze_view_node(self, view_node, view_file: Path, tree) -> Dict:
        """Analyze a view function or class"""
        
        is_class = isinstance(view_node, ast.ClassDef)
        
        view_info = {
            'name': view_node.name,
            'found': True,
            'file': str(view_file.relative_to(self.project_path)),
            'type': 'class' if is_class else 'function',
            'line_number': view_node.lineno,
            'models_used': [],
            'forms_used': [],
            'serializers_used': [],
            'decorators': [],
            'imports': self._extract_imports(tree),
        }
        
        # Extract decorators
        if hasattr(view_node, 'decorator_list'):
            for decorator in view_node.decorator_list:
                dec_name = self._get_decorator_name(decorator)
                view_info['decorators'].append(dec_name)
        
        # Analyze view body
        if is_class:
            view_info.update(self._analyze_class_view(view_node))
        else:
            view_info.update(self._analyze_function_view(view_node))
        
        # Detect models, forms, serializers used
        view_info['models_used'] = self._detect_models_used(view_node)
        view_info['forms_used'] = self._detect_forms_used(view_node)
        view_info['serializers_used'] = self._detect_serializers_used(view_node)
        
        return view_info
    
    def _analyze_function_view(self, func_node: ast.FunctionDef) -> Dict:
        """Analyze a function-based view"""
        
        info = {
            'parameters': [arg.arg for arg in func_node.args.args],
            'returns_response': self._checks_for_response(func_node),
        }
        
        return info
    
    def _analyze_class_view(self, class_node: ast.ClassDef) -> Dict:
        """Analyze a class-based view"""
        
        methods = []
        http_methods = []
        
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
                
                # Track HTTP methods
                if item.name in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options'):
                    http_methods.append(item.name.upper())
        
        return {
            'methods': methods,
            'http_methods': http_methods,
            'base_classes': [self._get_base_name(base) for base in class_node.bases],
        }
    
    def _detect_models_used(self, node) -> List[str]:
        """Detect which models are used in the view"""
        models = set()
        
        for child in ast.walk(node):
            # Look for Model.objects patterns
            if isinstance(child, ast.Attribute):
                if child.attr == 'objects':
                    if isinstance(child.value, ast.Name):
                        models.add(child.value.id)
            
            # Look for get_object_or_404, get_list_or_404
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)
                if 'get_object_or_404' in func_name or 'get_list_or_404' in func_name:
                    if child.args and isinstance(child.args[0], ast.Name):
                        models.add(child.args[0].id)
        
        return list(models)
    
    def _detect_forms_used(self, node) -> List[str]:
        """Detect which forms are used in the view"""
        forms = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)
                if 'Form' in func_name and func_name not in ('Form', 'forms.Form'):
                    forms.add(func_name)
        
        return list(forms)
    
    def _detect_serializers_used(self, node) -> List[str]:
        """Detect which serializers are used (for DRF)"""
        serializers = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)
                if 'Serializer' in func_name:
                    serializers.add(func_name)
        
        return list(serializers)
    
    def _extract_imports(self, tree) -> List[Dict]:
        """Extract import statements"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'alias': alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        'module': f"{node.module}.{alias.name}" if node.module else alias.name,
                        'alias': alias.asname
                    })
        
        return imports
    
    def _checks_for_response(self, func_node) -> bool:
        """Check if function returns a response"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Return) and node.value:
                return True
        return False
    
    def _get_decorator_name(self, decorator) -> str:
        """Get decorator name"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_call_name(decorator)
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_base_name(decorator.value)}.{decorator.attr}"
        return str(decorator)
    
    def _get_base_name(self, node) -> str:
        """Get base class or attribute name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_base_name(node.value)
            return f"{base}.{node.attr}"
        return ''
    
    def _get_call_name(self, call_node) -> str:
        """Get function call name"""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return f"{self._get_base_name(call_node.func.value)}.{call_node.func.attr}"
        return ''