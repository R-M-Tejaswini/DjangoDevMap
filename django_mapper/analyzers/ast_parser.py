import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

class ASTParser:
    """Parse Python files using AST to extract detailed code structure"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        
    def parse_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a Python file and extract all relevant information"""
        
        # Skip if not a project file
        if not self._is_project_file(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
        
        return {
            'file_path': str(file_path.relative_to(self.project_path)),
            'classes': self._extract_classes(tree),
            'functions': self._extract_functions(tree),
            'imports': self._extract_imports(tree),
            'constants': self._extract_constants(tree),
            'decorators': self._extract_decorators(tree),
        }
    
    def _is_project_file(self, file_path: Path) -> bool:
        """Check if file is part of the actual project (not third-party)"""
        
        file_str = str(file_path)
        
        # Exclude patterns
        exclude_patterns = [
            'site-packages',
            'venv',
            'env',
            '.venv',
            'virtualenv',
            'migrations',  # Django migrations
            '__pycache__',
            '.git',
            'node_modules',
        ]
        
        for pattern in exclude_patterns:
            if pattern in file_str:
                return False
        
        # Must be within project path
        try:
            file_path.relative_to(self.project_path)
            return True
        except ValueError:
            return False
    
    def _extract_classes(self, tree) -> List[Dict]:
        """Extract all class definitions with detailed information"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'line_number': node.lineno,
                    'end_line': node.end_lineno,
                    'docstring': ast.get_docstring(node),
                    'base_classes': [self._get_node_name(base) for base in node.bases],
                    'decorators': [self._get_node_name(dec) for dec in node.decorator_list],
                    'methods': self._extract_class_methods(node),
                    'class_variables': self._extract_class_variables(node),
                    'is_abstract': self._is_abstract_class(node),
                    'is_django_model': self._is_django_model(node),
                    'is_django_view': self._is_django_view(node),
                    'is_rest_framework': self._is_rest_framework_class(node),
                }
                classes.append(class_info)
        
        return classes
    
    def _extract_class_methods(self, class_node: ast.ClassDef) -> List[Dict]:
        """Extract all methods from a class"""
        methods = []
        
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = {
                    'name': item.name,
                    'line_number': item.lineno,
                    'docstring': ast.get_docstring(item),
                    'parameters': self._extract_parameters(item),
                    'decorators': [self._get_node_name(dec) for dec in item.decorator_list],
                    'return_type': self._extract_return_type(item),
                    'is_property': self._is_property(item),
                    'is_classmethod': self._is_classmethod(item),
                    'is_staticmethod': self._is_staticmethod(item),
                    'calls_super': self._calls_super(item),
                    'http_method': self._get_http_method(item),
                }
                methods.append(method_info)
        
        return methods
    
    def _extract_class_variables(self, class_node: ast.ClassDef) -> List[Dict]:
        """Extract class-level variables"""
        variables = []
        
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        variables.append({
                            'name': target.id,
                            'line_number': item.lineno,
                            'value': self._get_value_repr(item.value),
                        })
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                variables.append({
                    'name': item.target.id,
                    'line_number': item.lineno,
                    'annotation': self._get_node_name(item.annotation),
                    'value': self._get_value_repr(item.value) if item.value else None,
                })
        
        return variables
    
    def _extract_functions(self, tree) -> List[Dict]:
        """Extract all top-level functions"""
        functions = []
        
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_info = {
                    'name': node.name,
                    'line_number': node.lineno,
                    'end_line': node.end_lineno,
                    'docstring': ast.get_docstring(node),
                    'parameters': self._extract_parameters(node),
                    'decorators': [self._get_node_name(dec) for dec in node.decorator_list],
                    'return_type': self._extract_return_type(node),
                    'calls': self._extract_function_calls(node),
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'is_view': self._is_view_function(node),
                }
                functions.append(func_info)
        
        return functions
    
    def _extract_imports(self, tree) -> List[Dict]:
        """Extract all import statements"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line_number': node.lineno,
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        'type': 'from_import',
                        'module': node.module or '',
                        'name': alias.name,
                        'alias': alias.asname,
                        'line_number': node.lineno,
                    })
        
        return imports
    
    def _extract_constants(self, tree) -> List[Dict]:
        """Extract module-level constants"""
        constants = []
        
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants.append({
                            'name': target.id,
                            'value': self._get_value_repr(node.value),
                            'line_number': node.lineno,
                        })
        
        return constants
    
    def _extract_decorators(self, tree) -> Set[str]:
        """Extract all unique decorators used in the file"""
        decorators = set()
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                for dec in node.decorator_list:
                    decorators.add(self._get_node_name(dec))
        
        return list(decorators)
    
    def _extract_parameters(self, func_node) -> List[Dict]:
        """Extract function parameters with details"""
        params = []
        
        for arg in func_node.args.args:
            param = {
                'name': arg.arg,
                'annotation': self._get_node_name(arg.annotation) if arg.annotation else None,
            }
            params.append(param)
        
        return params
    
    def _extract_return_type(self, func_node) -> Optional[str]:
        """Extract return type annotation"""
        if func_node.returns:
            return self._get_node_name(func_node.returns)
        return None
    
    def _extract_function_calls(self, func_node) -> List[Dict]:
        """Extract all function calls within a function"""
        calls = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_name = self._get_node_name(node.func)
                if call_name:
                    calls.append({
                        'name': call_name,
                        'line_number': node.lineno,
                    })
        
        return calls
    
    def _get_node_name(self, node) -> str:
        """Get the name/string representation of an AST node"""
        if node is None:
            return ''
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_node_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        elif isinstance(node, ast.Call):
            return self._get_node_name(node.func)
        elif isinstance(node, ast.Subscript):
            return self._get_node_name(node.value)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Str):
            return node.s
        return ''
    
    def _get_value_repr(self, node) -> str:
        """Get a string representation of a value"""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Str):
            return repr(node.s)
        elif isinstance(node, ast.Num):
            return str(node.n)
        elif isinstance(node, ast.List):
            return '[...]'
        elif isinstance(node, ast.Dict):
            return '{...}'
        elif isinstance(node, ast.Name):
            return node.id
        return '...'
    
    def _is_property(self, func_node) -> bool:
        """Check if method is a property"""
        return any(self._get_node_name(dec) == 'property' for dec in func_node.decorator_list)
    
    def _is_classmethod(self, func_node) -> bool:
        """Check if method is a classmethod"""
        return any(self._get_node_name(dec) == 'classmethod' for dec in func_node.decorator_list)
    
    def _is_staticmethod(self, func_node) -> bool:
        """Check if method is a staticmethod"""
        return any(self._get_node_name(dec) == 'staticmethod' for dec in func_node.decorator_list)
    
    def _calls_super(self, func_node) -> bool:
        """Check if method calls super()"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'super':
                    return True
        return False
    
    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class is abstract"""
        for base in class_node.bases:
            base_name = self._get_node_name(base)
            if 'ABC' in base_name or 'Abstract' in base_name:
                return True
        return False
    
    def _is_django_model(self, class_node: ast.ClassDef) -> bool:
        """Check if class is a Django model"""
        for base in class_node.bases:
            base_name = self._get_node_name(base)
            if 'Model' in base_name or 'models.Model' in base_name:
                return True
        return False
    
    def _is_django_view(self, class_node: ast.ClassDef) -> bool:
        """Check if class is a Django view"""
        for base in class_node.bases:
            base_name = self._get_node_name(base)
            if 'View' in base_name:
                return True
        return False
    
    def _is_rest_framework_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class is a DRF ViewSet/Serializer"""
        for base in class_node.bases:
            base_name = self._get_node_name(base)
            if any(keyword in base_name for keyword in ['ViewSet', 'Serializer', 'APIView']):
                return True
        return False
    
    def _is_view_function(self, func_node: ast.FunctionDef) -> bool:
        """Check if function is likely a Django view"""
        # Check parameters
        if func_node.args.args and func_node.args.args[0].arg == 'request':
            return True
        
        # Check decorators
        view_decorators = ['login_required', 'require_http_methods', 'require_GET', 'require_POST']
        for dec in func_node.decorator_list:
            dec_name = self._get_node_name(dec)
            if any(vd in dec_name for vd in view_decorators):
                return True
        
        return False
    
    def _get_http_method(self, func_node: ast.FunctionDef) -> Optional[str]:
        """Get HTTP method for class-based view methods"""
        method_name = func_node.name.lower()
        if method_name in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
            return method_name.upper()
        return None