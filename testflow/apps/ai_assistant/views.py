from django.db import transaction
from django.utils import timezone
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.audit.services import record_action
from apps.test_cases.models import TestCase
from apps.requirements.models import Requirement
from apps.executions.models import APITest
from apps.projects.models import Project
from .models import AIAnalysis, AIFixProposal, AIBenchmarkRun
from .serializers import AIAnalysisSerializer, AnalyzeTestCaseSerializer, AnalyzeTextSerializer, GenerateTestCasesSerializer, CoverageSerializer, FixRequestSerializer, AIFixProposalSerializer
from .services import AIService
from .copilot import CoverageAnalyzer
from .benchmark import run_benchmark


def allowed_cases(user):
    return TestCase.objects.all() if user.role in {"ADMIN", "MANAGER"} else TestCase.objects.filter(assigned_to=user)


class AIBaseView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai"
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method == 'POST':
            from apps.security.services import rate_limit, ip_of
            rate_limit('ai', f'{request.user.pk}:{ip_of(request)}', 20, 3600)


@extend_schema(request=AnalyzeTestCaseSerializer, responses=AIAnalysisSerializer)
class AnalyzeTestCaseView(AIBaseView):
    def post(self, request):
        serializer = AnalyzeTestCaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test_case = serializer.validated_data["test_case"]
        if not allowed_cases(request.user).filter(pk=test_case.pk).exists():
            raise PermissionDenied('У вас немає доступу до цього тесткейсу.')
        service = AIService()
        result = service.analyze_test_case(test_case)
        with transaction.atomic():
            analysis = AIAnalysis.objects.create(project=test_case.project, test_case=test_case, requested_by=request.user, analysis_type=AIAnalysis.AnalysisType.ANALYZE, provider="local" if service.is_local else service.provider, model_name=service.model, result=result)
            record_action(user=request.user, action="AI_ANALYZED_TEST_CASE", entity_type="TestCase", entity_id=test_case.id, metadata={"analysis_id": analysis.id, "mode": result.get("mode")})
        return Response(AIAnalysisSerializer(analysis).data, status=201)


@extend_schema(request=AnalyzeTextSerializer, responses=AIAnalysisSerializer)
class AnalyzeTextView(AIBaseView):
    def post(self, request):
        serializer = AnalyzeTextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AIService()
        result = service.analyze_text(serializer.validated_data['scenario'])
        with transaction.atomic():
            analysis = AIAnalysis.objects.create(
                requested_by=request.user,
                analysis_type=AIAnalysis.AnalysisType.ANALYZE,
                provider='local' if service.is_local else service.provider,
                model_name=service.model,
                result=result,
            )
            record_action(user=request.user, action='AI_ANALYZED_TEXT', entity_type='AIAnalysis', entity_id=analysis.id, metadata={'mode': result.get('mode')})
        return Response(AIAnalysisSerializer(analysis).data, status=201)


@extend_schema(request=GenerateTestCasesSerializer, responses=AIAnalysisSerializer)
class GenerateTestCasesView(AIBaseView):
    def post(self, request):
        if request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied('Готувати пропозиції можуть лише менеджери й адміністратори.')
        serializer = GenerateTestCasesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AIService()
        requirement = serializer.validated_data.get("requirement")
        project_id = serializer.validated_data.get("project_id") or (requirement.project_id if requirement else None)
        project = Project.objects.filter(pk=project_id).first() if project_id else None
        # New project workspace always supplies project_id. Keep old saved draft links
        # readable until the frontend is migrated; a project becomes mandatory on accept.
        if not project and project_id:
            raise ValidationError({"project_id": "Проєкт не знайдено."})
        if requirement and requirement.project_id != project.id:
            raise ValidationError({"requirement_id": "Вимога повинна належати вибраному проєкту."})
        options={key: serializer.validated_data[key] for key in ("test_type", "priority", "detail_level", "suite_id", "api_test_id") if serializer.validated_data.get(key) is not None}
        if project:
            options["project_context"] = project.ai_context[:2400]
            options["project_name"] = project.name
        if requirement:
            options["requirement"] = {"key": requirement.key, "title": requirement.title, "description": requirement.description[:4000]}
        result = service.generate_test_cases(serializer.validated_data["feature_description"], serializer.validated_data["count"], options)
        result["generation_options"] = options
        with transaction.atomic():
            analysis = AIAnalysis.objects.create(project=project, requested_by=request.user, requirement=requirement, analysis_type=AIAnalysis.AnalysisType.GENERATE, provider="local" if service.is_local else service.provider, model_name=service.model, result=result)
            record_action(user=request.user, action="AI_GENERATED_SUGGESTIONS", entity_type="AIAnalysis", entity_id=analysis.id, metadata={"mode": result.get("mode")})
        return Response(AIAnalysisSerializer(analysis).data, status=201)


