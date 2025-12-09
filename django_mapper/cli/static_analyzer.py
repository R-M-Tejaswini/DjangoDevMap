import os
import ast
from pathlib import Path
from typing import Dict, List, Set
import importlib.util

from django_mapper.cli.url_mapper import URLMapper
from django_mapper.cli.model_tracker import ModelTracker
from django_mapper.cli.view_analyzer import ViewAnalyzer
from django_mapper.analyzers.env_detector import EnvDetector

class StaticAnalyzer:
    """Main static analyzer for Django projects"""
    
    def __init__(self, project_path: Path, include_tests: bool = False):
        self.project_path = project_path
        self.include_tests = include_tests
        self.url_mapper = URLMapper(project_path)
        self.model_tracker = ModelTracker(project_path)
        self.view_analyzer = ViewAnalyzer(project_path)
        self.env_detector = EnvDetector(project_path)
        
    def analyze(self) -> Dict:
        """Run complete static analysis"""
        
        # Find all Django apps
        apps = self._find_django_apps()
        
        # Analyze URLs
        url_patterns = self.url_mapper.extract_urls()
        
        # Analyze models
        models = self.model_tracker.find_models()
        
        # Analyze views
        views = self.view_analyzer.analyze_views(url_patterns)
        
        # Detect environment variables
        env_vars = self.env_detector.detect()
        
        # Build flow graph
        flow_graph = self._build_flow_graph(url_patterns, views, models)
        
        return {
            'apps': apps,
            'url_patterns': url_patterns,
            'models': models,
            'views': views,
            'env_vars': env_vars,
            'flow_graph': flow_graph,
            'stats': self._calculate_stats(url_patterns, views, models, apps, env_vars)
        }
    
    def _find_django_apps(self) -> List[Dict]:
        """Find all Django apps in the project"""
        apps = []
        
        for item in self.project_path.rglob('*'):
            if item.is_dir() and (item / 'apps.py').exists():
                app_name = item.name
                apps.append({
                    'name': app_name,
                    'path': str(item.relative_to(self.project_path)),
                    'has_models': (item / 'models.py').exists() or (item / 'models').exists(),
                    'has_views': (item / 'views.py').exists() or (item / 'views').exists(),
                    'has_urls': (item / 'urls.py').exists(),
                    'has_admin': (item / 'admin.py').exists(),
                })
        
        return apps
    
    def _build_flow_graph(self, url_patterns, views, models):
        """Build a flow graph connecting URLs -> Views -> Models"""
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Add URL nodes
        for url in url_patterns:
            graph['nodes'].append({
                'id': f"url_{url['pattern']}",
                'type': 'url',
                'label': url['pattern'],
                'data': url
            })
            
            # Connect URL to View
            if url.get('view_name'):
                graph['edges'].append({
                    'from': f"url_{url['pattern']}",
                    'to': f"view_{url['view_name']}",
                    'type': 'routes_to'
                })
        
        # Add View nodes
        for view_name, view_data in views.items():
            graph['nodes'].append({
                'id': f"view_{view_name}",
                'type': 'view',
                'label': view_name,
                'data': view_data
            })
            
            # Connect View to Models
            for model in view_data.get('models_used', []):
                graph['edges'].append({
                    'from': f"view_{view_name}",
                    'to': f"model_{model}",
                    'type': 'uses'
                })
        
        # Add Model nodes
        for model_name, model_data in models.items():
            graph['nodes'].append({
                'id': f"model_{model_name}",
                'type': 'model',
                'label': model_name,
                'data': model_data
            })
        
        return graph
    
    def _calculate_stats(self, url_patterns, views, models, apps, env_vars):
        """Calculate summary statistics"""
        return {
            'total_urls': len(url_patterns),
            'total_views': len(views),
            'total_models': len(models),
            'total_apps': len(apps),
            'total_env_vars': len(env_vars)
        }