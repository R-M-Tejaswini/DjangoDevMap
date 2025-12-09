from pathlib import Path
from typing import Dict, List

class MermaidGenerator:
    """Generate Mermaid diagrams from analysis results"""
    
    def __init__(self, analysis_result: Dict):
        self.data = analysis_result
        
    def generate(self, output_path: Path):
        """Generate Mermaid diagrams file"""
        
        content = "# Django Codebase Diagrams\n\n"
        
        # Generate URL flow diagram
        content += "## URL → View → Model Flow\n\n"
        content += self._generate_flow_diagram()
        content += "\n\n"
        
        # Generate model relationships diagram
        content += "## Model Relationships\n\n"
        content += self._generate_model_diagram()
        content += "\n\n"
        
        # Generate app structure diagram
        content += "## App Structure\n\n"
        content += self._generate_app_diagram()
        content += "\n\n"
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_flow_diagram(self) -> str:
        """Generate main flow diagram showing URL → View → Model"""
        
        diagram = "```mermaid\ngraph LR\n"
        
        flow_graph = self.data.get('flow_graph', {})
        
        # Add nodes
        for node in flow_graph.get('nodes', []):
            node_id = self._sanitize_id(node['id'])
            label = self._sanitize_label(node['label'])
            
            if node['type'] == 'url':
                diagram += f"    {node_id}[/{label}/]\n"
            elif node['type'] == 'view':
                diagram += f"    {node_id}[{label}]\n"
            elif node['type'] == 'model':
                diagram += f"    {node_id}[({label})]\n"
        
        # Add edges
        for edge in flow_graph.get('edges', []):
            from_id = self._sanitize_id(edge['from'])
            to_id = self._sanitize_id(edge['to'])
            edge_type = edge.get('type', '')
            
            if edge_type == 'routes_to':
                diagram += f"    {from_id} -->|routes| {to_id}\n"
            elif edge_type == 'uses':
                diagram += f"    {from_id} -.->|uses| {to_id}\n"
        
        diagram += "```\n"
        
        return diagram
    
    def _generate_model_diagram(self) -> str:
        """Generate entity relationship diagram for models"""
        
        diagram = "```mermaid\nerDiagram\n"
        
        models = self.data.get('models', {})
        
        for model_name, model_data in models.items():
            # Add model with fields
            diagram += f"    {model_name} {{\n"
            
            for field in model_data.get('fields', []):
                field_type = field.get('type', 'Unknown')
                field_name = field.get('name', '')
                diagram += f"        {field_type} {field_name}\n"
            
            diagram += "    }\n"
        
        # Add relationships
        for model_name, model_data in models.items():
            for rel in model_data.get('relationships', []):
                related_model = rel.get('related_model', '')
                rel_type = rel.get('type', 'ForeignKey')
                
                # Clean up related model name (remove quotes, self references)
                if related_model and related_model != 'self' and related_model in models:
                    if rel_type == 'ForeignKey':
                        diagram += f"    {model_name} ||--o{{ {related_model} : has\n"
                    elif rel_type == 'OneToOneField':
                        diagram += f"    {model_name} ||--|| {related_model} : has\n"
                    elif rel_type == 'ManyToManyField':
                        diagram += f"    {model_name} }}o--o{{ {related_model} : has\n"
        
        diagram += "```\n"
        
        return diagram
    
    def _generate_app_diagram(self) -> str:
        """Generate diagram showing app structure"""
        
        diagram = "```mermaid\ngraph TB\n"
        
        apps = self.data.get('apps', [])
        
        diagram += "    Project[Django Project]\n"
        
        for app in apps:
            app_name = app['name']
            app_id = self._sanitize_id(app_name)
            
            diagram += f"    Project --> {app_id}[{app_name}]\n"
            
            if app.get('has_models'):
                diagram += f"    {app_id} --> {app_id}_models[(Models)]\n"
            
            if app.get('has_views'):
                diagram += f"    {app_id} --> {app_id}_views[Views]\n"
            
            if app.get('has_urls'):
                diagram += f"    {app_id} --> {app_id}_urls[URLs]\n"
            
            if app.get('has_admin'):
                diagram += f"    {app_id} --> {app_id}_admin[Admin]\n"
        
        diagram += "```\n"
        
        return diagram
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use as Mermaid node ID"""
        # Replace special characters with underscores
        sanitized = text.replace('/', '_').replace('.', '_').replace('-', '_')
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
        # Ensure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'n_' + sanitized
        return sanitized or 'node'
    
    def _sanitize_label(self, text: str) -> str:
        """Sanitize text for use as Mermaid label"""
        # Escape special characters
        return text.replace('[', '(').replace(']', ')').replace('"', "'")