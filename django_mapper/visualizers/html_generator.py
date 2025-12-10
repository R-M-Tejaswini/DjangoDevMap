import json
from pathlib import Path
from typing import Dict
from jinja2 import Template

class HTMLGenerator:
    """Generate enhanced interactive HTML visualization"""
    
    def __init__(self, analysis_result: Dict, runtime_mode: bool = False):
        self.data = analysis_result
        self.runtime_mode = runtime_mode
        
    def generate(self, output_path: Path):
        """Generate HTML file"""
        
        template = self._get_template()
        
        html_content = template.render(
            data=self.data,
            data_json=json.dumps(self.data, indent=2, default=str),
            runtime_mode=self.runtime_mode
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _get_template(self) -> Template:
        """Get Jinja2 template with enhanced features"""
        
        template_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Django Codebase Map - Enhanced</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            padding: 20px;
            background: #f5f5f5;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .stat-card h3 {
            font-size: 2em;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .stat-card p {
            color: #666;
            font-size: 0.9em;
        }
        
        .tabs {
            display: flex;
            background: #f7f7f7;
            border-bottom: 2px solid #ddd;
            overflow-x: auto;
        }
        
        .tab {
            padding: 15px 25px;
            cursor: pointer;
            background: #f7f7f7;
            border: none;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s;
            white-space: nowrap;
        }
        
        .tab:hover { background: #e7e7e7; }
        .tab.active {
            background: white;
            color: #667eea;
            border-bottom: 3px solid #667eea;
        }
        
        .tab-content {
            display: none;
            padding: 30px;
            max-height: 800px;
            overflow-y: auto;
        }
        
        .tab-content.active { display: block; }
        
        #graph {
            width: 100%;
            height: 700px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: #fafafa;
        }
        
        .node { cursor: pointer; }
        .node circle { stroke: #fff; stroke-width: 2px; }
        .node.url circle { fill: #4CAF50; }
        .node.view circle { fill: #2196F3; }
        .node.model circle { fill: #FF9800; }
        .node.form circle { fill: #9C27B0; }
        .node.function circle { fill: #00BCD4; }
        .node.class circle { fill: #673AB7; }
        .node text { font-size: 12px; pointer-events: none; }
        
        .link {
            fill: none;
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
        }
        
        .list-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }
        
        .card {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .card h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        
        .card-content {
            font-size: 14px;
            color: #555;
        }
        
        .card-content p {
            margin: 8px 0;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 5px;
            margin-top: 5px;
        }
        
        .badge-url { background: #4CAF50; color: white; }
        .badge-view { background: #2196F3; color: white; }
        .badge-model { background: #FF9800; color: white; }
        .badge-method { background: #9C27B0; color: white; }
        .badge-function { background: #00BCD4; color: white; }
        .badge-class { background: #673AB7; color: white; }
        
        .search-box {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            margin-bottom: 20px;
        }
        
        .search-box:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .legend {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
            padding: 15px;
            background: #f0f0f0;
            border-radius: 8px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }
        
        .code-snippet {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 12px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
            margin: 10px 0;
        }
        
        .dependency-tree {
            font-family: monospace;
            font-size: 13px;
            line-height: 1.6;
        }
        
        .dependency-item {
            padding-left: 20px;
            border-left: 2px solid #ddd;
            margin: 5px 0;
        }
        
        .sequence-flow {
            display: flex;
            align-items: center;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
            margin: 10px 0;
            overflow-x: auto;
        }
        
        .sequence-step {
            padding: 10px 15px;
            background: white;
            border-radius: 6px;
            min-width: 120px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .sequence-arrow {
            margin: 0 10px;
            color: #667eea;
            font-size: 24px;
        }
        
        ul { padding-left: 20px; }
        li { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗺️ Django Codebase Map</h1>
            <p>Comprehensive interactive visualization of your Django project</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{{ data.stats.total_urls }}</h3>
                <p>URL Patterns</p>
            </div>
            <div class="stat-card">
                <h3>{{ data.stats.total_views }}</h3>
                <p>Views</p>
            </div>
            <div class="stat-card">
                <h3>{{ data.stats.total_models }}</h3>
                <p>Models</p>
            </div>
            <div class="stat-card">
                <h3>{{ data.stats.total_classes }}</h3>
                <p>Classes</p>
            </div>
            <div class="stat-card">
                <h3>{{ data.stats.total_functions }}</h3>
                <p>Functions</p>
            </div>
            <div class="stat-card">
                <h3>{{ data.stats.total_apps }}</h3>
                <p>Apps</p>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('graph')">Flow Diagram</button>
            <button class="tab" onclick="showTab('sequences')">Request Sequences</button>
            <button class="tab" onclick="showTab('urls')">URLs</button>
            <button class="tab" onclick="showTab('views')">Views</button>
            <button class="tab" onclick="showTab('models')">Models</button>
            <button class="tab" onclick="showTab('classes')">Classes</button>
            <button class="tab" onclick="showTab('functions')">Functions</button>
            <button class="tab" onclick="showTab('dependencies')">Dependencies</button>
            <button class="tab" onclick="showTab('env')">Environment</button>
        </div>
        
        <div id="graph-tab" class="tab-content active">
            <div class="legend">
                <div class="legend-item"><div class="legend-color" style="background: #4CAF50;"></div><span>URLs</span></div>
                <div class="legend-item"><div class="legend-color" style="background: #2196F3;"></div><span>Views</span></div>
                <div class="legend-item"><div class="legend-color" style="background: #FF9800;"></div><span>Models</span></div>
                <div class="legend-item"><div class="legend-color" style="background: #9C27B0;"></div><span>Forms</span></div>
                <div class="legend-item"><div class="legend-color" style="background: #00BCD4;"></div><span>Functions</span></div>
                <div class="legend-item"><div class="legend-color" style="background: #673AB7;"></div><span>Classes</span></div>
            </div>
            <div id="graph"></div>
        </div>
        
        <div id="sequences-tab" class="tab-content">
            <h2>Typical Request Flow Sequences</h2>
            <p style="margin-bottom: 20px; color: #666;">Visual representation of how requests flow through your application</p>
            <div id="sequences-list"></div>
        </div>
        
        <div id="urls-tab" class="tab-content">
            <input type="text" class="search-box" id="url-search" placeholder="Search URLs...">
            <div id="urls-list" class="list-container"></div>
        </div>
        
        <div id="views-tab" class="tab-content">
            <input type="text" class="search-box" id="view-search" placeholder="Search views...">
            <div id="views-list" class="list-container"></div>
        </div>
        
        <div id="models-tab" class="tab-content">
            <input type="text" class="search-box" id="model-search" placeholder="Search models...">
            <div id="models-list" class="list-container"></div>
        </div>
        
        <div id="classes-tab" class="tab-content">
            <input type="text" class="search-box" id="class-search" placeholder="Search classes...">
            <div id="classes-list" class="list-container"></div>
        </div>
        
        <div id="functions-tab" class="tab-content">
            <input type="text" class="search-box" id="function-search" placeholder="Search functions...">
            <div id="functions-list" class="list-container"></div>
        </div>
        
        <div id="dependencies-tab" class="tab-content">
            <h2>Project Dependencies</h2>
            <div id="dependencies-list"></div>
        </div>
        
        <div id="env-tab" class="tab-content">
            <div id="env-list" class="list-container"></div>
        </div>
    </div>
    
    <script>
        const data = {{ data_json | safe }};
        
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').classList.add('active');
            
            const renderFunctions = {
                'graph': renderGraph,
                'sequences': renderSequences,
                'urls': renderUrls,
                'views': renderViews,
                'models': renderModels,
                'classes': renderClasses,
                'functions': renderFunctions,
                'dependencies': renderDependencies,
                'env': renderEnv
            };
            
            const renderKey = tabName + 'Rendered';
            if (!window[renderKey] && renderFunctions[tabName]) {
                renderFunctions[tabName]();
                window[renderKey] = true;
            }
        }
        
        function renderGraph() {
            const width = document.getElementById('graph').clientWidth;
            const height = 700;
            
            const svg = d3.select('#graph')
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const flowGraph = data.flow_graph || {nodes: [], edges: []};
            
            const simulation = d3.forceSimulation(flowGraph.nodes)
                .force('link', d3.forceLink(flowGraph.edges).id(d => d.id).distance(120))
                .force('charge', d3.forceManyBody().strength(-400))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(40));
            
            const link = svg.append('g')
                .selectAll('line')
                .data(flowGraph.edges)
                .enter().append('line')
                .attr('class', 'link');
            
            const node = svg.append('g')
                .selectAll('g')
                .data(flowGraph.nodes)
                .enter().append('g')
                .attr('class', d => 'node ' + d.type)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            node.append('circle').attr('r', 20);
            
            node.append('text')
                .attr('dy', 35)
                .attr('text-anchor', 'middle')
                .text(d => d.label.length > 20 ? d.label.substring(0, 20) + '...' : d.label);
            
            node.append('title').text(d => d.label);
            
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node.attr('transform', d => `translate(${d.x},${d.y})`);
            });
            
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
        }
        
        function renderSequences() {
            const container = document.getElementById('sequences-list');
            const sequences = data.sequences || [];
            
            sequences.forEach(seq => {
                const seqDiv = document.createElement('div');
                seqDiv.className = 'card';
                seqDiv.style.gridColumn = '1 / -1';
                
                let stepsHtml = '<div class="sequence-flow">';
                seq.steps.forEach((step, idx) => {
                    if (idx > 0) stepsHtml += '<div class="sequence-arrow">→</div>';
                    stepsHtml += `<div class="sequence-step">
                        <strong>${step.name}</strong><br>
                        <small>${step.type}</small>
                    </div>`;
                });
                stepsHtml += '</div>';
                
                seqDiv.innerHTML = `<h3>${seq.url}</h3>${stepsHtml}`;
                container.appendChild(seqDiv);
            });
        }
        
        function renderUrls() {
            const container = document.getElementById('urls-list');
            const urls = data.url_patterns || [];
            
            urls.forEach(url => {
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <h3>${url.pattern}</h3>
                    <div class="card-content">
                        <p><strong>View:</strong> ${url.view_name || 'N/A'}</p>
                        <p><strong>Name:</strong> ${url.name || 'N/A'}</p>
                        <p><strong>Type:</strong> <span class="badge badge-view">${url.view_type || 'N/A'}</span></p>
                    </div>
                `;
                container.appendChild(card);
            });
            
            addSearchListener('url-search', 'urls-list');
        }
        
        function renderViews() {
            const container = document.getElementById('views-list');
            const views = data.views || {};
            
            Object.entries(views).forEach(([name, view]) => {
                const card = document.createElement('div');
                card.className = 'card';
                
                const modelsUsed = view.models_used || [];
                const methods = view.http_methods || [];
                
                card.innerHTML = `
                    <h3>${name}</h3>
                    <div class="card-content">
                        <p><strong>File:</strong> ${view.file || 'N/A'}</p>
                        <p><strong>Type:</strong> <span class="badge badge-view">${view.type || 'N/A'}</span></p>
                        ${methods.length ? '<p><strong>HTTP Methods:</strong> ' + methods.map(m => '<span class="badge badge-method">' + m + '</span>').join(' ') + '</p>' : ''}
                        ${modelsUsed.length ? '<p><strong>Uses Models:</strong> ' + modelsUsed.map(m => '<span class="badge badge-model">' + m + '</span>').join(' ') + '</p>' : ''}
                    </div>
                `;
                container.appendChild(card);
            });
            
            addSearchListener('view-search', 'views-list');
        }
        
        function renderModels() {
            const container = document.getElementById('models-list');
            const models = data.models || {};
            
            Object.entries(models).forEach(([name, model]) => {
                const card = document.createElement('div');
                card.className = 'card';
                
                const fields = model.fields || [];
                
                card.innerHTML = `
                    <h3>${name}</h3>
                    <div class="card-content">
                        <p><strong>App:</strong> ${model.app || 'N/A'}</p>
                        <p><strong>File:</strong> ${model.file || 'N/A'}</p>
                        <p><strong>Fields (${fields.length}):</strong></p>
                        <ul>${fields.map(f => '<li>' + f.name + ' (' + f.type + ')</li>').join('')}</ul>
                    </div>
                `;
                container.appendChild(card);
            });
            
            addSearchListener('model-search', 'models-list');
        }
        
        function renderClasses() {
            const container = document.getElementById('classes-list');
            const parsedFiles = data.parsed_files || {};
            
            Object.entries(parsedFiles).forEach(([filePath, fileData]) => {
                const classes = fileData.classes || [];
                
                classes.forEach(cls => {
                    // Skip models and views (they're in other tabs)
                    if (cls.is_django_model || cls.is_django_view) return;
                    
                    const card = document.createElement('div');
                    card.className = 'card';
                    
                    const methods = cls.methods || [];
                    const baseClasses = cls.base_classes || [];
                    
                    card.innerHTML = `
                        <h3>${cls.name}</h3>
                        <div class="card-content">
                            <p><strong>File:</strong> ${filePath}</p>
                            <p><strong>Line:</strong> ${cls.line_number}</p>
                            ${baseClasses.length ? '<p><strong>Inherits from:</strong> ' + baseClasses.join(', ') + '</p>' : ''}
                            <p><strong>Methods (${methods.length}):</strong></p>
                            <ul>${methods.slice(0, 10).map(m => '<li>' + m.name + (m.http_method ? ' [' + m.http_method + ']' : '') + '</li>').join('')}</ul>
                            ${methods.length > 10 ? '<p><small>... and ' + (methods.length - 10) + ' more</small></p>' : ''}
                        </div>
                    `;
                    container.appendChild(card);
                });
            });
            
            addSearchListener('class-search', 'classes-list');
        }
        
        function renderFunctions() {
            const container = document.getElementById('functions-list');
            const parsedFiles = data.parsed_files || {};
            
            Object.entries(parsedFiles).forEach(([filePath, fileData]) => {
                const functions = fileData.functions || [];
                
                functions.forEach(func => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    
                    const params = func.parameters || [];
                    
                    card.innerHTML = `
                        <h3>${func.name}</h3>
                        <div class="card-content">
                            <p><strong>File:</strong> ${filePath}</p>
                            <p><strong>Line:</strong> ${func.line_number}</p>
                            <p><strong>Parameters:</strong> ${params.map(p => p.name).join(', ') || 'None'}</p>
                            ${func.return_type ? '<p><strong>Returns:</strong> ' + func.return_type + '</p>' : ''}
                            ${func.is_view ? '<p><span class="badge badge-view">Django View</span></p>' : ''}
                        </div>
                    `;
                    container.appendChild(card);
                });
            });
            
            addSearchListener('function-search', 'functions-list');
        }
        
        function renderDependencies() {
            const container = document.getElementById('dependencies-list');
            const depGraph = data.dependency_graph || {};
            
            const card = document.createElement('div');
            card.className = 'card';
            card.style.gridColumn = '1 / -1';
            
            let html = '<h3>Dependency Overview</h3><div class="card-content">';
            html += '<p>Total files with dependencies: ' + Object.keys(depGraph).length + '</p>';
            
            // Show circular dependencies if any
            const circular = depGraph.circular_dependencies || [];
            if (circular.length > 0) {
                html += '<h4 style="color: #f44336; margin-top: 15px;">⚠️ Circular Dependencies Found</h4>';
                html += '<ul>';
                circular.forEach(cycle => {
                    html += '<li>' + cycle.join(' → ') + '</li>';
                });
                html += '</ul>';
            }
            
            html += '</div>';
            card.innerHTML = html;
            container.appendChild(card);
        }
        
        function renderEnv() {
            const container = document.getElementById('env-list');
            const envVars = data.env_vars || [];
            
            envVars.forEach(env => {
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <h3>${env.name}</h3>
                    <div class="card-content">
                        <p><strong>Category:</strong> ${env.category}</p>
                        <p><strong>Required:</strong> ${env.required ? 'Yes' : 'Likely optional'}</p>
                    </div>
                `;
                container.appendChild(card);
            });
        }
        
        function addSearchListener(searchId, containerId) {
            document.getElementById(searchId).addEventListener('input', (e) => {
                const search = e.target.value.toLowerCase();
                const container = document.getElementById(containerId);
                Array.from(container.children).forEach(card => {
                    const text = card.textContent.toLowerCase();
                    card.style.display = text.includes(search) ? 'block' : 'none';
                });
            });
        }
        
        // Initialize
        renderGraph();
        window.graphRendered = true;
    </script>
</body>
</html>
        '''
        
        return Template(template_str)