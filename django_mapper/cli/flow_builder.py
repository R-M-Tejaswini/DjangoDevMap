from typing import Dict, List, Set
from pathlib import Path

class FlowBuilder:
    """Build comprehensive flow graphs showing code execution paths"""
    
    def __init__(self, analysis_data: Dict):
        self.data = analysis_data
        self.nodes = []
        self.edges = []
        self.flow_sequences = []
        
    def build_complete_flow(self) -> Dict:
        """Build a complete flow graph with all relationships"""
        
        # Reset
        self.nodes = []
        self.edges = []
        
        # Add URL nodes
        self._add_url_nodes()
        
        # Add View nodes
        self._add_view_nodes()
        
        # Add Model nodes
        self._add_model_nodes()
        
        # Add Form/Serializer nodes
        self._add_form_serializer_nodes()
        
        # Add Function nodes
        self._add_function_nodes()
        
        # Add Class nodes
        self._add_class_nodes()
        
        # Connect URLs to Views
        self._connect_urls_to_views()
        
        # Connect Views to Models
        self._connect_views_to_models()
        
        # Connect Views to Forms/Serializers
        self._connect_views_to_forms()
        
        # Connect function calls
        self._connect_function_calls()
        
        # Connect class inheritance
        self._connect_class_hierarchy()
        
        # Connect method calls
        self._connect_method_calls()
        
        # Build sequences
        self._build_request_sequences()
        
        return {
            'nodes': self.nodes,
            'edges': self.edges,
            'sequences': self.flow_sequences,
            'stats': self._calculate_flow_stats()
        }
    
    def _add_url_nodes(self):
        """Add URL pattern nodes"""
        for url in self.data.get('url_patterns', []):
            self.nodes.append({
                'id': self._make_id('url', url['pattern']),
                'type': 'url',
                'label': url['pattern'],
                'name': url.get('name'),
                'http_methods': self._extract_http_methods(url),
                'data': url
            })
    
    def _add_view_nodes(self):
        """Add view nodes (both function and class-based)"""
        for view_name, view_data in self.data.get('views', {}).items():
            node = {
                'id': self._make_id('view', view_name),
                'type': 'view',
                'label': view_name,
                'view_type': view_data.get('type'),
                'file': view_data.get('file'),
                'data': view_data
            }
            
            # Add HTTP methods if it's a class-based view
            if view_data.get('http_methods'):
                node['http_methods'] = view_data['http_methods']
            
            self.nodes.append(node)
    
    def _add_model_nodes(self):
        """Add model nodes"""
        for model_name, model_data in self.data.get('models', {}).items():
            self.nodes.append({
                'id': self._make_id('model', model_name),
                'type': 'model',
                'label': model_name,
                'app': model_data.get('app'),
                'fields': [f['name'] for f in model_data.get('fields', [])],
                'data': model_data
            })
    
    def _add_form_serializer_nodes(self):
        """Add form and serializer nodes"""
        # Extract from views
        for view_name, view_data in self.data.get('views', {}).items():
            for form in view_data.get('forms_used', []):
                if not self._node_exists('form', form):
                    self.nodes.append({
                        'id': self._make_id('form', form),
                        'type': 'form',
                        'label': form,
                        'data': {}
                    })
            
            for serializer in view_data.get('serializers_used', []):
                if not self._node_exists('serializer', serializer):
                    self.nodes.append({
                        'id': self._make_id('serializer', serializer),
                        'type': 'serializer',
                        'label': serializer,
                        'data': {}
                    })
    
    def _add_function_nodes(self):
        """Add standalone function nodes"""
        for file_path, file_data in self.data.get('parsed_files', {}).items():
            for func in file_data.get('functions', []):
                # Only add if not already added as a view
                func_name = func['name']
                if not self._node_exists('function', func_name):
                    self.nodes.append({
                        'id': self._make_id('function', func_name),
                        'type': 'function',
                        'label': func_name,
                        'file': file_path,
                        'parameters': [p['name'] for p in func.get('parameters', [])],
                        'data': func
                    })
    
    def _add_class_nodes(self):
        """Add class nodes (non-model, non-view classes)"""
        for file_path, file_data in self.data.get('parsed_files', {}).items():
            for cls in file_data.get('classes', []):
                cls_name = cls['name']
                
                # Skip if already added as model or view
                if cls.get('is_django_model') or cls.get('is_django_view'):
                    continue
                
                if not self._node_exists('class', cls_name):
                    self.nodes.append({
                        'id': self._make_id('class', cls_name),
                        'type': 'class',
                        'label': cls_name,
                        'file': file_path,
                        'methods': [m['name'] for m in cls.get('methods', [])],
                        'base_classes': cls.get('base_classes', []),
                        'data': cls
                    })
    
    def _connect_urls_to_views(self):
        """Connect URL patterns to their views"""
        for url in self.data.get('url_patterns', []):
            view_name = url.get('view_name')
            if view_name:
                url_id = self._make_id('url', url['pattern'])
                view_id = self._make_id('view', view_name)
                
                if self._node_exists_by_id(view_id):
                    self.edges.append({
                        'from': url_id,
                        'to': view_id,
                        'type': 'routes_to',
                        'label': 'routes to',
                        'methods': self._extract_http_methods(url)
                    })
    
    def _connect_views_to_models(self):
        """Connect views to models they use"""
        for view_name, view_data in self.data.get('views', {}).items():
            view_id = self._make_id('view', view_name)
            
            for model in view_data.get('models_used', []):
                model_id = self._make_id('model', model)
                if self._node_exists_by_id(model_id):
                    self.edges.append({
                        'from': view_id,
                        'to': model_id,
                        'type': 'uses_model',
                        'label': 'uses'
                    })
    
    def _connect_views_to_forms(self):
        """Connect views to forms and serializers"""
        for view_name, view_data in self.data.get('views', {}).items():
            view_id = self._make_id('view', view_name)
            
            for form in view_data.get('forms_used', []):
                form_id = self._make_id('form', form)
                if self._node_exists_by_id(form_id):
                    self.edges.append({
                        'from': view_id,
                        'to': form_id,
                        'type': 'uses_form',
                        'label': 'uses'
                    })
            
            for serializer in view_data.get('serializers_used', []):
                serializer_id = self._make_id('serializer', serializer)
                if self._node_exists_by_id(serializer_id):
                    self.edges.append({
                        'from': view_id,
                        'to': serializer_id,
                        'type': 'uses_serializer',
                        'label': 'uses'
                    })
    
    def _connect_function_calls(self):
        """Connect function calls"""
        for file_path, file_data in self.data.get('parsed_files', {}).items():
            for func in file_data.get('functions', []):
                func_id = self._make_id('function', func['name'])
                
                for call in func.get('calls', []):
                    called_func = call['name'].split('.')[-1]  # Get last part
                    called_id = self._make_id('function', called_func)
                    
                    if self._node_exists_by_id(called_id) and func_id != called_id:
                        self.edges.append({
                            'from': func_id,
                            'to': called_id,
                            'type': 'calls',
                            'label': 'calls'
                        })
    
    def _connect_class_hierarchy(self):
        """Connect class inheritance relationships"""
        for file_path, file_data in self.data.get('parsed_files', {}).items():
            for cls in file_data.get('classes', []):
                cls_id = self._make_id('class', cls['name'])
                
                for base_class in cls.get('base_classes', []):
                    # Get just the class name (remove module path)
                    base_name = base_class.split('.')[-1]
                    base_id = self._make_id('class', base_name)
                    
                    if self._node_exists_by_id(base_id) and cls_id != base_id:
                        self.edges.append({
                            'from': cls_id,
                            'to': base_id,
                            'type': 'inherits',
                            'label': 'inherits from'
                        })
    
    def _connect_method_calls(self):
        """Connect method calls within classes"""
        for file_path, file_data in self.data.get('parsed_files', {}).items():
            for cls in file_data.get('classes', []):
                cls_id = self._make_id('class', cls['name'])
                
                for method in cls.get('methods', []):
                    # Track method calls to models
                    for call in method.get('calls', []):
                        # Check if it's a model query
                        if '.objects.' in call['name']:
                            model_name = call['name'].split('.')[0]
                            model_id = self._make_id('model', model_name)
                            
                            if self._node_exists_by_id(model_id):
                                self.edges.append({
                                    'from': cls_id,
                                    'to': model_id,
                                    'type': 'queries',
                                    'label': 'queries',
                                    'method': method['name']
                                })
    
    def _build_request_sequences(self):
        """Build typical request flow sequences"""
        # Start from each URL
        for url in self.data.get('url_patterns', []):
            sequence = self._trace_sequence_from_url(url)
            if sequence:
                self.flow_sequences.append(sequence)
    
    def _trace_sequence_from_url(self, url: Dict) -> Dict:
        """Trace the sequence of operations from a URL"""
        
        sequence = {
            'url': url['pattern'],
            'steps': []
        }
        
        # Step 1: URL
        sequence['steps'].append({
            'type': 'url',
            'name': url['pattern'],
            'details': f"Request to {url['pattern']}"
        })
        
        # Step 2: View
        view_name = url.get('view_name')
        if not view_name:
            return None
        
        view_data = self.data.get('views', {}).get(view_name)
        if view_data:
            sequence['steps'].append({
                'type': 'view',
                'name': view_name,
                'details': f"{view_data.get('type', 'function')} view"
            })
            
            # Step 3: Models used
            for model in view_data.get('models_used', []):
                sequence['steps'].append({
                    'type': 'model',
                    'name': model,
                    'details': f"Query/Update {model}"
                })
            
            # Step 4: Forms/Serializers
            for form in view_data.get('forms_used', []):
                sequence['steps'].append({
                    'type': 'form',
                    'name': form,
                    'details': f"Validate with {form}"
                })
        
        return sequence if len(sequence['steps']) > 1 else None
    
    def _extract_http_methods(self, url: Dict) -> List[str]:
        """Extract HTTP methods for a URL"""
        methods = url.get('methods', [])
        if not methods:
            # Try to infer from view
            view_name = url.get('view_name')
            if view_name:
                view_data = self.data.get('views', {}).get(view_name)
                if view_data:
                    methods = view_data.get('http_methods', [])
        return methods or ['GET']
    
    def _make_id(self, node_type: str, name: str) -> str:
        """Create a unique node ID"""
        return f"{node_type}_{name}".replace('/', '_').replace('.', '_').replace(' ', '_')
    
    def _node_exists(self, node_type: str, name: str) -> bool:
        """Check if a node already exists"""
        node_id = self._make_id(node_type, name)
        return any(node['id'] == node_id for node in self.nodes)
    
    def _node_exists_by_id(self, node_id: str) -> bool:
        """Check if a node with given ID exists"""
        return any(node['id'] == node_id for node in self.nodes)
    
    def _calculate_flow_stats(self) -> Dict:
        """Calculate statistics about the flow"""
        
        stats = {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'by_type': {},
            'complexity_score': 0
        }
        
        # Count nodes by type
        for node in self.nodes:
            node_type = node['type']
            stats['by_type'][node_type] = stats['by_type'].get(node_type, 0) + 1
        
        # Calculate complexity (rough estimate)
        stats['complexity_score'] = len(self.edges) * 0.5 + len(self.nodes) * 0.3
        
        return stats
    
    def get_node_by_id(self, node_id: str) -> Dict:
        """Get a node by its ID"""
        for node in self.nodes:
            if node['id'] == node_id:
                return node
        return None
    
    def get_connected_nodes(self, node_id: str, direction: str = 'both') -> List[Dict]:
        """Get all nodes connected to a given node"""
        connected = []
        
        for edge in self.edges:
            if direction in ['from', 'both'] and edge['from'] == node_id:
                node = self.get_node_by_id(edge['to'])
                if node:
                    connected.append(node)
            
            if direction in ['to', 'both'] and edge['to'] == node_id:
                node = self.get_node_by_id(edge['from'])
                if node:
                    connected.append(node)
        
        return connected