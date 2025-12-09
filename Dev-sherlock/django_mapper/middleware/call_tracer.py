import sys
import functools
from pathlib import Path
from django.conf import settings

class CallTracerMiddleware:
    """
    Middleware to trace function calls during request processing.
    This is optional and can add overhead, so use carefully.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, 'DJANGO_MAPPER', {})
        self.enabled = self.config.get('TRACK_FUNCTION_CALLS', False) and self.config.get('ENABLED', False)
        self.call_stack = []
        self.project_path = Path(settings.BASE_DIR) if hasattr(settings, 'BASE_DIR') else None
    
    def __call__(self, request):
        if not self.enabled or not self.project_path:
            return self.get_response(request)
        
        # Clear call stack for new request
        self.call_stack = []
        
        # Set up tracing
        old_trace = sys.gettrace()
        sys.settrace(self.trace_calls)
        
        try:
            response = self.get_response(request)
        finally:
            # Restore old trace function
            sys.settrace(old_trace)
        
        # Store call stack (you could log this to a file)
        # For now, we just attach it to the request for potential use
        request.call_trace = self.call_stack
        
        return response
    
    def trace_calls(self, frame, event, arg):
        """Trace function calls"""
        if event != 'call':
            return
        
        # Get function info
        code = frame.f_code
        filename = code.co_filename
        function_name = code.co_name
        line_number = frame.f_lineno
        
        # Only trace project files, not stdlib or site-packages
        if not self._should_trace(filename):
            return
        
        # Record the call
        try:
            relative_path = Path(filename).relative_to(self.project_path)
        except ValueError:
            relative_path = filename
        
        self.call_stack.append({
            'file': str(relative_path),
            'function': function_name,
            'line': line_number,
        })
        
        return self.trace_calls
    
    def _should_trace(self, filename: str) -> bool:
        """Determine if we should trace calls in this file"""
        
        # Skip standard library
        if '/lib/python' in filename or '/lib64/python' in filename:
            return False
        
        # Skip site-packages
        if 'site-packages' in filename:
            return False
        
        # Skip Django internals (unless in our project)
        if '/django/' in filename and self.project_path and str(self.project_path) not in filename:
            return False
        
        # Only trace if file is in our project
        if self.project_path:
            try:
                Path(filename).relative_to(self.project_path)
                return True
            except ValueError:
                return False
        
        return False