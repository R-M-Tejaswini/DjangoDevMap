import ast
from pathlib import Path
from typing import Dict, List

class ModelTracker:
    """Track Django models in the project"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        
    def find_models(self) -> Dict:
        """Find all Django models in the project"""
        models = {}
        
        # Find all models.py files (exclude site-packages and virtualenv)
        for models_file in self.project_path.rglob('models.py'):
            # Skip if in venv or site-packages
            if 'site-packages' in str(models_file) or 'venv' in str(models_file):
                continue
            
            file_models = self._parse_models_file(models_file)
            models.update(file_models)
        
        # Also check for models/ directories
        for models_dir in self.project_path.rglob('models'):
            if models_dir.is_dir() and (models_dir / '__init__.py').exists():
                for py_file in models_dir.glob('*.py'):
                    if py_file.name != '__init__.py':
                        file_models = self._parse_models_file(py_file)
                        models.update(file_models)
        
        return models
    
    def _parse_models_file(self, file_path: Path) -> Dict:
        """Parse a models file and extract model definitions"""
        models = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return models
        
        # Find all class definitions that inherit from models.Model
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_model_class(node):
                    model_info = self._extract_model_info(node, file_path)
                    models[model_info['name']] = model_info
        
        return models
    
    def _is_model_class(self, class_node: ast.ClassDef) -> bool:
        """Check if a class is a Django model"""
        for base in class_node.bases:
            base_name = self._get_base_class_name(base)
            if 'Model' in base_name or 'models.Model' in base_name:
                return True
        return False
    
    def _extract_model_info(self, class_node: ast.ClassDef, file_path: Path) -> Dict:
        """Extract detailed information about a model"""
        
        fields = []
        methods = []
        relationships = []
        meta_info = {}
        
        for item in class_node.body:
            # Extract fields
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        field_info = self._extract_field_info(target.id, item.value)
                        if field_info:
                            fields.append(field_info)
                            
                            # Track relationships
                            if field_info['type'] in ('ForeignKey', 'OneToOneField', 'ManyToManyField'):
                                relationships.append({
                                    'field': field_info['name'],
                                    'type': field_info['type'],
                                    'related_model': field_info.get('related_model')
                                })
            
            # Extract methods
            elif isinstance(item, ast.FunctionDef):
                if not item.name.startswith('_') or item.name in ('__str__', '__repr__'):
                    methods.append(item.name)
            
            # Extract Meta class
            elif isinstance(item, ast.ClassDef) and item.name == 'Meta':
                meta_info = self._extract_meta_info(item)
        
        return {
            'name': class_node.name,
            'file': str(file_path.relative_to(self.project_path)),
            'app': self._get_app_name(file_path),
            'fields': fields,
            'methods': methods,
            'relationships': relationships,
            'meta': meta_info
        }
    
    def _extract_field_info(self, field_name: str, value_node) -> Dict:
        """Extract field information from assignment"""
        
        if not isinstance(value_node, ast.Call):
            return None
        
        field_type = self._get_field_type(value_node.func)
        
        if not field_type:
            return None
        
        field_info = {
            'name': field_name,
            'type': field_type,
            'options': {}
        }
        
        # Extract field options
        for keyword in value_node.keywords:
            if keyword.arg:
                field_info['options'][keyword.arg] = self._extract_value(keyword.value)
        
        # For relationship fields, extract related model
        if field_type in ('ForeignKey', 'OneToOneField', 'ManyToManyField') and value_node.args:
            related_model = self._extract_value(value_node.args[0])
            field_info['related_model'] = related_model
        
        return field_info
    
    def _get_field_type(self, node) -> str:
        """Get the field type from the call node"""
        if isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Name):
            return node.id
        return ''
    
    def _extract_meta_info(self, meta_class: ast.ClassDef) -> Dict:
        """Extract Meta class information"""
        meta = {}
        
        for item in meta_class.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        meta[target.id] = self._extract_value(item.value)
        
        return meta
    
    def _get_base_class_name(self, node) -> str:
        """Get base class name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_base_class_name(node.value)
            return f"{base}.{node.attr}"
        return ''
    
    def _get_app_name(self, file_path: Path) -> str:
        """Get the app name from file path"""
        # Walk up to find apps.py
        current = file_path.parent
        while current != self.project_path:
            if (current / 'apps.py').exists():
                return current.name
            current = current.parent
        return 'unknown'
    
    def _extract_value(self, node):
        """Extract value from AST node"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self._extract_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self._extract_value(elt) for elt in node.elts)
        return str(node)