class CoverageAnalysisView(AIBaseView):
    def post(self, request):
        if request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Coverage analysis доступний менеджерам і адміністраторам.")
        serializer=CoverageSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        requirement=serializer.validated_data["requirement"]
        result=CoverageAnalyzer().analyze(requirement)
        analysis=AIAnalysis.objects.create(project=requirement.project, requirement=requirement, requested_by=request.user, analysis_type=AIAnalysis.AnalysisType.COVERAGE, provider="deterministic", model_name="coverage-rules-v1", result=result)
        record_action(user=request.user, action="AI_COVERAGE_ANALYZED", entity_type="Requirement", entity_id=requirement.id, metadata={"analysis_id":analysis.id})
        return Response(AIAnalysisSerializer(analysis).data, status=201)


class CreateFixView(AIBaseView):
    def post(self, request, pk):
        if request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Застосовувати AI-виправлення можуть лише менеджери й адміністратори.")
        data=FixRequestSerializer(data=request.data); data.is_valid(raise_exception=True)
        analysis=AIAnalysis.objects.select_related("test_case").filter(pk=pk, analysis_type=AIAnalysis.AnalysisType.ANALYZE).first()
        if not analysis or not analysis.test_case: raise NotFound("Аналіз тесткейсу не знайдено.")
        item=next((value for value in analysis.result.get("findings",[]) if value.get("id")==data.validated_data["finding_id"]),None)
        if not item or not item.get("fix") or not item["fix"].get("after"):
            raise ValidationError("Для цього зауваження немає безпечної конкретної пропозиції.")
        fix, created=AIFixProposal.objects.get_or_create(analysis=analysis,finding_id=item["id"],defaults={"target_field":item["field"],"before":item["fix"].get("before",item.get("evidence", "")),"after":data.validated_data.get("after",item["fix"]["after"]),"rationale":item["recommendation"],"related_fields":item["fix"].get("related_fields",[]),"test_case_updated_at":analysis.test_case.updated_at})
        if not created and data.validated_data.get("after") and fix.status==AIFixProposal.Status.PROPOSED:
            fix.after=data.validated_data["after"];fix.save(update_fields=["after"])
        return Response(AIFixProposalSerializer(fix).data, status=201 if created else 200)


class ApplyFixView(AIBaseView):
    def post(self, request, pk):
        if request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Застосовувати AI-виправлення можуть лише менеджери й адміністратори.")
        with transaction.atomic():
            fix=AIFixProposal.objects.select_for_update().select_related("analysis__test_case").filter(pk=pk).first()
            if not fix: raise NotFound()
            if fix.status!=AIFixProposal.Status.PROPOSED: raise ValidationError("Ця пропозиція вже оброблена.")
            case=fix.analysis.test_case
            if not case or case.updated_at != fix.test_case_updated_at:
                raise ValidationError("Тесткейс змінено після аналізу. Запустіть review повторно, щоб не перезаписати нові дані.")
            if fix.target_field in {"title","description","preconditions","expected_result"}:
                setattr(case,fix.target_field,fix.after);case.save()
            else:
                import re
                match=re.fullmatch(r"steps\.(\d+)\.(action|expected_result)",fix.target_field)
                if not match: raise ValidationError("Ціль виправлення не підтримується.")
                step=case.steps.order_by("step_number")[int(match.group(1))]
                setattr(step,match.group(2),fix.after);step.save()
                case.save()
            fix.status=AIFixProposal.Status.APPLIED;fix.decided_by=request.user;fix.decided_at=timezone.now();fix.save(update_fields=["status","decided_by","decided_at"])
            record_action(user=request.user,action="AI_FIX_APPLIED",entity_type="TestCase",entity_id=case.id,metadata={"fix_id":fix.id,"field":fix.target_field})
        return Response(AIFixProposalSerializer(fix).data)


class RejectFixView(AIBaseView):
    def post(self, request, pk):
        if request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Недоступно.")
        fix=AIFixProposal.objects.filter(pk=pk,status=AIFixProposal.Status.PROPOSED).first()
        if not fix: raise NotFound()
        fix.status=AIFixProposal.Status.REJECTED;fix.decided_by=request.user;fix.decided_at=timezone.now();fix.save(update_fields=["status","decided_by","decided_at"])
        return Response(AIFixProposalSerializer(fix).data)


class APITestAssistantView(AIBaseView):
    def post(self, request, pk):
        if request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("API Assistant доступний менеджерам і адміністраторам.")
        test=APITest.objects.filter(pk=pk).prefetch_related("executions").first()
        if not test: raise NotFound()
        last=test.executions.order_by("-executed_at").first()
        assertions=[{"path":"status","equals":"ok"}] if test.expected_status==200 and test.method=="GET" else []
        result={"api_test":{"id":test.id,"name":test.name,"method":test.method,"url":test.url},"suggested_assertions":assertions,"suggested_scenarios":["Перевірити очікуваний HTTP status.","Перевірити негативний запит з невалідними або відсутніми даними.","Перевірити граничні значення параметрів."],"failure_explanation":None,"scope":"Пропозиції не запускають API й не визначають PASS/FAIL."}
        if last and last.status!="PASSED": result["failure_explanation"]={"expected_status":test.expected_status,"actual_status":last.actual_status,"failed_assertions":[item for item in last.assertion_results if not item.get("passed")],"next_checks":["Зіставити контракт endpoint із фактичною відповіддю.","Перевірити request body та тестові дані."]}
        analysis=AIAnalysis.objects.create(requested_by=request.user,analysis_type=AIAnalysis.AnalysisType.API,provider="deterministic",model_name="api-assistant-v1",result=result)
        return Response(AIAnalysisSerializer(analysis).data,status=201)


