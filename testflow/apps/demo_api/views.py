from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from .services import prepare_guided_demo


class StoreHealthView(APIView):
    permission_classes = []
    authentication_classes = []
    def get(self, request):
        return Response({"service": "demo-store", "status": "ok"})


class CheckoutView(APIView):
    """Local training API. It deliberately accepts an invalid payment token for API-test demonstrations."""
    permission_classes = []
    authentication_classes = []
    def post(self, request):
        items = request.data.get("items", [])
        token = request.data.get("payment_token", "")
        if not isinstance(items, list) or not items:
            return Response({"detail": "items are required"}, status=400)
        total = sum(int(item.get("price", 0)) * int(item.get("quantity", 1)) for item in items if isinstance(item, dict))
        # Intentional defect DEMO-API-01: invalid tokens are accepted.
        return Response({"order_id": "DEMO-1001", "status": "paid", "total": total, "payment_token_received": bool(token)}, status=201)


class PrepareDemoView(APIView):
    """Provision reproducible demonstration records from the UI, without fixture imports."""
    def post(self, request):
        if request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Підготувати демонстрацію можуть менеджери й адміністратори.")
        return Response(prepare_guided_demo(request.user), status=201)
