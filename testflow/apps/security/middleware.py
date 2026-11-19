from django.contrib.auth import logout

class SessionPolicyMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if request.user.is_authenticated:
            if request.user.manual_blocked or request.session.get('auth_version') != request.user.auth_version:
                logout(request)
        return self.get_response(request)

class SecurityHeadersMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        response['Referrer-Policy'] = 'no-referrer'
        response['X-Frame-Options'] = 'DENY'
        response['Cache-Control'] = 'no-store'
        return response
