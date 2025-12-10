from pathlib import Path
from typing import Dict, List
import json

class Config:
    """Configuration management for Django Mapper"""
    
    DEFAULT_CONFIG = {
        'analysis': {
            'include_tests': False,
            'include_migrations': False,
            'max_file_size_kb': 500,
            'exclude_patterns': [
                'site-packages',
                'venv',
                'env',
                '.venv',
                'virtualenv',
                '__pycache__',
                '.git',
                'node_modules',
                '.pytest_cache',
                '.tox',
            ]
        },
        'output': {
            'format': 'both',  # html, mermaid, or both
            'output_dir': './django_map',
            'include_source_code': False,
            'max_nodes_in_graph': 200,
        },
        'visualization': {
            'show_external_packages': True,
            'show_decorators': True,
            'show_parameters': True,
            'group_by_app': True,
            'color_scheme': {
                'url': '#4CAF50',
                'view': '#2196F3',
                'model': '#FF9800',
                'form': '#9C27B0',
                'serializer': '#E91E63',
                'function': '#00BCD4',
                'class': '#673AB7',
            }
        },
        'runtime': {
            'enabled': False,
            'log_dir': './django_mapper_logs',
            'exclude_paths': ['/static/', '/media/', '/admin/jsi18n/'],
            'track_queries': True,
            'track_function_calls': False,
            'sanitize_sensitive_data': True,
        },
        'filtering': {
            'only_project_code': True,  # Filter out third-party packages
            'exclude_init_files': True,  # Don't analyze __init__.py
            'exclude_test_files': True,
            'exclude_migration_files': True,
            'min_function_lines': 2,  # Don't show trivial functions
        }
    }
    
    def __init__(self, config_path: Path = None):
        self.config = self.DEFAULT_CONFIG.copy()
        
        if config_path and config_path.exists():
            self.load_from_file(config_path)
    
    def load_from_file(self, config_path: Path):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self._merge_config(user_config)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def _merge_config(self, user_config: Dict):
        """Merge user configuration with defaults"""
        for section, values in user_config.items():
            if section in self.config:
                if isinstance(values, dict):
                    self.config[section].update(values)
                else:
                    self.config[section] = values
    
    def get(self, section: str, key: str = None, default=None):
        """Get configuration value"""
        if key is None:
            return self.config.get(section, default)
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def save_to_file(self, config_path: Path):
        """Save current configuration to file"""
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from analysis"""
        
        file_str = str(file_path)
        file_name = file_path.name
        
        # Check exclude patterns
        exclude_patterns = self.get('analysis', 'exclude_patterns', [])
        for pattern in exclude_patterns:
            if pattern in file_str:
                return True
        
        # Check filtering rules
        if self.get('filtering', 'exclude_init_files') and file_name == '__init__.py':
            return True
        
        if self.get('filtering', 'exclude_test_files') and 'test' in file_name:
            return True
        
        if self.get('filtering', 'exclude_migration_files') and 'migration' in file_str:
            return True
        
        # Check file size
        max_size = self.get('analysis', 'max_file_size_kb', 500) * 1024
        try:
            if file_path.stat().st_size > max_size:
                return True
        except:
            pass
        
        return False
    
    def is_project_file(self, file_path: Path, project_path: Path) -> bool:
        """Check if file is part of the actual project"""
        
        if not self.get('filtering', 'only_project_code'):
            return True
        
        # Must be within project
        try:
            file_path.relative_to(project_path)
        except ValueError:
            return False
        
        # Check exclusions
        return not self.should_exclude_file(file_path)
    
    def get_color_for_type(self, node_type: str) -> str:
        """Get color for a node type"""
        colors = self.get('visualization', 'color_scheme', {})
        return colors.get(node_type, '#999999')
    
    @classmethod
    def create_default_config(cls, output_path: Path):
        """Create a default configuration file"""
        config = cls()
        config.save_to_file(output_path)
        return config