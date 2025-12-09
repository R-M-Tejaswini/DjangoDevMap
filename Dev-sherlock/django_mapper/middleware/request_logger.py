import json
import time
import traceback
from pathlib import Path
from django.conf import settings
from django.urls import resolve
from django.db import connection

class RequestLoggerMiddleware:
    """Middleware to log all requests and their flow through the application"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, 'DJANGO_MAPPER', {})
        self.enabled = self.config.get('ENABLED', settings.DEBUG)
        self.log_dir = Path(self.config.get('LOG_DIR', './django_mapper_logs'))
        self.exclude_paths = self.config.get('EXCLUDE_PATHS', ['/static/', '/media/'])
        self.track_queries = self.config.get('TRACK_QUERIES', True)
        
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / 'requests.jsonl'
    
    def __call__(self, request):
        if not self.enabled or self._should_exclude(request.path):
            return self.get_response(request)
        
        # Start timing
        start_time = time.time()
        
        # Capture request info
        request_data = self._capture_request_info(request)
        
        # Reset query counter
        if self.track_queries:
            connection.queries_log.clear()
        
        # Process request
        try:
            response = self.get_response(request)
            request_data['response_status'] = response.status_code
            request_data['success'] = True
        except Exception as e:
            request_data['error'] = str(e)
            request_data['traceback'] = traceback.format_exc()
            request_data['success'] = False
            raise
        finally:
            # Calculate duration
            request_data['duration_ms'] = (time.time() - start_time) * 1000
            
            # Capture queries
            if self.track_queries:
                request_data['queries'] = self._capture_queries()
            
            # Log the request
            self._log_request(request_data)
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from logging"""
        for exclude_pattern in self.exclude_paths:
            if exclude_pattern in path:
                return True
        return False
    
    def _capture_request_info(self, request) -> dict:
        """Capture detailed request information"""
        
        # Resolve URL to view
        try:
            resolved = resolve(request.path)
            view_name = self._get_view_name(resolved)
            url_name = resolved.url_name
            app_name = resolved.app_name
        except:
            view_name = None
            url_name = None
            app_name = None
        
        return {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'full_path': request.get_full_path(),
            'view_name': view_name,
            'url_name': url_name,
            'app_name': app_name,
            'user': str(request.user) if hasattr(request, 'user') else None,
            'is_authenticated': request.user.is_authenticated if hasattr(request, 'user') else False,
            'get_params': dict(request.GET),
            'post_params': self._sanitize_post_data(dict(request.POST)),
            'headers': self._capture_headers(request),
            'session_key': request.session.session_key if hasattr(request, 'session') else None,
        }
    
    def _get_view_name(self, resolved) -> str:
        """Get the view name from resolved URL"""
        view = resolved.func
        
        # For class-based views
        if hasattr(view, 'view_class'):
            return f"{view.view_class.__module__}.{view.view_class.__name__}"
        
        # For function-based views
        return f"{view.__module__}.{view.__name__}"
    
    def _capture_headers(self, request) -> dict:
        """Capture relevant headers (excluding sensitive ones)"""
        headers = {}
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                if header_name not in sensitive_headers:
                    headers[header_name] = value
        
        return headers
    
    def _sanitize_post_data(self, data: dict) -> dict:
        """Remove sensitive data from POST params"""
        sensitive_keys = ['password', 'token', 'secret', 'api_key', 'credit_card']
        sanitized = {}
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _capture_queries(self) -> list:
        """Capture database queries executed during request"""
        queries = []
        
        for query in connection.queries:
            queries.append({
                'sql': query['sql'],
                'time': float(query['time']),
            })
        
        return queries
    
    def _log_request(self, request_data: dict):
        """Write request data to log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(request_data) + '\n')
        except Exception as e:
            print(f"Failed to log request: {e}")