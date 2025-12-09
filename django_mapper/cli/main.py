import click
import os
import sys
from pathlib import Path
from colorama import init, Fore, Style

from django_mapper.cli.static_analyzer import StaticAnalyzer
from django_mapper.visualizers.html_generator import HTMLGenerator
from django_mapper.visualizers.mermaid_generator import MermaidGenerator
from django_mapper.storage.log_store import LogStore

init(autoreset=True)

@click.group()
def cli():
    """Django Codebase Mapper - Understand Django projects visually"""
    pass

@cli.command()
@click.option('--path', default='.', help='Path to Django project root')
@click.option('--output', default='./django_map', help='Output directory for visualizations')
@click.option('--format', type=click.Choice(['html', 'mermaid', 'both']), default='both')
@click.option('--include-tests', is_flag=True, help='Include test files in analysis')
def analyze(path, output, format, include_tests):
    """Analyze Django project structure statically"""
    click.echo(f"{Fore.CYAN}🔍 Starting Django Codebase Analysis...{Style.RESET_ALL}")
    
    project_path = Path(path).resolve()
    if not project_path.exists():
        click.echo(f"{Fore.RED}❌ Project path does not exist: {project_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    # Check if it's a Django project
    if not _is_django_project(project_path):
        click.echo(f"{Fore.YELLOW}⚠️  Warning: No manage.py found. Is this a Django project?{Style.RESET_ALL}")
        if not click.confirm('Continue anyway?'):
            sys.exit(0)
    
    # Create output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Run static analysis
    analyzer = StaticAnalyzer(project_path, include_tests=include_tests)
    click.echo(f"{Fore.GREEN}📊 Analyzing project structure...{Style.RESET_ALL}")
    
    analysis_result = analyzer.analyze()
    
    # Display summary
    _display_summary(analysis_result)
    
    # Generate visualizations
    if format in ['html', 'both']:
        click.echo(f"\n{Fore.CYAN}🎨 Generating HTML visualization...{Style.RESET_ALL}")
        html_gen = HTMLGenerator(analysis_result)
        html_path = output_path / 'codebase_map.html'
        html_gen.generate(html_path)
        click.echo(f"{Fore.GREEN}✅ HTML saved to: {html_path}{Style.RESET_ALL}")
    
    if format in ['mermaid', 'both']:
        click.echo(f"\n{Fore.CYAN}📈 Generating Mermaid diagrams...{Style.RESET_ALL}")
        mermaid_gen = MermaidGenerator(analysis_result)
        mermaid_path = output_path / 'diagrams.md'
        mermaid_gen.generate(mermaid_path)
        click.echo(f"{Fore.GREEN}✅ Mermaid diagrams saved to: {mermaid_path}{Style.RESET_ALL}")
    
    # Save raw data
    log_store = LogStore(output_path / 'analysis_data.json')
    log_store.save(analysis_result)
    
    click.echo(f"\n{Fore.GREEN}🎉 Analysis complete!{Style.RESET_ALL}")

@cli.command()
@click.option('--settings', help='Django settings module (e.g., myproject.settings)')
def setup_middleware(settings):
    """Generate middleware setup instructions"""
    click.echo(f"{Fore.CYAN}📝 Middleware Setup Instructions{Style.RESET_ALL}\n")
    
    instructions = """
To enable runtime request logging, add the following to your Django settings:

1. Add to MIDDLEWARE (at the top for best coverage):
   
   MIDDLEWARE = [
       'django_mapper.middleware.request_logger.RequestLoggerMiddleware',
       'django_mapper.middleware.call_tracer.CallTracerMiddleware',
       # ... your other middleware
   ]

2. Add to INSTALLED_APPS:
   
   INSTALLED_APPS = [
       # ... your apps
       'django_mapper',
   ]

3. Configure logging settings:
   
   DJANGO_MAPPER = {
       'ENABLED': True,  # Set to False in production!
       'LOG_DIR': './django_mapper_logs',
       'EXCLUDE_PATHS': ['/static/', '/media/', '/admin/jsi18n/'],
       'TRACK_QUERIES': True,
       'TRACK_FUNCTION_CALLS': True,
   }

4. After exploring your app, run:
   
   django-mapper visualize-runtime --log-dir ./django_mapper_logs

⚠️  IMPORTANT: Only enable in development/debug mode!
⚠️  Add django_mapper_logs/ to your .gitignore
"""
    
    click.echo(instructions)

@cli.command()
@click.option('--log-dir', default='./django_mapper_logs', help='Directory containing runtime logs')
@click.option('--output', default='./django_map', help='Output directory for visualizations')
def visualize_runtime(log_dir, output):
    """Visualize runtime request flow from logged data"""
    click.echo(f"{Fore.CYAN}🔍 Loading runtime logs...{Style.RESET_ALL}")
    
    log_path = Path(log_dir)
    if not log_path.exists():
        click.echo(f"{Fore.RED}❌ Log directory not found: {log_path}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}💡 Run 'django-mapper setup-middleware' for setup instructions{Style.RESET_ALL}")
        sys.exit(1)
    
    # Load and process logs
    log_store = LogStore(log_path / 'runtime_data.json')
    runtime_data = log_store.load()
    
    if not runtime_data:
        click.echo(f"{Fore.YELLOW}⚠️  No runtime data found. Have you explored the app with middleware enabled?{Style.RESET_ALL}")
        sys.exit(1)
    
    # Generate visualizations
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"{Fore.GREEN}🎨 Generating runtime flow visualization...{Style.RESET_ALL}")
    html_gen = HTMLGenerator(runtime_data, runtime_mode=True)
    html_path = output_path / 'runtime_flow.html'
    html_gen.generate(html_path)
    
    click.echo(f"{Fore.GREEN}✅ Runtime visualization saved to: {html_path}{Style.RESET_ALL}")

def _is_django_project(path):
    """Check if directory contains a Django project"""
    return (path / 'manage.py').exists()

def _display_summary(analysis_result):
    """Display analysis summary"""
    stats = analysis_result.get('stats', {})
    
    click.echo(f"\n{Fore.YELLOW}📊 Analysis Summary:{Style.RESET_ALL}")
    click.echo(f"  • URLs: {stats.get('total_urls', 0)}")
    click.echo(f"  • Views: {stats.get('total_views', 0)}")
    click.echo(f"  • Models: {stats.get('total_models', 0)}")
    click.echo(f"  • Apps: {stats.get('total_apps', 0)}")
    click.echo(f"  • Required ENV vars: {stats.get('total_env_vars', 0)}")

if __name__ == '__main__':
    cli()