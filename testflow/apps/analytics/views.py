from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from .serializers import AnalyticsFilterSerializer
from .services import AnalyticsService


class AnalyticsBaseView(APIView):
    def service(self, request):
        serializer = AnalyticsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return AnalyticsService(request.user, serializer.validated_data)


@extend_schema(responses=OpenApiTypes.OBJECT)
class OverviewView(AnalyticsBaseView):
    def get(self, request): return Response(self.service(request).overview())


@extend_schema(responses=OpenApiTypes.OBJECT)
class ExecutionTrendsView(AnalyticsBaseView):
    def get(self, request): return Response(self.service(request).execution_trends())


@extend_schema(responses=OpenApiTypes.OBJECT)
class ProjectComparisonView(AnalyticsBaseView):
    def get(self, request): return Response(self.service(request).project_comparison())


@extend_schema(responses=OpenApiTypes.OBJECT)
class TestStabilityView(AnalyticsBaseView):
    def get(self, request): return Response(self.service(request).test_stability())


@extend_schema(responses=OpenApiTypes.OBJECT)
class DefectTrendsView(AnalyticsBaseView):
    def get(self, request): return Response(self.service(request).defect_trends())


@extend_schema(responses=OpenApiTypes.OBJECT)
class TesterPerformanceView(AnalyticsBaseView):
    def get(self, request): return Response(self.service(request).tester_performance())
