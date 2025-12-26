from pathlib import Path
from typing import List, Dict, Set, Optional
import hashlib
import re

def sanitize_identifier(text: str) -> str:
    """Sanitize text for use as an identifier"""
    # Replace special characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', text)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'n_' + sanitized
    return sanitized or 'node'

def shorten_path(file_path: str, max_length: int = 50) -> str:
    """Shorten a file path for display"""
    if len(file_path) <= max_length:
        return file_path
    
    parts = file_path.split('/')
    if len(parts) <= 2:
        return file_path
    
    # Keep first and last parts, abbreviate middle
    return f"{parts[0]}/.../{parts[-1]}"

def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def get_file_hash(file_path: Path) -> str:
    """Get MD5 hash of a file"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ''

def is_django_project(path: Path) -> bool:
    """Check if directory contains a Django project"""
    indicators = [
        path / 'manage.py',
        path / 'wsgi.py',
        path / 'settings.py',
    ]
    
    # Check direct indicators
    for indicator in indicators:
        if indicator.exists():
            return True
    
    # Check for settings directory
    for item in path.iterdir():
        if item.is_dir():
            if (item / 'settings.py').exists() or (item / 'settings').is_dir():
                return True
    
    return False

def find_django_settings(project_path: Path) -> Optional[Path]:
    """Find the Django settings file"""
    
    # Common locations
    candidates = [
        project_path / 'settings.py',
        project_path / 'settings' / '__init__.py',
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    # Search in subdirectories
    for settings_file in project_path.rglob('settings.py'):
        # Skip migrations, tests, etc.
        if 'migrations' not in str(settings_file) and 'tests' not in str(settings_file):
            parent_has_init = (settings_file.parent / '__init__.py').exists()
            if parent_has_init:
                return settings_file
    
    return None

def extract_app_name_from_path(file_path: Path, project_path: Path) -> Optional[str]:
    """Extract Django app name from file path"""
    try:
        rel_path = file_path.relative_to(project_path)
    except ValueError:
        return None
    
    # Walk up to find apps.py
    current = file_path.parent
    while current != project_path:
        if (current / 'apps.py').exists():
            return current.name
        current = current.parent
    
    return None

def group_by_app(items: List[Dict], project_path: Path) -> Dict[str, List[Dict]]:
    """Group items by Django app"""
    grouped = {}
    
    for item in items:
        file_path = item.get('file')
        if file_path:
            app_name = extract_app_name_from_path(Path(file_path), project_path)
            if not app_name:
                app_name = 'core'
            
            if app_name not in grouped:
                grouped[app_name] = []
            grouped[app_name].append(item)
    
    return grouped

def clean_model_name(model_ref: str) -> str:
    """Clean model reference (remove quotes, 'self', etc.)"""
    # Remove quotes
    cleaned = model_ref.strip('\'"')
    
    # Handle 'self' reference
    if cleaned.lower() == 'self':
        return None
    
    # Get just the model name if it's a full path
    if '.' in cleaned:
        cleaned = cleaned.split('.')[-1]
    
    return cleaned

def deduplicate_list(items: List) -> List:
    """Remove duplicates while preserving order"""
    seen = set()
    result = []
    for item in items:
        # Handle dicts
        if isinstance(item, dict):
            key = item.get('name') or item.get('id') or str(item)
        else:
            key = item
        
        if key not in seen:
            seen.add(key)
            result.append(item)
    
    return result

def filter_third_party_imports(imports: List[Dict]) -> List[Dict]:
    """Filter out third-party package imports"""
    
    third_party_packages = {
        'django', 'rest_framework', 'celery', 'redis',
        'requests', 'numpy', 'pandas', 'pytest',
        'selenium', 'bs4', 'scrapy', 'flask',
        'sqlalchemy', 'alembic', 'jwt', 'bcrypt',
        'PIL', 'cv2', 'tensorflow', 'torch',
    }
    
    filtered = []
    for imp in imports:
        module = imp.get('module', '')
        if module:
            base_module = module.split('.')[0]
            if base_module not in third_party_packages:
                filtered.append(imp)
    
    return filtered

def format_parameter_list(params: List[Dict]) -> str:
    """Format parameter list for display"""
    if not params:
        return '()'
    
    param_strs = []
    for param in params:
        name = param.get('name', '')
        annotation = param.get('annotation')
        
        if annotation:
            param_strs.append(f"{name}: {annotation}")
        else:
            param_strs.append(name)
    
    if len(param_strs) > 3:
        return f"({', '.join(param_strs[:3])}, ...)"
    
    return f"({', '.join(param_strs)})"

def calculate_complexity_score(analysis_data: Dict) -> Dict:
    """Calculate complexity metrics for the codebase"""
    
    scores = {
        'total_files': 0,
        'total_lines': 0,
        'total_functions': 0,
        'total_classes': 0,
        'avg_file_size': 0,
        'cyclomatic_complexity': 0,
        'maintainability_index': 100,  # 0-100, higher is better
    }
    
    parsed_files = analysis_data.get('parsed_files', {})
    
    for file_path, file_data in parsed_files.items():
        scores['total_files'] += 1
        scores['total_functions'] += len(file_data.get('functions', []))
        scores['total_classes'] += len(file_data.get('classes', []))
    
    # Calculate averages
    if scores['total_files'] > 0:
        scores['avg_file_size'] = scores['total_lines'] / scores['total_files']
    
    # Rough maintainability calculation
    if scores['total_files'] > 0:
        files_penalty = min(scores['total_files'] / 10, 30)
        functions_penalty = min(scores['total_functions'] / 50, 20)
        classes_penalty = min(scores['total_classes'] / 20, 15)
        
        scores['maintainability_index'] = max(
            0,
            100 - files_penalty - functions_penalty - classes_penalty
        )
    
    return scores

def generate_summary_text(analysis_data: Dict) -> str:
    """Generate a text summary of the analysis"""
    
    summary = []
    
    stats = analysis_data.get('stats', {})
    
    summary.append("## Django Codebase Analysis Summary\n")
    summary.append(f"- **URLs**: {stats.get('total_urls', 0)}")
    summary.append(f"- **Views**: {stats.get('total_views', 0)}")
    summary.append(f"- **Models**: {stats.get('total_models', 0)}")
    summary.append(f"- **Apps**: {stats.get('total_apps', 0)}")
    summary.append(f"- **Environment Variables**: {stats.get('total_env_vars', 0)}\n")
    
    # Complexity
    complexity = calculate_complexity_score(analysis_data)
    summary.append("### Complexity Metrics")
    summary.append(f"- Files: {complexity['total_files']}")
    summary.append(f"- Functions: {complexity['total_functions']}")
    summary.append(f"- Classes: {complexity['total_classes']}")
    summary.append(f"- Maintainability: {complexity['maintainability_index']:.1f}/100\n")
    
    return '\n'.join(summary)

def detect_framework_version(project_path: Path) -> Dict:
    """Detect Django and other framework versions"""
    
    versions = {
        'django': 'unknown',
        'python': 'unknown',
        'drf': None,
    }
    
    # Check requirements files
    req_files = ['requirements.txt', 'requirements.in', 'Pipfile', 'pyproject.toml']
    
    for req_file in req_files:
        req_path = project_path / req_file
        if req_path.exists():
            try:
                content = req_path.read_text()
                
                # Django version
                django_match = re.search(r'[Dd]jango[=><~]+([0-9.]+)', content)
                if django_match:
                    versions['django'] = django_match.group(1)
                
                # DRF version
                drf_match = re.search(r'djangorestframework[=><~]+([0-9.]+)', content)
                if drf_match:
                    versions['drf'] = drf_match.group(1)
                
            except:
                pass
    
    return versions

def safe_file_read(file_path: Path, max_size_mb: int = 5) -> Optional[str]:
    """Safely read a file with size limit"""
    
    try:
        # Check file size
        size = file_path.stat().st_size
        if size > max_size_mb * 1024 * 1024:
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return None

def create_backup(file_path: Path) -> bool:
    """Create a backup of a file"""
    try:
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        import shutil
        shutil.copy2(file_path, backup_path)
        return True
    except:
        return False