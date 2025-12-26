import json
from pathlib import Path
from jinja2 import Template
from typing import Dict, List, Any

class HTMLGenerator:
    def __init__(self, data, runtime_mode=False):
        self.data = data
        self.runtime_mode = runtime_mode
    
    def generate(self, output_path: Path):
        """Generate HTML file with proper data structure"""
        
        template = self._get_template()
        
        # Transform the data to match template expectations
        template_data = self._prepare_template_data()
        
        html_content = template.render(
            **template_data,
            data_json=json.dumps(template_data, indent=2, default=str)
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _prepare_template_data(self):
        """Prepare data in the format the template expects"""
        
        # Get stats
        stats = self.data.get('stats', {})
        
        # Transform views data
        views_data = {}
        raw_views = self.data.get('views', {})
        for view_name, view_info in raw_views.items():
            views_data[view_name] = {
                'name': view_name,
                'type': view_info.get('type', 'unknown'),
                'file': view_info.get('file', ''),
                'app': view_info.get('app', 'unknown'),
                'methods': view_info.get('http_methods', []),
                'models_used': view_info.get('models_used', []),
                'url_patterns': view_info.get('url_patterns', [])
            }
        
        # Transform models data
        models_data = {}
        raw_models = self.data.get('models', {})
        for model_name, model_info in raw_models.items():
            models_data[model_name] = {
                'name': model_name,
                'app': model_info.get('app', 'unknown'),
                'file': model_info.get('file', ''),
                'fields': model_info.get('fields', []),
                'methods': model_info.get('methods', []),
                'relationships': model_info.get('relationships', [])
            }
        
        # Transform URLs data
        urls_data = self.data.get('url_patterns', [])
        
        # Transform parsed files for classes and functions
        classes_data = {}
        functions_data = {}
        parsed_files = self.data.get('parsed_files', {})
        
        for file_path, file_info in parsed_files.items():
            # Handle classes
            classes_info = file_info.get('classes', [])
            if isinstance(classes_info, list):
                for class_item in classes_info:
                    if isinstance(class_item, dict):
                        class_name = class_item.get('name', 'Unknown')
                        # Extract method names from method dicts
                        methods = class_item.get('methods', [])
                        method_names = []
                        for m in methods:
                            if isinstance(m, dict):
                                method_names.append(m.get('name', ''))
                            elif isinstance(m, str):
                                method_names.append(m)
                        
                        classes_data[f"{file_path}::{class_name}"] = {
                            'name': class_name,
                            'file': file_path,
                            'methods': method_names,
                            'bases': class_item.get('base_classes', []),
                            'type': self._determine_class_type(class_item),
                            'docstring': class_item.get('docstring', ''),
                            'is_django_model': class_item.get('is_django_model', False),
                            'is_django_view': class_item.get('is_django_view', False),
                            'is_rest_framework': class_item.get('is_rest_framework', False),
                        }
                    elif isinstance(class_item, str):
                        classes_data[f"{file_path}::{class_item}"] = {
                            'name': class_item,
                            'file': file_path,
                            'methods': [],
                            'bases': [],
                            'type': 'class'
                        }
            
            # Handle functions
            functions_info = file_info.get('functions', [])
            if isinstance(functions_info, list):
                for func_item in functions_info:
                    if isinstance(func_item, dict):
                        func_name = func_item.get('name', 'Unknown')
                        functions_data[f"{file_path}::{func_name}"] = {
                            'name': func_name,
                            'file': file_path,
                            'type': 'view' if func_item.get('is_view') else 'function',
                            'parameters': func_item.get('parameters', []),
                            'docstring': func_item.get('docstring', ''),
                            'decorators': func_item.get('decorators', []),
                        }
                    elif isinstance(func_item, str):
                        functions_data[f"{file_path}::{func_item}"] = {
                            'name': func_item,
                            'file': file_path,
                            'type': 'function',
                            'parameters': []
                        }
        
        # Prepare flow graph
        flow_graph = self.data.get('flow_graph', {'nodes': [], 'edges': []})
        
        # Build app structure for architecture view
        apps_data = self._build_apps_structure()
        
        # Build request flows
        request_flows = self._build_request_flows()
        
        return {
            'stats': stats,
            'urls': urls_data,
            'views': views_data,
            'models': models_data,
            'classes': classes_data,
            'functions': functions_data,
            'apps': apps_data,
            'sequences': self.data.get('sequences', []),
            'dependencies': self.data.get('dependency_graph', {}),
            'env_vars': self.data.get('env_vars', []),
            'flow_graph': flow_graph,
            'request_flows': request_flows,
            'runtime_mode': self.runtime_mode
        }
    
    def _determine_class_type(self, class_item: Dict) -> str:
        """Determine the type of class based on its properties"""
        if class_item.get('is_django_model'):
            return 'Model'
        elif class_item.get('is_rest_framework'):
            bases = class_item.get('base_classes', [])
            for base in bases:
                if 'ViewSet' in base:
                    return 'ViewSet'
                elif 'Serializer' in base:
                    return 'Serializer'
                elif 'APIView' in base:
                    return 'APIView'
            return 'DRF Class'
        elif class_item.get('is_django_view'):
            return 'View'
        else:
            return 'Class'
    
    def _build_apps_structure(self) -> List[Dict]:
        """Build structured app data for architecture visualization"""
        apps = self.data.get('apps', [])
        structured_apps = []
        
        for app in apps:
            app_name = app.get('name', 'Unknown')
            
            # Collect app's components
            app_models = []
            app_views = []
            app_urls = []
            
            # Get models for this app
            for model_name, model_info in self.data.get('models', {}).items():
                if model_info.get('app') == app_name:
                    app_models.append(model_name)
            
            # Get views for this app
            for view_name, view_info in self.data.get('views', {}).items():
                if view_info.get('app') == app_name or app_name in view_name:
                    app_views.append(view_name)
            
            # Get URLs for this app
            for url in self.data.get('url_patterns', []):
                if app_name in url.get('view_name', ''):
                    app_urls.append(url.get('pattern', ''))
            
            structured_apps.append({
                'name': app_name,
                'path': app.get('path', ''),
                'models': app_models,
                'views': app_views,
                'urls': app_urls,
                'has_models': app.get('has_models', False),
                'has_views': app.get('has_views', False),
                'has_urls': app.get('has_urls', False),
                'has_serializers': app.get('has_serializers', False),
                'has_admin': app.get('has_admin', False),
                'file_count': app.get('file_count', 0),
            })
        
        return structured_apps
    
    def _build_request_flows(self) -> List[Dict]:
        """Build request flow data showing URL -> View -> Model chains"""
        flows = []
        
        for url in self.data.get('url_patterns', []):
            view_name = url.get('view_name', '')
            view_info = self.data.get('views', {}).get(view_name, {})
            
            flow = {
                'url': url.get('pattern', ''),
                'url_name': url.get('name', ''),
                'view': view_name,
                'view_type': view_info.get('type', 'unknown'),
                'view_file': view_info.get('file', ''),
                'models': view_info.get('models_used', []),
                'methods': url.get('methods', ['GET']),
            }
            flows.append(flow)
        
        return flows
    
    def _get_template(self):
        """Get the comprehensive HTML template"""
        template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Django Codebase Intelligence</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        :root {
            --primary: #667eea;
            --primary-dark: #5a67d8;
            --secondary: #764ba2;
            --success: #48bb78;
            --warning: #ed8936;
            --danger: #f56565;
            --info: #4299e1;
            --dark: #2d3748;
            --light: #f7fafc;
            --gray: #718096;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
        }
        
        .app-container {
            display: flex;
            min-height: 100vh;
        }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background: var(--dark);
            color: white;
            padding: 20px;
            overflow-y: auto;
            position: fixed;
            height: 100vh;
        }
        
        .sidebar h1 {
            font-size: 1.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .sidebar .subtitle {
            font-size: 0.85em;
            color: var(--gray);
            margin-bottom: 30px;
        }
        
        .nav-section {
            margin-bottom: 25px;
        }
        
        .nav-section h3 {
            font-size: 0.75em;
            text-transform: uppercase;
            color: var(--gray);
            margin-bottom: 10px;
            letter-spacing: 1px;
        }
        
        .nav-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 15px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 5px;
            color: #cbd5e0;
        }
        
        .nav-item:hover {
            background: rgba(255,255,255,0.1);
            color: white;
        }
        
        .nav-item.active {
            background: var(--primary);
            color: white;
        }
        
        .nav-item .badge {
            margin-left: auto;
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }
        
        /* Main Content */
        .main-content {
            flex: 1;
            margin-left: 280px;
            padding: 30px;
            background: var(--light);
            min-height: 100vh;
        }
        
        .page {
            display: none;
        }
        
        .page.active {
            display: block;
        }
        
        .page-header {
            margin-bottom: 30px;
        }
        
        .page-header h2 {
            font-size: 2em;
            color: var(--dark);
            margin-bottom: 10px;
        }
        
        .page-header p {
            color: var(--gray);
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .stat-card .icon {
            width: 50px;
            height: 50px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5em;
            margin-bottom: 15px;
        }
        
        .stat-card .icon.urls { background: #c6f6d5; }
        .stat-card .icon.views { background: #bee3f8; }
        .stat-card .icon.models { background: #feebc8; }
        .stat-card .icon.classes { background: #e9d8fd; }
        .stat-card .icon.functions { background: #b2f5ea; }
        .stat-card .icon.apps { background: #fed7e2; }
        
        .stat-card h3 {
            font-size: 2.5em;
            color: var(--dark);
            margin-bottom: 5px;
        }
        
        .stat-card p {
            color: var(--gray);
            font-size: 0.9em;
        }
        
        /* Cards Grid */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 20px;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        .card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 15px;
        }
        
        .card-title {
            font-size: 1.1em;
            color: var(--dark);
            font-weight: 600;
            word-break: break-word;
        }
        
        .card-type {
            font-size: 0.75em;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .card-type.model { background: #feebc8; color: #c05621; }
        .card-type.view { background: #bee3f8; color: #2b6cb0; }
        .card-type.viewset { background: #c6f6d5; color: #276749; }
        .card-type.serializer { background: #e9d8fd; color: #6b46c1; }
        .card-type.class { background: #e2e8f0; color: #4a5568; }
        .card-type.function { background: #b2f5ea; color: #234e52; }
        
        .card-body {
            font-size: 0.9em;
            color: #4a5568;
        }
        
        .card-body .field {
            margin-bottom: 12px;
        }
        
        .card-body .field-label {
            font-weight: 600;
            color: var(--gray);
            font-size: 0.8em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin: 2px;
        }
        
        .badge-primary { background: var(--primary); color: white; }
        .badge-success { background: var(--success); color: white; }
        .badge-warning { background: var(--warning); color: white; }
        .badge-info { background: var(--info); color: white; }
        .badge-secondary { background: #e2e8f0; color: #4a5568; }
        
        /* Search */
        .search-container {
            margin-bottom: 25px;
        }
        
        .search-input {
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 1em;
            transition: border-color 0.2s;
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        /* Architecture View */
        .architecture-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .mermaid {
            text-align: center;
        }
        
        /* Flow Diagram */
        #flow-graph {
            width: 100%;
            height: 600px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .node circle {
            stroke-width: 3px;
        }
        
        .node text {
            font-size: 11px;
            font-weight: 500;
        }
        
        .link {
            fill: none;
            stroke: #cbd5e0;
            stroke-width: 2px;
        }
        
        .link.routes { stroke: var(--success); }
        .link.uses { stroke: var(--info); }
        .link.queries { stroke: var(--warning); }
        
        /* Request Flow Cards */
        .flow-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .flow-steps {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        
        .flow-step {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .flow-step-box {
            padding: 8px 15px;
            border-radius: 8px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .flow-step-box.url { background: #c6f6d5; color: #276749; }
        .flow-step-box.view { background: #bee3f8; color: #2b6cb0; }
        .flow-step-box.model { background: #feebc8; color: #c05621; }
        
        .flow-arrow {
            color: var(--gray);
            font-size: 1.2em;
        }
        
        /* Onboarding Section */
        .onboarding-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .onboarding-section h3 {
            color: var(--dark);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .step-list {
            list-style: none;
        }
        
        .step-list li {
            padding: 15px;
            border-left: 3px solid var(--primary);
            margin-bottom: 15px;
            background: var(--light);
            border-radius: 0 8px 8px 0;
        }
        
        .step-list li strong {
            color: var(--dark);
        }
        
        .code-block {
            background: var(--dark);
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85em;
            overflow-x: auto;
            margin: 10px 0;
        }
        
        /* Dependency Graph */
        .dep-tree {
            font-family: monospace;
            font-size: 0.9em;
            line-height: 1.8;
        }
        
        .dep-item {
            padding-left: 25px;
            border-left: 2px solid #e2e8f0;
            margin-left: 10px;
        }
        
        /* App Cards */
        .app-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        
        .app-card h3 {
            color: var(--dark);
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .app-components {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }
        
        .app-component {
            padding: 15px;
            background: var(--light);
            border-radius: 8px;
        }
        
        .app-component h4 {
            font-size: 0.8em;
            color: var(--gray);
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        
        .app-component ul {
            list-style: none;
            font-size: 0.9em;
        }
        
        .app-component li {
            padding: 3px 0;
            color: var(--dark);
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--gray);
        }
        
        .empty-state .icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 25px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0;
        }
        
        .tab-btn {
            padding: 12px 20px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.95em;
            color: var(--gray);
            border-bottom: 3px solid transparent;
            margin-bottom: -2px;
            transition: all 0.2s;
        }
        
        .tab-btn:hover {
            color: var(--primary);
        }
        
        .tab-btn.active {
            color: var(--primary);
            border-bottom-color: var(--primary);
            font-weight: 600;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Navigation -->
        <nav class="sidebar">
            <h1>🗺️ Django Map</h1>
            <p class="subtitle">Codebase Intelligence</p>
            
            <div class="nav-section">
                <h3>Overview</h3>
                <div class="nav-item active" onclick="showPage('dashboard')">
                    📊 Dashboard
                </div>
                <div class="nav-item" onclick="showPage('architecture')">
                    🏗️ Architecture
                </div>
                <div class="nav-item" onclick="showPage('flows')">
                    🔀 Request Flows
                </div>
            </div>
            
            <div class="nav-section">
                <h3>Code Elements</h3>
                <div class="nav-item" onclick="showPage('urls')">
                    🔗 URLs <span class="badge">{{ urls|length }}</span>
                </div>
                <div class="nav-item" onclick="showPage('views')">
                    👁️ Views <span class="badge">{{ views|length }}</span>
                </div>
                <div class="nav-item" onclick="showPage('models')">
                    📦 Models <span class="badge">{{ models|length }}</span>
                </div>
                <div class="nav-item" onclick="showPage('classes')">
                    🏛️ Classes <span class="badge">{{ classes|length }}</span>
                </div>
                <div class="nav-item" onclick="showPage('functions')">
                    ⚡ Functions <span class="badge">{{ functions|length }}</span>
                </div>
            </div>
            
            <div class="nav-section">
                <h3>Developer Tools</h3>
                <div class="nav-item" onclick="showPage('onboarding')">
                    🚀 Onboarding Guide
                </div>
                <div class="nav-item" onclick="showPage('dependencies')">
                    📦 Dependencies
                </div>
            </div>
        </nav>
        
        <!-- Main Content -->
        <main class="main-content">
            
            <!-- Dashboard Page -->
            <div id="dashboard-page" class="page active">
                <div class="page-header">
                    <h2>Dashboard</h2>
                    <p>Overview of your Django project structure</p>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="icon urls">🔗</div>
                        <h3>{{ stats.get('total_urls', 0) }}</h3>
                        <p>URL Patterns</p>
                    </div>
                    <div class="stat-card">
                        <div class="icon views">👁️</div>
                        <h3>{{ stats.get('total_views', 0) }}</h3>
                        <p>Views</p>
                    </div>
                    <div class="stat-card">
                        <div class="icon models">📦</div>
                        <h3>{{ stats.get('total_models', 0) }}</h3>
                        <p>Models</p>
                    </div>
                    <div class="stat-card">
                        <div class="icon classes">🏛️</div>
                        <h3>{{ stats.get('total_classes', 0) }}</h3>
                        <p>Classes</p>
                    </div>
                    <div class="stat-card">
                        <div class="icon functions">⚡</div>
                        <h3>{{ stats.get('total_functions', 0) }}</h3>
                        <p>Functions</p>
                    </div>
                    <div class="stat-card">
                        <div class="icon apps">📱</div>
                        <h3>{{ stats.get('total_apps', 0) }}</h3>
                        <p>Django Apps</p>
                    </div>
                </div>
                
                <!-- Apps Overview -->
                <h3 style="margin-bottom: 20px; color: var(--dark);">📱 Django Apps</h3>
                {% for app in apps %}
                <div class="app-card">
                    <h3>{{ app.name }}</h3>
                    <div class="app-components">
                        {% if app.models %}
                        <div class="app-component">
                            <h4>Models ({{ app.models|length }})</h4>
                            <ul>
                                {% for model in app.models[:5] %}
                                <li>{{ model }}</li>
                                {% endfor %}
                                {% if app.models|length > 5 %}
                                <li>... and {{ app.models|length - 5 }} more</li>
                                {% endif %}
                            </ul>
                        </div>
                        {% endif %}
                        {% if app.views %}
                        <div class="app-component">
                            <h4>Views ({{ app.views|length }})</h4>
                            <ul>
                                {% for view in app.views[:5] %}
                                <li>{{ view.split('.')[-1] }}</li>
                                {% endfor %}
                                {% if app.views|length > 5 %}
                                <li>... and {{ app.views|length - 5 }} more</li>
                                {% endif %}
                            </ul>
                        </div>
                        {% endif %}
                        {% if app.urls %}
                        <div class="app-component">
                            <h4>URLs ({{ app.urls|length }})</h4>
                            <ul>
                                {% for url in app.urls[:5] %}
                                <li>/{{ url }}</li>
                                {% endfor %}
                                {% if app.urls|length > 5 %}
                                <li>... and {{ app.urls|length - 5 }} more</li>
                                {% endif %}
                            </ul>
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <!-- Architecture Page -->
            <div id="architecture-page" class="page">
                <div class="page-header">
                    <h2>Architecture Overview</h2>
                    <p>Visual representation of your Django project structure</p>
                </div>
                
                <div class="architecture-container">
                    <div class="mermaid" id="architecture-diagram">
graph TB
    subgraph Project["🏠 Django Project"]
        {% for app in apps %}
        subgraph {{ app.name }}["📱 {{ app.name }}"]
            {% if app.has_urls %}{{ app.name }}_urls[🔗 URLs]{% endif %}
            {% if app.has_views %}{{ app.name }}_views[👁️ Views]{% endif %}
            {% if app.has_models %}{{ app.name }}_models[(📦 Models)]{% endif %}
            {% if app.has_serializers %}{{ app.name }}_serializers[📋 Serializers]{% endif %}
            
            {% if app.has_urls and app.has_views %}{{ app.name }}_urls --> {{ app.name }}_views{% endif %}
            {% if app.has_views and app.has_models %}{{ app.name }}_views --> {{ app.name }}_models{% endif %}
            {% if app.has_views and app.has_serializers %}{{ app.name }}_views --> {{ app.name }}_serializers{% endif %}
        end
        {% endfor %}
    end
                    </div>
                </div>
            </div>
            
            <!-- Request Flows Page -->
            <div id="flows-page" class="page">
                <div class="page-header">
                    <h2>Request Flows</h2>
                    <p>Trace how requests flow through your application</p>
                </div>
                
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search flows by URL or view..." onkeyup="filterFlows(event)">
                </div>
                
                <div id="flows-container">
                    {% for flow in request_flows %}
                    <div class="flow-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: var(--dark);">{{ flow.url or '/' }}</strong>
                            <div>
                                {% for method in flow.methods %}
                                <span class="badge badge-{% if method == 'GET' %}success{% elif method == 'POST' %}primary{% elif method == 'DELETE' %}warning{% else %}info{% endif %}">{{ method }}</span>
                                {% endfor %}
                            </div>
                        </div>
                        <div class="flow-steps">
                            <div class="flow-step">
                                <span class="flow-step-box url">🔗 /{{ flow.url }}</span>
                            </div>
                            <span class="flow-arrow">→</span>
                            <div class="flow-step">
                                <span class="flow-step-box view">👁️ {{ flow.view.split('.')[-1] if flow.view else 'Unknown' }}</span>
                            </div>
                            {% if flow.models %}
                            <span class="flow-arrow">→</span>
                            {% for model in flow.models %}
                            <div class="flow-step">
                                <span class="flow-step-box model">📦 {{ model }}</span>
                            </div>
                            {% endfor %}
                            {% endif %}
                        </div>
                        {% if flow.view_file %}
                        <div style="margin-top: 10px; font-size: 0.8em; color: var(--gray);">
                            📁 {{ flow.view_file }}
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- URLs Page -->
            <div id="urls-page" class="page">
                <div class="page-header">
                    <h2>URL Patterns</h2>
                    <p>All URL routes in your Django project</p>
                </div>
                
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search URLs..." onkeyup="filterCards('urls-container', event)">
                </div>
                
                <div class="cards-grid" id="urls-container">
                    {% for url in urls %}
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">/{{ url.pattern }}</span>
                            <span class="card-type view">{{ url.view_type }}</span>
                        </div>
                        <div class="card-body">
                            <div class="field">
                                <div class="field-label">View</div>
                                <div>{{ url.view_name }}</div>
                            </div>
                            {% if url.name %}
                            <div class="field">
                                <div class="field-label">URL Name</div>
                                <div>{{ url.name }}</div>
                            </div>
                            {% endif %}
                            {% if url.methods %}
                            <div class="field">
                                <div class="field-label">HTTP Methods</div>
                                <div>
                                    {% for method in url.methods %}
                                    <span class="badge badge-{% if method == 'GET' %}success{% elif method == 'POST' %}primary{% elif method == 'DELETE' %}warning{% else %}info{% endif %}">{{ method }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Views Page -->
            <div id="views-page" class="page">
                <div class="page-header">
                    <h2>Views</h2>
                    <p>All views handling requests in your project</p>
                </div>
                
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search views..." onkeyup="filterCards('views-container', event)">
                </div>
                
                <div class="cards-grid" id="views-container">
                    {% for view_name, view in views.items() %}
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">{{ view.name.split('.')[-1] }}</span>
                            <span class="card-type {% if 'ViewSet' in view.type %}viewset{% else %}view{% endif %}">{{ view.type }}</span>
                        </div>
                        <div class="card-body">
                            <div class="field">
                                <div class="field-label">Full Name</div>
                                <div>{{ view.name }}</div>
                            </div>
                            {% if view.app %}
                            <div class="field">
                                <div class="field-label">App</div>
                                <div>{{ view.app }}</div>
                            </div>
                            {% endif %}
                            {% if view.file %}
                            <div class="field">
                                <div class="field-label">File</div>
                                <div>{{ view.file }}</div>
                            </div>
                            {% endif %}
                            {% if view.models_used %}
                            <div class="field">
                                <div class="field-label">Models Used</div>
                                <div>
                                    {% for model in view.models_used %}
                                    <span class="badge badge-warning">{{ model }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Models Page -->
            <div id="models-page" class="page">
                <div class="page-header">
                    <h2>Models</h2>
                    <p>Django models and their relationships</p>
                </div>
                
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search models..." onkeyup="filterCards('models-container', event)">
                </div>
                
                <div class="cards-grid" id="models-container">
                    {% for model_name, model in models.items() %}
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">{{ model.name }}</span>
                            <span class="card-type model">Model</span>
                        </div>
                        <div class="card-body">
                            {% if model.app %}
                            <div class="field">
                                <div class="field-label">App</div>
                                <div>{{ model.app }}</div>
                            </div>
                            {% endif %}
                            {% if model.file %}
                            <div class="field">
                                <div class="field-label">File</div>
                                <div>{{ model.file }}</div>
                            </div>
                            {% endif %}
                            {% if model.fields %}
                            <div class="field">
                                <div class="field-label">Fields ({{ model.fields|length }})</div>
                                <div>
                                    {% for field in model.fields[:8] %}
                                    <span class="badge badge-secondary">{{ field.name if field.name else field }}</span>
                                    {% endfor %}
                                    {% if model.fields|length > 8 %}
                                    <span class="badge badge-secondary">+{{ model.fields|length - 8 }} more</span>
                                    {% endif %}
                                </div>
                            </div>
                            {% endif %}
                            {% if model.relationships %}
                            <div class="field">
                                <div class="field-label">Relationships</div>
                                <div>
                                    {% for rel in model.relationships %}
                                    <span class="badge badge-info">{{ rel.type if rel.type else rel }} → {{ rel.target if rel.target else '?' }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Classes Page -->
            <div id="classes-page" class="page">
                <div class="page-header">
                    <h2>Classes</h2>
                    <p>All classes in your codebase</p>
                </div>
                
                <div class="tabs">
                    <button class="tab-btn active" onclick="filterClassType('all')">All</button>
                    <button class="tab-btn" onclick="filterClassType('Model')">Models</button>
                    <button class="tab-btn" onclick="filterClassType('ViewSet')">ViewSets</button>
                    <button class="tab-btn" onclick="filterClassType('Serializer')">Serializers</button>
                    <button class="tab-btn" onclick="filterClassType('View')">Views</button>
                    <button class="tab-btn" onclick="filterClassType('Class')">Other</button>
                </div>
                
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search classes..." onkeyup="filterCards('classes-container', event)">
                </div>
                
                <div class="cards-grid" id="classes-container">
                    {% for class_key, class_info in classes.items() %}
                    <div class="card" data-class-type="{{ class_info.type }}">
                        <div class="card-header">
                            <span class="card-title">{{ class_info.name }}</span>
                            <span class="card-type {% if class_info.type == 'Model' %}model{% elif 'View' in class_info.type %}viewset{% elif class_info.type == 'Serializer' %}serializer{% else %}class{% endif %}">{{ class_info.type }}</span>
                        </div>
                        <div class="card-body">
                            <div class="field">
                                <div class="field-label">File</div>
                                <div>{{ class_info.file }}</div>
                            </div>
                            {% if class_info.bases %}
                            <div class="field">
                                <div class="field-label">Inherits From</div>
                                <div>
                                    {% for base in class_info.bases %}
                                    <span class="badge badge-secondary">{{ base }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                            {% if class_info.methods %}
                            <div class="field">
                                <div class="field-label">Methods ({{ class_info.methods|length }})</div>
                                <div>
                                    {% for method in class_info.methods[:6] %}
                                    <span class="badge badge-primary">{{ method }}</span>
                                    {% endfor %}
                                    {% if class_info.methods|length > 6 %}
                                    <span class="badge badge-secondary">+{{ class_info.methods|length - 6 }} more</span>
                                    {% endif %}
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Functions Page -->
            <div id="functions-page" class="page">
                <div class="page-header">
                    <h2>Functions</h2>
                    <p>Standalone functions in your codebase</p>
                </div>
                
                <div class="search-container">
                    <input type="text" class="search-input" placeholder="Search functions..." onkeyup="filterCards('functions-container', event)">
                </div>
                
                <div class="cards-grid" id="functions-container">
                    {% for func_key, func_info in functions.items() %}
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">{{ func_info.name }}</span>
                            <span class="card-type function">{{ func_info.type }}</span>
                        </div>
                        <div class="card-body">
                            <div class="field">
                                <div class="field-label">File</div>
                                <div>{{ func_info.file }}</div>
                            </div>
                            {% if func_info.parameters %}
                            <div class="field">
                                <div class="field-label">Parameters</div>
                                <div>
                                    {% for param in func_info.parameters %}
                                    <span class="badge badge-secondary">{{ param.name if param.name else param }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                            {% if func_info.decorators %}
                            <div class="field">
                                <div class="field-label">Decorators</div>
                                <div>
                                    {% for dec in func_info.decorators %}
                                    <span class="badge badge-info">@{{ dec }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <!-- Onboarding Page -->
            <div id="onboarding-page" class="page">
                <div class="page-header">
                    <h2>🚀 Developer Onboarding Guide</h2>
                    <p>Everything you need to understand and start working with this codebase</p>
                </div>
                
                <div class="onboarding-section">
                    <h3>📁 Project Structure</h3>
                    <p>This Django project contains <strong>{{ stats.get('total_apps', 0) }} apps</strong> with the following structure:</p>
                    <div class="code-block">
project/
├── manage.py              # Django management script
{% for app in apps %}├── {{ app.name }}/
│   ├── models.py          {% if app.has_models %}# {{ app.models|length }} models{% endif %}
│   ├── views.py           {% if app.has_views %}# {{ app.views|length }} views{% endif %}
│   ├── urls.py            {% if app.has_urls %}# URL routing{% endif %}
│   {% if app.has_serializers %}├── serializers.py     # DRF serializers{% endif %}
│   {% if app.has_admin %}└── admin.py           # Admin configuration{% endif %}
{% endfor %}</div>
                </div>
                
                <div class="onboarding-section">
                    <h3>🔗 Key Entry Points</h3>
                    <p>Main URL patterns that serve as entry points:</p>
                    <ul class="step-list">
                        {% for url in urls[:10] %}
                        <li>
                            <strong>/{{ url.pattern }}</strong><br>
                            → Handled by: <code>{{ url.view_name }}</code>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                
                <div class="onboarding-section">
                    <h3>📦 Data Models</h3>
                    <p>Core data models in this project:</p>
                    <ul class="step-list">
                        {% for model_name, model in models.items() %}
                        <li>
                            <strong>{{ model.name }}</strong> ({{ model.app }})<br>
                            {% if model.fields %}
                            Fields: {% for field in model.fields[:5] %}{{ field.name if field.name else field }}{% if not loop.last %}, {% endif %}{% endfor %}{% if model.fields|length > 5 %} (+{{ model.fields|length - 5 }} more){% endif %}
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                
                <div class="onboarding-section">
                    <h3>⚙️ Environment Setup</h3>
                    <div class="code-block">
# Clone and setup
git clone &lt;repository-url&gt;
cd &lt;project-name&gt;

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
                    </div>
                </div>
                
                {% if env_vars %}
                <div class="onboarding-section">
                    <h3>🔐 Environment Variables</h3>
                    <p>Required environment variables:</p>
                    <div class="code-block">
{% for env_var in env_vars %}{{ env_var.name }}={{ env_var.default or '&lt;value&gt;' }}
{% endfor %}</div>
                </div>
                {% endif %}
            </div>
            
            <!-- Dependencies Page -->
            <div id="dependencies-page" class="page">
                <div class="page-header">
                    <h2>Dependencies</h2>
                    <p>Import dependencies between modules</p>
                </div>
                
                <div class="onboarding-section">
                    <h3>📦 Module Dependencies</h3>
                    <div class="dep-tree">
                        {% for file, deps in dependencies.items() %}
                        <div style="margin-bottom: 15px;">
                            <strong>{{ file }}</strong>
                            {% if deps.imports %}
                            <div class="dep-item">
                                {% for imp in deps.imports[:10] %}
                                <div>↳ {{ imp.module }}{% if imp.name %}.{{ imp.name }}{% endif %}</div>
                                {% endfor %}
                                {% if deps.imports|length > 10 %}
                                <div>↳ ... and {{ deps.imports|length - 10 }} more</div>
                                {% endif %}
                            </div>
                            {% endif %}
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            
        </main>
    </div>
    
    <script>
        // Initialize Mermaid
        mermaid.initialize({ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
        
        // Page navigation
        function showPage(pageName) {
            // Hide all pages
            document.querySelectorAll('.page').forEach(page => {
                page.classList.remove('active');
            });
            
            // Remove active from all nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Show selected page
            document.getElementById(pageName + '-page').classList.add('active');
            
            // Add active to clicked nav item
            event.target.closest('.nav-item').classList.add('active');
        }
        
        // Filter cards
        function filterCards(containerId, event) {
            const filter = event.target.value.toLowerCase();
            const container = document.getElementById(containerId);
            const cards = container.getElementsByClassName('card');
            
            for (let card of cards) {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(filter) ? '' : 'none';
            }
        }
        
        // Filter flows
        function filterFlows(event) {
            const filter = event.target.value.toLowerCase();
            const container = document.getElementById('flows-container');
            const cards = container.getElementsByClassName('flow-card');
            
            for (let card of cards) {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(filter) ? '' : 'none';
            }
        }
        
        // Filter class types
        function filterClassType(type) {
            // Update active tab
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Filter cards
            const container = document.getElementById('classes-container');
            const cards = container.getElementsByClassName('card');
            
            for (let card of cards) {
                if (type === 'all') {
                    card.style.display = '';
                } else {
                    const cardType = card.getAttribute('data-class-type');
                    card.style.display = cardType === type ? '' : 'none';
                }
            }
        }
        
        // Log data for debugging
        console.log('Django Mapper Data:', {{ data_json | safe }});
    </script>
</body>
</html>'''
        return Template(template_content)