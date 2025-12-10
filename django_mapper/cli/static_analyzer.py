import os
import ast
from pathlib import Path
from typing import Dict, List, Set

from django_mapper.cli.url_mapper import URLMapper
from django_mapper.cli.model_tracker import ModelTracker
from django_mapper.cli.view_analyzer import ViewAnalyzer
from django_mapper.cli.flow_builder import FlowBuilder
from django_mapper.analyzers.env_detector import EnvDetector
from django_mapper.analyzers.ast_parser import ASTParser
from django_mapper.analyzers.import_resolver import ImportResolver
from django_mapper.utils.config import Config
from django_mapper.utils.helpers import (
    is_django_project,
    extract_app_name_from_path,
    calculate_complexity_score
)

class StaticAnalyzer:
    """Enhanced static analyzer for Django projects with comprehensive code analysis"""
    
    def __init__(self, project_path: Path, include_tests: bool = False, config: Config = None):
        self.project_path = project_path
        self.include_tests = include_tests
        self.config = config or Config()
        
        # Core analyzers
        self.url_mapper = URLMapper(project_path)
        self.model_tracker = ModelTracker(project_path)
        self.view_analyzer = ViewAnalyzer(project_path)
        self.env_detector = EnvDetector(project_path)
        
        # Enhanced analyzers
        self.ast_parser = ASTParser(project_path)
        self.import_resolver = ImportResolver(project_path)
        
        # Results storage
        self.parsed_files = {}
        
    def analyze(self) -> Dict:
        """Run complete comprehensive static analysis"""
        
        print("🔍 Discovering Django apps...")
        apps = self._find_django_apps()
        
        print("📄 Parsing all Python files...")
        self._parse_all_project_files()
        
        print("🔗 Building module map...")
        self.import_resolver.build_module_map()
        
        print("🌐 Analyzing URLs...")
        url_patterns = self.url_mapper.extract_urls()
        
        print("📊 Analyzing models...")
        models = self.model_tracker.find_models()
        
        print("👁️  Analyzing views...")
        views = self.view_analyzer.analyze_views(url_patterns)
        
        print("🔧 Detecting environment variables...")
        env_vars = self.env_detector.detect()
        
        print("📦 Resolving imports and dependencies...")
        dependency_graph = self._build_dependency_graph()
        
        print("🔄 Building flow graph...")
        flow_data = self._build_comprehensive_flow(url_patterns, views, models)
        
        print("📈 Calculating metrics...")
        complexity = calculate_complexity_score({'parsed_files': self.parsed_files})
        
        print("✅ Analysis complete!")
        
        return {
            'apps': apps,
            'url_patterns': url_patterns,
            'models': models,
            'views': views,
            'env_vars': env_vars,
            'parsed_files': self.parsed_files,
            'dependency_graph': dependency_graph,
            'flow_graph': flow_data['flow_graph'],
            'sequences': flow_data['sequences'],
            'complexity': complexity,
            'stats': self._calculate_comprehensive_stats(
                url_patterns, views, models, apps, env_vars
            )
        }
    
    def _parse_all_project_files(self):
        """Parse all Python files in the project"""
        
        for py_file in self.project_path.rglob('*.py'):
            # Use config to check if file should be included
            if not self.config.is_project_file(py_file, self.project_path):
                continue
            
            # Skip test files if not included
            if not self.include_tests and 'test' in py_file.name.lower():
                continue
            
            # Parse the file
            parsed = self.ast_parser.parse_file(py_file)
            if parsed:
                rel_path = str(py_file.relative_to(self.project_path))
                self.parsed_files[rel_path] = parsed
    
    def _find_django_apps(self) -> List[Dict]:
        """Find all Django apps with enhanced metadata"""
        apps = []
        
        for item in self.project_path.rglob('*'):
            if item.is_dir() and (item / 'apps.py').exists():
                # Skip if in excluded directories
                if not self.config.is_project_file(item, self.project_path):
                    continue
                
                app_name = item.name
                rel_path = str(item.relative_to(self.project_path))
                
                # Count files
                py_files = list(item.glob('*.py'))
                total_lines = sum(
                    len(f.read_text().splitlines()) 
                    for f in py_files 
                    if f.is_file()
                )
                
                apps.append({
                    'name': app_name,
                    'path': rel_path,
                    'has_models': (item / 'models.py').exists() or (item / 'models').exists(),
                    'has_views': (item / 'views.py').exists() or (item / 'views').exists(),
                    'has_urls': (item / 'urls.py').exists(),
                    'has_admin': (item / 'admin.py').exists(),
                    'has_forms': (item / 'forms.py').exists(),
                    'has_serializers': (item / 'serializers.py').exists(),
                    'has_tests': any('test' in f.name for f in py_files),
                    'file_count': len(py_files),
                    'total_lines': total_lines,
                })
        
        return apps
    
    def _build_dependency_graph(self) -> Dict:
        """Build comprehensive dependency graph"""
        
        # Resolve imports for all parsed files
        for file_path, file_data in self.parsed_files.items():
            imports = file_data.get('imports', [])
            resolved = self.import_resolver.resolve_imports(
                self.project_path / file_path,
                imports
            )
            file_data['resolved_imports'] = resolved
        
        # Build the graph
        dependency_graph = self.import_resolver.build_dependency_graph(self.parsed_files)
        
        # Find circular dependencies
        circular = self.import_resolver.find_circular_dependencies(dependency_graph)
        dependency_graph['circular_dependencies'] = circular
        
        return dependency_graph
    
    def _build_comprehensive_flow(self, url_patterns, views, models) -> Dict:
        """Build comprehensive flow graph with all code elements"""
        
        # Prepare data for flow builder
        flow_data = {
            'url_patterns': url_patterns,
            'views': views,
            'models': models,
            'parsed_files': self.parsed_files,
        }
        
        # Build flow
        flow_builder = FlowBuilder(flow_data)
        complete_flow = flow_builder.build_complete_flow()
        
        return {
            'flow_graph': {
                'nodes': complete_flow['nodes'],
                'edges': complete_flow['edges'],
            },
            'sequences': complete_flow['sequences'],
            'stats': complete_flow['stats'],
        }
    
    def _calculate_comprehensive_stats(self, url_patterns, views, models, apps, env_vars) -> Dict:
        """Calculate comprehensive statistics"""
        
        stats = {
            'total_urls': len(url_patterns),
            'total_views': len(views),
            'total_models': len(models),
            'total_apps': len(apps),
            'total_env_vars': len(env_vars),
            'total_files': len(self.parsed_files),
        }
        
        # Count code elements
        total_classes = 0
        total_functions = 0
        total_methods = 0
        
        for file_data in self.parsed_files.values():
            classes = file_data.get('classes', [])
            functions = file_data.get('functions', [])
            
            total_classes += len(classes)
            total_functions += len(functions)
            
            for cls in classes:
                total_methods += len(cls.get('methods', []))
        
        stats['total_classes'] = total_classes
        stats['total_functions'] = total_functions
        stats['total_methods'] = total_methods
        
        # View types
        stats['function_based_views'] = sum(
            1 for v in views.values() if v.get('type') == 'function'
        )
        stats['class_based_views'] = sum(
            1 for v in views.values() if v.get('type') == 'class'
        )
        
        # Model relationships
        total_relationships = sum(
            len(m.get('relationships', [])) for m in models.values()
        )
        stats['total_model_relationships'] = total_relationships
        
        return stats