class BenchmarkView(AIBaseView):
    def post(self, request):
        if request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Benchmark доступний менеджерам і адміністраторам.")
        metrics, details=run_benchmark()
        service=AIService()
        run=AIBenchmarkRun.objects.create(provider="deterministic", model_name="qa-review-rules-v1", metrics=metrics, details=details, requested_by=request.user)
        record_action(user=request.user, action="AI_BENCHMARK_RAN", entity_type="AIBenchmarkRun", entity_id=run.id, metadata=metrics)
        return Response({"id":run.id,"provider":run.provider,"model_name":run.model_name,"dataset_version":run.dataset_version,"metrics":metrics,"details":details},status=201)

    def get(self, request):
        if request.user.role not in {"ADMIN", "MANAGER"}: raise PermissionDenied("Benchmark доступний менеджерам і адміністраторам.")
        return Response([{"id":run.id,"provider":run.provider,"model_name":run.model_name,"dataset_version":run.dataset_version,"metrics":run.metrics,"created_at":run.created_at} for run in AIBenchmarkRun.objects.all()[:20]])


class AIConfigurationView(APIView):
    def get(self,request):return Response(AIService().configuration())

class CreateSuggestedCaseView(AIBaseView):
    def post(self,request,pk):
        if request.user.role not in {'ADMIN','MANAGER'}:raise PermissionDenied('Створювати тесткейси можуть лише менеджери й адміністратори.')
        from apps.test_cases.serializers import TestCaseSerializer
        index=request.data.get('index')
        if type(index) is not int or index<0:raise ValidationError('Недійсний індекс пропозиції.')
        with transaction.atomic():
            analysis=AIAnalysis.objects.select_for_update().filter(pk=pk,analysis_type__in=['GENERATE','COVERAGE']).first()
            if not analysis:raise NotFound()
            if analysis.requested_by_id!=request.user.pk and request.user.role!='ADMIN':raise PermissionDenied('Це пропозиція іншого користувача.')
            suggestions=analysis.result.get('suggestions',[])
            if index>=len(suggestions):raise ValidationError('Пропозицію не знайдено.')
            previous=analysis.result.get('created_cases',{}).get(str(index))
            if previous:return Response({'id':previous,'already_created':True})
            suggestion=suggestions[index]
            if not AIService.valid_suggestion(suggestion):raise ValidationError('Стара або неповна пропозиція. Згенеруйте нову.')
            payload={k:suggestion[k] for k in ['title','description','preconditions','expected_result','priority']}
            project_id=request.data.get('project', analysis.project_id)
            payload.update(project=project_id, requirement=analysis.requirement_id, status='NOT_RUN',steps=[dict(step,step_number=i+1) for i,step in enumerate(suggestion['steps'])])
            serializer=TestCaseSerializer(data=payload,context={'request':request});serializer.is_valid(raise_exception=True)
            case=serializer.save(created_by=request.user)
            if not analysis.project_id:
                analysis.project = case.project
                analysis.save(update_fields=["project"])
            if analysis.requirement:
                if analysis.requirement.project_id != case.project_id:
                    raise ValidationError('Проєкт тесткейсу має відповідати проєкту пов’язаної вимоги.')
                analysis.requirement.test_cases.add(case)
            suite_id=request.data.get('suite')
            if suite_id:
                from apps.test_cases.models import TestSuite
                suite=TestSuite.objects.filter(pk=suite_id, project_id=case.project_id).first()
                if not suite: raise ValidationError('Test Suite має належати проєкту тесткейсу.')
                suite.test_cases.add(case)
            analysis.result.setdefault('created_cases',{})[str(index)]=case.pk
            analysis.save(update_fields=['result'])
            record_action(user=request.user,action='AI_SUGGESTION_ACCEPTED',entity_type='TestCase',entity_id=case.pk,metadata={'analysis_id':analysis.pk})
        return Response({'id':case.pk},status=201)

class AnalysisHistoryView(generics.ListAPIView):
    serializer_class = AIAnalysisSerializer
    filterset_fields = ["analysis_type", "test_case", "project"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AIAnalysis.objects.none()
        qs = AIAnalysis.objects.select_related("project", "test_case", "requested_by")
        return qs if self.request.user.role in {"ADMIN", "MANAGER"} else qs.filter(requested_by=self.request.user, test_case__assigned_to=self.request.user)
