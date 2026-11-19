from django.urls import path
from .views import CheckoutView, StoreHealthView, PrepareDemoView
urlpatterns = [path("demo-store/health/", StoreHealthView.as_view()), path("demo-store/checkout/", CheckoutView.as_view()), path("demo/prepare/", PrepareDemoView.as_view())]
