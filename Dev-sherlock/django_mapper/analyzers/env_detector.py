import re
from pathlib import Path
from typing import List, Dict, Set

class EnvDetector:
    """Detect required environment variables in Django project"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.env_vars = set()
        
    def detect(self) -> List[Dict]:
        """Detect all environment variables used in the project"""
        
        # Scan settings files
        self._scan_settings_files()
        
        # Scan .env.example if it exists
        self._scan_env_example()
        
        # Scan Python files for os.environ usage
        self._scan_python_files()
        
        return self._format_env_vars()
    
    def _scan_settings_files(self):
        """Scan Django settings files for env var usage"""
        
        for settings_file in self.project_path.rglob('settings*.py'):
            if 'site-packages' in str(settings_file) or 'venv' in str(settings_file):
                continue
            
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Look for os.environ, os.getenv patterns
                self._extract_env_vars_from_code(content, settings_file)
                    
            except Exception as e:
                print(f"Error reading {settings_file}: {e}")
    
    def _scan_env_example(self):
        """Scan .env.example file if it exists"""
        env_example_files = [
            '.env.example',
            '.env.sample',
            'env.example',
        ]
        
        for filename in env_example_files:
            env_file = self.project_path / filename
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                if '=' in line:
                                    var_name = line.split('=')[0].strip()
                                    self.env_vars.add(var_name)
                except Exception as e:
                    print(f"Error reading {env_file}: {e}")
    
    def _scan_python_files(self):
        """Scan all Python files for environment variable usage"""
        
        for py_file in self.project_path.rglob('*.py'):
            if 'site-packages' in str(py_file) or 'venv' in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._extract_env_vars_from_code(content, py_file)
            except Exception as e:
                pass  # Skip files that can't be read
    
    def _extract_env_vars_from_code(self, content: str, file_path: Path):
        """Extract environment variable names from code"""
        
        # Pattern 1: os.environ['VAR_NAME']
        pattern1 = r"os\.environ\[(['\"])([A-Z_][A-Z0-9_]*)\\1\]"
        
        # Pattern 2: os.environ.get('VAR_NAME')
        pattern2 = r"os\.environ\.get\((['\"])([A-Z_][A-Z0-9_]*)\\1"
        
        # Pattern 3: os.getenv('VAR_NAME')
        pattern3 = r"os\.getenv\((['\"])([A-Z_][A-Z0-9_]*)\\1"
        
        # Pattern 4: config('VAR_NAME') - for python-decouple
        pattern4 = r"config\((['\"])([A-Z_][A-Z0-9_]*)\\1"
        
        patterns = [pattern1, pattern2, pattern3, pattern4]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                var_name = match.group(2)
                self.env_vars.add(var_name)
    
    def _format_env_vars(self) -> List[Dict]:
        """Format environment variables with categorization"""
        
        categorized = []
        
        for var in sorted(self.env_vars):
            category = self._categorize_var(var)
            categorized.append({
                'name': var,
                'category': category,
                'required': self._is_likely_required(var),
            })
        
        return categorized
    
    def _categorize_var(self, var_name: str) -> str:
        """Categorize environment variable by name"""
        
        var_lower = var_name.lower()
        
        if 'secret' in var_lower or 'key' in var_lower:
            return 'security'
        elif 'db' in var_lower or 'database' in var_lower:
            return 'database'
        elif 'email' in var_lower or 'mail' in var_lower:
            return 'email'
        elif 'redis' in var_lower or 'cache' in var_lower:
            return 'cache'
        elif 'aws' in var_lower or 's3' in var_lower:
            return 'storage'
        elif 'debug' in var_lower or 'env' in var_lower:
            return 'environment'
        elif 'api' in var_lower:
            return 'api'
        else:
            return 'other'
    
    def _is_likely_required(self, var_name: str) -> bool:
        """Determine if a variable is likely required"""
        
        required_patterns = [
            'SECRET_KEY',
            'DATABASE',
            'DB_',
        ]
        
        for pattern in required_patterns:
            if pattern in var_name:
                return True
        
        return False