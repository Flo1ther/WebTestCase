from django.urls import path

from .views import AnalysisHistoryView, AnalyzeTestCaseView, AnalyzeTextView, GenerateTestCasesView, AIConfigurationView, CreateSuggestedCaseView, CoverageAnalysisView, CreateFixView, ApplyFixView, RejectFixView, APITestAssistantView, BenchmarkView

urlpatterns = [
    path('ai/config/', AIConfigurationView.as_view()),
    path('ai/analyses/<int:pk>/create-case/', CreateSuggestedCaseView.as_view()),
    path("ai/analyze-test-case/", AnalyzeTestCaseView.as_view()),
    path("ai/analyze-text/", AnalyzeTextView.as_view()),
    path("ai/generate-test-cases/", GenerateTestCasesView.as_view()),
    path("ai/coverage-analysis/", CoverageAnalysisView.as_view()),
    path("ai/analyses/<int:pk>/fixes/", CreateFixView.as_view()),
    path("ai/fixes/<int:pk>/apply/", ApplyFixView.as_view()),
    path("ai/fixes/<int:pk>/reject/", RejectFixView.as_view()),
    path("ai/api-tests/<int:pk>/assistant/", APITestAssistantView.as_view()),
    path("ai/benchmark/", BenchmarkView.as_view()),
    path("ai/analysis-history/", AnalysisHistoryView.as_view()),
]
