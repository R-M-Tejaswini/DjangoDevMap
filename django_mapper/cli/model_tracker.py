import ast
import re
from pathlib import Path
from typing import Dict, List

class ModelTracker:
    """Track Django models in the project"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        
    def find_models(self) -> Dict:
        """Find all Django models in the project"""
        models = {}
        
        # Find all models.py files
        for models_file in self.project_path.rglob('models.py'):
            if 'site-packages' in str(models_file) or 'venv' in str(models_file):
                continue
            
            file_models = self._parse_models_file(models_file)
            models.update(file_models)
        
        # Also check for models/ directories
        for models_dir in self.project_path.rglob('models'):
            if models_dir.is_dir() and (models_dir / '__init__.py').exists():
                # Check __init__.py for imports
                init_file = models_dir / '__init__.py'
                if init_file.exists():
                    file_models = self._parse_models_file(init_file)
                    models.update(file_models)
                
                # Parse individual model files
                for py_file in models_dir.glob('*.py'):
                    if py_file.name != '__init__.py':
                        file_models = self._parse_models_file(py_file)
                        models.update(file_models)
        
        return models
    
    def _parse_models_file(self, models_file: Path) -> Dict:
        """Enhanced model parsing with better relationship detection"""
        models = {}
        
        try:
            content = models_file.read_text(encoding='utf-8')
            
            # Find all model classes
            class_pattern = r'class\s+(\w+)\s*\([^)]*Model[^)]*\):'
            model_classes = re.finditer(class_pattern, content)
            
            for match in model_classes:
                model_name = match.group(1)
                if model_name == 'Meta':  # Skip Meta classes
                    continue
                    
                model_info = self._parse_single_model(content, model_name, models_file)
                if model_info:
                    models[model_name] = model_info
                    
        except Exception as e:
            print(f"Error parsing models file {models_file}: {e}")
        
        return models
    
    def _parse_single_model(self, content: str, model_name: str, file_path: Path) -> Dict:
        """Parse a single model class with enhanced field and relationship detection"""
        
        # Extract the model class content
        class_start = content.find(f'class {model_name}')
        if class_start == -1:
            return None
            
        # Find the end of the class (next class or end of file)
        next_class = content.find('\nclass ', class_start + 1)
        if next_class == -1:
            class_content = content[class_start:]
        else:
            class_content = content[class_start:next_class]
        
        model_info = {
            'name': model_name,
            'file': str(file_path.relative_to(self.project_path)),
            'app': self._get_app_name(file_path),
            'fields': [],
            'methods': [],
            'relationships': [],
            'meta': {}
        }
        
        # Parse fields
        field_patterns = [
            r'(\w+)\s*=\s*models\.(\w+)\s*\([^)]*\)',  # Standard fields
            r'(\w+)\s*=\s*models\.(\w+)\s*\(\s*([^)]+)\)',  # Fields with options
        ]
        
        for pattern in field_patterns:
            fields = re.finditer(pattern, class_content)
            for field_match in fields:
                field_name = field_match.group(1)
                field_type = field_match.group(2)
                
                field_info = {
                    'name': field_name,
                    'type': field_type,
                    'options': {}
                }
                
                # Parse field options if present
                if len(field_match.groups()) > 2:
                    options_str = field_match.group(3)
                    field_info['options'] = self._parse_field_options(options_str)
                
                # Check for relationships
                if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                    related_model = self._extract_related_model(field_match.group(0))
                    if related_model:
                        field_info['related_model'] = related_model
                        model_info['relationships'].append({
                            'field': field_name,
                            'type': field_type,
                            'related_model': related_model
                        })
                
                model_info['fields'].append(field_info)
        
        # Parse methods
        method_pattern = r'def\s+(\w+)\s*\(self[^)]*\):'
        methods = re.findall(method_pattern, class_content)
        model_info['methods'] = [m for m in methods if not m.startswith('_') or m in ['__str__', '__unicode__']]
        
        # Parse Meta class
        meta_match = re.search(r'class Meta:(.*?)(?=\n    def|\n    \w+\s*=|\nclass|\Z)', class_content, re.DOTALL)
        if meta_match:
            meta_content = meta_match.group(1)
            model_info['meta'] = self._parse_meta_class(meta_content)
        
        return model_info
        
    def _extract_related_model(self, field_declaration: str) -> str:
        """Extract related model from field declaration"""
        # Look for quoted model names
        quoted_model = re.search(r'[\'"](\w+)[\'"]', field_declaration)
        if quoted_model:
            return quoted_model.group(1)
            
        # Look for direct model references
        model_ref = re.search(r'models\.\w+\s*\(\s*(\w+)', field_declaration)
        if model_ref:
            return model_ref.group(1)
            
        return None
        
    def _parse_field_options(self, options_str: str) -> Dict:
        """Parse field options from string"""
        options = {}
        
        # Common option patterns
        option_patterns = [
            (r'max_length\s*=\s*(\d+)', 'max_length', int),
            (r'null\s*=\s*(True|False)', 'null', lambda x: x == 'True'),
            (r'blank\s*=\s*(True|False)', 'blank', lambda x: x == 'True'),
            (r'unique\s*=\s*(True|False)', 'unique', lambda x: x == 'True'),
            (r'db_index\s*=\s*(True|False)', 'db_index', lambda x: x == 'True'),
            (r'default\s*=\s*([^,\)]+)', 'default', str),
            (r'help_text\s*=\s*[\'"]([^\'"]+)[\'"]', 'help_text', str),
        ]
        
        for pattern, key, converter in option_patterns:
            match = re.search(pattern, options_str)
            if match:
                try:
                    options[key] = converter(match.group(1).strip())
                except:
                    options[key] = match.group(1).strip()
        
        return options

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