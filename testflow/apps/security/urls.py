from django.urls import path
from . import views as v
urlpatterns = [
    path('api/health/', v.HealthView.as_view()), path('api/config/', v.ConfigView.as_view()), path('api/csrf/', v.CSRFView.as_view()),
    path('api/auth/register/', v.RegisterView.as_view()), path('api/auth/login/', v.LoginView.as_view()),
    path('api/auth/logout/', v.LogoutView.as_view()), path('api/auth/verify-email/', v.VerifyView.as_view()),
    path('api/auth/resend/', v.ResendView.as_view()), path('api/auth/forgot-password/', v.ForgotView.as_view()),
    path('api/auth/reset-password/', v.ResetView.as_view()), path('api/auth/two-factor/', v.OTPView.as_view()),
    path('api/auth/oidc/start/', v.GoogleStartView.as_view()), path('api/auth/oidc/callback/', v.google_callback),
    path('api/me/', v.MeView.as_view()), path('api/auth/me/', v.MeView.as_view()), path('api/profiles/<int:pk>/', v.ProfileView.as_view()),
    path('api/security/password/', v.ChangePasswordView.as_view()), path('api/security/2fa/setup/', v.Setup2FAView.as_view()),
    path('api/security/2fa/enable/', v.Enable2FAView.as_view()), path('api/security/2fa/disable/', v.Disable2FAView.as_view()),
    path('api/security/admin/dashboard/', v.DashboardView.as_view()), path('api/security/admin/users/', v.AdminUsersView.as_view()),
    path('api/security/admin/users/<int:pk>/', v.AdminUserView.as_view()), path('api/security/admin/events/', v.AdminEventsView.as_view()),
]
