import { Link, useLocation, useParams } from "react-router-dom";
import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Bot,
  Bug,
  ClipboardCheck,
  FileText,
  FlaskConical,
  Github,
  ListChecks,
  PlayCircle,
  Plus,
} from "lucide-react";
import api, { errorText } from "../services/api";
import { Badge, Empty, Loader, Notice } from "../components/ui";
import { useAuth } from "../context/AuthContext";

type Workspace = {
  project: any;
  summary: any;
  coverage: any[];
  recent_executions: any[];
  recent_defects: any[];
};
type Lists = {
  requirements: any[];
  cases: any[];
  apis: any[];
  executions: any[];
  defects: any[];
};
const tabs = [
  ["overview", "Огляд", BarChart3],
  ["requirements", "Вимоги", ListChecks],
  ["test-cases", "Тесткейси", ClipboardCheck],
  ["api-tests", "API-тести", FlaskConical],
  ["executions", "Виконання", PlayCircle],
  ["defects", "Дефекти", Bug],
  ["analytics", "Аналітика", BarChart3],
  ["reports", "Звіти", FileText],
  ["ci", "GitHub CI", Github],
  ["ai", "AI QA", Bot],
] as const;

const results = (response: any) => response.data.results || response.data || [];

function buildFallback(project: any, lists: Lists) {
  const { requirements, cases, apis, executions, defects } = lists;
  const coverage = requirements.map((requirement) => {
    const manual = cases.filter(
      (testCase) =>
        testCase.requirement === requirement.id ||
        (requirement.test_case_ids || []).includes(testCase.id),
    );
    const apiTests = apis.filter(
      (apiTest) => apiTest.requirement === requirement.id,
    );
    return {
      id: requirement.id,
      key: requirement.key,
      title: requirement.title,
      status: requirement.status,
      manual_test_cases: manual.length,
      api_tests: apiTests.length,
      covered: Boolean(manual.length || apiTests.length),
    };
  });
  const passed = cases.filter((item) => item.status === "PASSED").length;
  const failed = cases.filter((item) => item.status === "FAILED").length;
  const blocked = cases.filter((item) => item.status === "BLOCKED").length;
  const notRun = cases.filter((item) => item.status === "NOT_RUN").length;
  const requirementsCovered = coverage.filter((item) => item.covered).length;
  const openDefects = defects.filter((item) =>
    ["OPEN", "IN_PROGRESS"].includes(item.status),
  );
  const summary = {
    requirements: requirements.length,
    requirements_covered: requirementsCovered,
    requirements_coverage: requirements.length
      ? Math.round((requirementsCovered * 1000) / requirements.length) / 10
      : 0,
    test_cases: cases.length,
    api_tests: apis.length,
    executions: executions.length,
    progress: cases.length
      ? Math.round(((cases.length - notRun) * 1000) / cases.length) / 10
      : 0,
    passed,
    failed,
    blocked,
    not_run: notRun,
    open_defects: openDefects.length,
  };
  const workspace: Workspace = {
    project,
    summary,
    coverage,
    recent_executions: executions
      .slice(0, 8)
      .map((item) => ({
        ...item,
        test_case__title: item.test_case_title,
        tester__username: item.tester_name,
      })),
    recent_defects: openDefects
      .slice(0, 8)
      .map((item) => ({
        ...item,
        test_case__title: item.test_case_title,
        requirement__key: requirements.find(
          (req) => req.id === item.requirement,
        )?.key,
      })),
  };
  const analytics = {
    summary,
    by_priority: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((priority) => ({
      priority,
      count: cases.filter((item) => item.priority === priority).length,
    })),
  };
  const report = {
    report_type: "project-quality-summary",
    failed_test_cases: cases.filter((item) => item.status === "FAILED"),
    open_defects: openDefects,
  };
  const uncovered = coverage.filter((item) => !item.covered);
  const aiSummary = {
    summary: `Проєкт ${project.name}: покрито ${requirementsCovered} з ${requirements.length} вимог (${summary.requirements_coverage}%). Ручних тесткейсів: ${cases.length}; API-тестів: ${apis.length}; відкритих дефектів: ${openDefects.length}.${uncovered.length ? ` Непокриті вимоги: ${uncovered.map((item) => item.key).join(", ")}.` : " Усі наявні вимоги мають щонайменше одну перевірку."}`,
  };
  return { workspace, analytics, report, aiSummary };
}

export function ProjectWorkspace() {
  const { projectId = "" } = useParams();
  const location = useLocation();
  const [workspace, setWorkspace] = useState<Workspace>();
  const [analytics, setAnalytics] = useState<any>();
  const [report, setReport] = useState<any>();
  const [reportType, setReportType] = useState("quality");
  const [aiSummary, setAiSummary] = useState<any>();
  const [lists, setLists] = useState<Lists>({
    requirements: [],
    cases: [],
    apis: [],
    executions: [],
    defects: [],
  });
  const [error, setError] = useState("");
  const [compatibilityMode, setCompatibilityMode] = useState(false);
  const { user } = useAuth();
  const tab = useMemo(
    () => location.pathname.split("/").pop() || "overview",
    [location.pathname],
  );

  const load = async () => {
    if (!projectId) return;
    setError("");
    try {
      // A running server with the former URL configuration can still render this
      // workspace from ordinary REST resources. New project endpoints remain preferred.
      const [
        projectResponse,
        requirementsResponse,
        casesResponse,
        apisResponse,
        executionsResponse,
        defectsResponse,
      ] = await Promise.all([
        api.get(`/projects/${projectId}/`),
        api.get("/requirements/", {
          params: { project: projectId, page_size: 100 },
        }),
        api.get("/test-cases/", {
          params: { project: projectId, page_size: 100 },
        }),
        api.get("/api-tests/", {
          params: { project: projectId, page_size: 100 },
        }),
        api.get("/executions/", {
          params: { project: projectId, page_size: 100 },
        }),
        api.get("/defects/", {
          params: { project: projectId, page_size: 100 },
        }),
      ]);
      const loadedLists: Lists = {
        requirements: results(requirementsResponse),
        cases: results(casesResponse),
        apis: results(apisResponse),
        executions: results(executionsResponse),
        defects: results(defectsResponse),
      };
      setLists(loadedLists);
      try {
        const [
          workspaceResponse,
          analyticsResponse,
          reportResponse,
          aiSummaryResponse,
        ] = await Promise.all([
          api.get(`/projects/${projectId}/workspace/`),
          api.get(`/projects/${projectId}/analytics/`),
          api.get(`/projects/${projectId}/reports/`),
          api.get(`/projects/${projectId}/ai/coverage-summary/`),
        ]);
        setWorkspace(workspaceResponse.data);
        setAnalytics(analyticsResponse.data);
        setReport(reportResponse.data);
        setAiSummary(aiSummaryResponse.data);
        setCompatibilityMode(false);
      } catch {
        const fallback = buildFallback(projectResponse.data, loadedLists);
        setWorkspace(fallback.workspace);
        setAnalytics(fallback.analytics);
        setReport(fallback.report);
        setAiSummary(fallback.aiSummary);
        setCompatibilityMode(true);
      }
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };

  useEffect(() => {
    void load();
  }, [projectId]);
  const loadReport = async (type: string) => {
    if (!projectId) return;
    setReportType(type);
    setError("");
    try {
      const response = await api.get(`/projects/${projectId}/reports/`, {
        params: { type },
      });
      setReport(response.data);
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };
  if (error) return <Notice text={error} />;
  if (!workspace) return <Loader />;
  const { project, summary, coverage } = workspace;
  const title = (label: string, text: string) => (
    <div className="project-section-title">
      <div>
        <h2>{label}</h2>
        <p>{text}</p>
      </div>
    </div>
  );

  return (
    <>
      <div className="project-hero">
        <div>
          <Link className="back" to="/projects">
            ← Усі проєкти
          </Link>
          <span>PROJECT WORKSPACE</span>
          <h1>{project.name}</h1>
          <p>{project.description || "Опис проєкту ще не заповнено."}</p>
        </div>
        <Badge value={project.status || "ACTIVE"} />
      </div>
      <nav className="project-tabs">
        {tabs.map(([key, label, Icon]) => (
          <Link
            key={key}
            className={tab === key ? "active" : ""}
            to={
              key === "overview"
                ? `/projects/${projectId}`
                : `/projects/${projectId}/${key}`
            }
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
      {compatibilityMode && (
        <p className="compatibility-note">
          Проєктний простір працює у режимі сумісності: показники обчислені з
          наявних API-ресурсів.
        </p>
      )}

      {tab === "overview" && (
        <>
          <section className="project-action-row">
            <div>
              <strong>Почніть QA-цикл з вимоги</strong>
              <span>
                Додайте вимогу, створіть тест або відкрийте AI-чернетку в
                контексті цього проєкту.
              </span>
            </div>
            <Link className="primary" to={`/requirements?project=${projectId}`}>
              <Plus size={17} />
              Додати вимогу
            </Link>
          </section>
          <section className="stats project-stats">
            {[
              ["Вимоги", summary.requirements],
              ["Покрито", `${summary.requirements_coverage}%`],
              ["Тесткейси", summary.test_cases],
              ["Виконання", summary.executions],
              ["Пройдено", summary.passed],
              ["Не пройдено", summary.failed],
              ["Відкриті дефекти", summary.open_defects],
            ].map(([name, value]) => (
              <div className="stat" key={String(name)}>
                <span>{name}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </section>
          <section className="dashboard-grid">
            <article className="panel">
              <div className="panel-title">
                <h2>Покриття вимог</h2>
                <strong>{summary.requirements_coverage}%</strong>
              </div>
              <div className="progress">
                <i style={{ width: `${summary.requirements_coverage}%` }} />
              </div>
              <p>
                {summary.requirements_covered} з {summary.requirements} вимог
                мають ручний або API-тест.
              </p>
              <Link to={`/projects/${projectId}/requirements`}>
                Відкрити вимоги
              </Link>
            </article>
            <article className="panel">
              <div className="panel-title">
                <h2>Прогрес виконання</h2>
                <strong>{summary.progress}%</strong>
              </div>
              <div className="progress">
                <i style={{ width: `${summary.progress}%` }} />
              </div>
              <p>
                Passed {summary.passed} · Failed {summary.failed} · Blocked{" "}
                {summary.blocked}
              </p>
              <Link to={`/projects/${projectId}/executions`}>
                Відкрити виконання
              </Link>
            </article>
          </section>
          <section className="dashboard-grid">
            <Compact
              title="Останні виконання"
              empty="У проєкті ще немає виконань."
              items={workspace.recent_executions}
              render={(item: any) => (
                <>
                  <strong>
                    {item.test_case__title || item.test_case_title}
                  </strong>
                  <small>
                    {item.tester__username || item.tester_name} ·{" "}
                    {item.executed_at &&
                      new Date(item.executed_at).toLocaleString("uk-UA")}
                  </small>
                </>
              )}
              badge={(item: any) => <Badge value={item.status} />}
            />
            <Compact
              title="Останні дефекти"
              empty="Відкритих дефектів немає."
              items={workspace.recent_defects}
              render={(item: any) => (
                <>
                  <strong>{item.title}</strong>
                  <small>
                    {item.requirement__key || "Без вимоги"} ·{" "}
                    {item.test_case__title || item.test_case_title}
                  </small>
                </>
              )}
              badge={(item: any) => <Badge value={item.status} />}
            />
          </section>
        </>
      )}
      {tab === "requirements" && (
        <section className="panel">
          {title(
            "Вимоги та покриття",
            "Кожна вимога показує кількість ручних і API-перевірок у цьому проєкті.",
          )}
          <Link
            className="primary inline-create"
            to={`/requirements?project=${projectId}`}
          >
            <Plus size={17} />
            Створити вимогу
          </Link>
          <div className="compact-list">
            {coverage.map((item: any) => (
              <div key={item.id}>
                <span>
                  <strong>
                    {item.key} · {item.title}
                  </strong>
                  <small>
                    Ручні тесткейси: {item.manual_test_cases} · API-тести:{" "}
                    {item.api_tests}
                  </small>
                </span>
                <b
                  className={
                    item.covered ? "stability stable" : "stability unstable"
                  }
                >
                  {item.covered ? "Покрито" : "Не покрито"}
                </b>
              </div>
            ))}
            {!coverage.length && (
              <Empty>Створіть першу вимогу для цього проєкту.</Empty>
            )}
          </div>
        </section>
      )}
      {tab === "test-cases" && (
        <section className="panel">
          {title(
            "Ручні тест-кейси",
            "Сценарії, які перевіряються людиною та можуть бути прив’язані до вимоги.",
          )}
          <Link
            className="primary inline-create"
            to={`/projects/${projectId}/test-cases/create`}
          >
            <Plus size={17} />
            Новий тесткейс
          </Link>
          <div className="compact-list">
            {lists.cases.map((item: any) => (
              <div key={item.id}>
                <span>
                  <Link to={`/projects/${projectId}/test-cases/${item.id}`}>
                    <strong>{item.title}</strong>
                  </Link>
                  <small>
                    {item.requirement_key || "Без вимоги"} ·{" "}
                    {item.assigned_to_name || "Не призначено"}
                  </small>
                </span>
                <Badge value={item.status} />
              </div>
            ))}
            {!lists.cases.length && (
              <Empty>Для проєкту ще немає ручних тест-кейсів.</Empty>
            )}
          </div>
        </section>
      )}
      {tab === "api-tests" && (
        <section className="panel">
          {title(
            "API-тести",
            "Необов’язкові технічні перевірки HTTP-відповідей, пов’язані з вимогами.",
          )}
          <Link
            className="primary inline-create"
            to={`/testing-api?project=${projectId}`}
          >
            <Plus size={17} />
            Новий API-тест
          </Link>
          <div className="compact-list">
            {lists.apis.map((item: any) => (
              <div key={item.id}>
                <span>
                  <strong>
                    {item.method} · {item.name}
                  </strong>
                  <small>
                    {item.requirement_key || "Без вимоги"} · Очікувано HTTP{" "}
                    {item.expected_status}
                  </small>
                </span>
              </div>
            ))}
            {!lists.apis.length && (
              <Empty>API-тести для цього проєкту не додані.</Empty>
            )}
          </div>
        </section>
      )}
      {tab === "executions" && (
        <Compact
          title="Історія виконань"
          empty="Виконань ще немає."
          items={lists.executions}
          render={(item: any) => (
            <>
              <strong>{item.test_case_title}</strong>
              <small>
                {item.tester_name} · {item.actual_result}
              </small>
            </>
          )}
          badge={(item: any) => <Badge value={item.status} />}
        />
      )}
      {tab === "defects" && (
        <Compact
          title="Дефекти проєкту"
          empty="Дефектів ще немає."
          items={lists.defects}
          render={(item: any) => (
            <>
              <strong>{item.title}</strong>
              <small>
                {item.test_case_title} · {item.description}
              </small>
            </>
          )}
          badge={(item: any) => <Badge value={item.status} />}
        />
      )}
      {tab === "analytics" && (
        <section className="panel">
          {title(
            "Аналітика проєкту",
            "Метрики обчислені лише за даними цього проєкту.",
          )}
          <section className="stats project-stats">
            {[
              ["Ручні тести", analytics?.summary.test_cases],
              ["API-тести", analytics?.summary.api_tests],
              ["Виконання", analytics?.summary.executions],
              ["Прогрес", `${analytics?.summary.progress || 0}%`],
              ["Дефекти", analytics?.summary.open_defects],
            ].map(([name, value]) => (
              <div className="stat" key={String(name)}>
                <span>{name}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </section>
          <h3>Розподіл за пріоритетом</h3>
          <div className="compact-list">
            {analytics?.by_priority?.map((item: any) => (
              <div key={item.priority}>
                <strong>{item.priority}</strong>
                <b>{item.count}</b>
              </div>
            ))}
          </div>
        </section>
      )}
      {tab === "reports" && (
        <section className="panel">
          {title(
            "Звіти проєкту",
            "Тип звіту створюється на backend через Factory Method із тих самих даних проєкту.",
          )}
          <label>
            Тип звіту
            <select
              value={reportType}
              onChange={(event) => void loadReport(event.target.value)}
            >
              <option value="quality">Якість і відкриті дефекти</option>
              <option value="traceability">Трасування та покриття вимог</option>
              <option value="execution">Прогрес тестових прогонів</option>
            </select>
          </label>
          {report?.report_type === "project-quality-summary" && (
            <>
              <p>
                <strong>Невдалі тест-кейси:</strong>{" "}
                {report?.failed_test_cases?.length || 0}.{" "}
                <strong>Відкриті дефекти:</strong>{" "}
                {report?.open_defects?.length || 0}.
              </p>
              <div className="compact-list">
                {report?.open_defects?.map((item: any) => (
                  <div key={item.id}>
                    <span>
                      <strong>{item.title}</strong>
                      <small>
                        {item.requirement__key || "Без вимоги"} ·{" "}
                        {item.test_case__title || item.test_case_title}
                      </small>
                    </span>
                    <Badge value={item.status} />
                  </div>
                ))}
              </div>
            </>
          )}
          {report?.report_type === "project-traceability" && (
            <>
              <p>
                <strong>Покриття вимог:</strong>{" "}
                {report?.summary?.requirements_covered} з{" "}
                {report?.summary?.requirements} (
                {report?.summary?.requirements_coverage}%).
              </p>
              <div className="compact-list">
                {report?.coverage_matrix?.map((item: any) => (
                  <div key={item.id}>
                    <span>
                      <strong>
                        {item.key} · {item.title}
                      </strong>
                      <small>
                        Ручні: {item.manual_test_cases} · API: {item.api_tests}
                      </small>
                    </span>
                    <b
                      className={
                        item.covered ? "stability stable" : "stability unstable"
                      }
                    >
                      {item.covered ? "Покрито" : "Не покрито"}
                    </b>
                  </div>
                ))}
              </div>
            </>
          )}
          {report?.report_type === "project-execution-progress" && (
            <>
              <p>
                <strong>Прогрес проєкту:</strong> {report?.summary?.progress}% ·
                виконань: {report?.summary?.executions}.
              </p>
              <div className="compact-list">
                {report?.test_runs?.map((item: any) => (
                  <div key={item.id}>
                    <span>
                      <strong>{item.name}</strong>
                      <small>
                        {item.completed_test_cases} з {item.total_test_cases}{" "}
                        тестів · {item.progress}%
                      </small>
                    </span>
                    <Badge value={item.status} />
                  </div>
                ))}
                {!report?.test_runs?.length && (
                  <Empty>У проєкті ще немає тестових прогонів.</Empty>
                )}
              </div>
            </>
          )}
        </section>
      )}
      {tab === "ci" && (
        <ProjectCI
          projectId={projectId}
          testCases={lists.cases}
          canManage={user?.role !== "TESTER"}
        />
      )}
      {tab === "ai" && (
        <section className="panel">
          {title(
            "AI QA-помічник проєкту",
            "Підсумок покриття доступний без LLM; генерація та review відкриваються в контексті цього проєкту.",
          )}
          <p className="ai-summary">
            <Bot size={20} />
            {aiSummary?.summary}
          </p>
          <p>
            <strong>Контекст для AI:</strong>{" "}
            {project.ai_context ||
              "Не заповнено. Додайте домен, терміни й правила проєкту в налаштуваннях проєкту."}
          </p>
          <Link className="primary" to={`/ai-assistant?project=${projectId}`}>
            Відкрити AI QA-помічник
          </Link>
        </section>
      )}
    </>
  );
}

function Compact({
  title,
  items,
  empty,
  render,
  badge,
}: {
  title: string;
  items: any[];
  empty: string;
  render: (item: any) => any;
  badge?: (item: any) => any;
}) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <div className="compact-list">
        {items.map((item) => (
          <div key={item.id}>
            <span>{render(item)}</span>
            {badge?.(item)}
          </div>
        ))}
        {!items.length && <Empty>{empty}</Empty>}
      </div>
    </section>
  );
}

function ProjectCI({
  projectId,
  testCases,
  canManage,
}: {
  projectId: string;
  testCases: any[];
  canManage: boolean;
}) {
  const [data, setData] = useState<any>();
  const [form, setForm] = useState({
    repository_full_name: "",
    repository_url: "",
    default_branch: "main",
    workflow_file: ".github/workflows/webtestcase.yml",
    is_enabled: true,
  });
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState("PASSED");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = async () => {
    try {
      const response = await api.get(`/projects/${projectId}/github/`);
      setData(response.data);
      if (response.data.integration) setForm(response.data.integration);
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };
  useEffect(() => {
    void load();
  }, [projectId]);
  const save = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await api.post(`/projects/${projectId}/github/`, form);
      setMessage(
        "Репозиторій прив’язано. Додайте секрет і callback до GitHub Actions за шаблоном із README.",
      );
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };
  const simulate = async () => {
    setError("");
    setMessage("");
    const testCase = testCases.find((item) => String(item.id) === selected);
    if (!testCase?.automation_key)
      return setError("Оберіть тесткейс із заповненим ключем автоматизації.");
    try {
      const response = await api.post(
        `/projects/${projectId}/github/simulate/`,
        {
          tests: [
            {
              automation_key: testCase.automation_key,
              status: result,
              actual_result: `Локальна симуляція GitHub Actions: ${result}`,
              comment:
                "Результат надійшов через той самий backend mapper, що й callback CI.",
            },
          ],
        },
      );
      setMessage(
        `Створено CI-прогін #${response.data.provider_run_id} та execution для «${testCase.title}».`,
      );
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };
  if (!canManage)
    return (
      <section className="panel">
        <h2>GitHub CI</h2>
        <p>
          Конфігурацію репозиторію та автоматичні CI-результати може переглядати
          й змінювати менеджер або адміністратор.
        </p>
      </section>
    );
  const automatedCases = testCases.filter((item) => item.automation_key);
  return (
    <section className="panel ci-panel">
      <div className="project-section-title">
        <div>
          <h2>GitHub Actions та CI-результати</h2>
          <p>
            GitHub запускає тести у репозиторії, а WebTestCase зберігає лише
            підписані результати як Test Run та execution history.
          </p>
        </div>
        <Github size={26} />
      </div>
      {error && <Notice text={error} />}{" "}
      {message && <p className="success-note">{message}</p>}
      {!data ? (
        <Loader />
      ) : (
        <>
          <form className="form-panel compact-form" onSubmit={save}>
            <div className="form-grid">
              <label>
                Репозиторій owner/repository
                <input
                  value={form.repository_full_name || ""}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      repository_full_name: event.target.value,
                    })
                  }
                  placeholder="team/shop-api"
                  required
                />
              </label>
              <label>
                URL репозиторію
                <input
                  value={form.repository_url || ""}
                  onChange={(event) =>
                    setForm({ ...form, repository_url: event.target.value })
                  }
                  placeholder="https://github.com/team/shop-api"
                />
              </label>
              <label>
                Основна гілка
                <input
                  value={form.default_branch || "main"}
                  onChange={(event) =>
                    setForm({ ...form, default_branch: event.target.value })
                  }
                  required
                />
              </label>
              <label>
                Workflow file
                <input
                  value={form.workflow_file || ""}
                  onChange={(event) =>
                    setForm({ ...form, workflow_file: event.target.value })
                  }
                  placeholder=".github/workflows/webtestcase.yml"
                />
              </label>
            </div>
            <button type="submit" className="primary">
              {data.integration
                ? "Зберегти інтеграцію"
                : "Прив’язати репозиторій"}
            </button>
          </form>
          {data.integration && (
            <>
              <div className="ci-callback">
                <strong>CI callback URL</strong>
                <code>{data.callback_url}</code>
                <p>
                  {data.secret_configured
                    ? "Секрет callback налаштований на сервері."
                    : "Секрет не налаштовано: реальний callback GitHub буде відхилено. Додайте GITHUB_WEBHOOK_SECRET у .env та перезапустіть backend."}
                </p>
                <small>
                  GitHub Actions не бачить localhost. Для реального зовнішнього
                  репозиторію вкажіть у PUBLIC_API_URL публічний HTTPS
                  tunnel/domain. Локальна симуляція нижче працює без тунелю.
                </small>
              </div>
              <div className="ci-simulation">
                <h3>Локальна демонстрація CI</h3>
                <p>
                  Створює Test Run та execution через той самий mapper, що
                  обробляє підписаний callback від GitHub Actions.
                </p>
                <select
                  value={selected}
                  onChange={(event) => setSelected(event.target.value)}
                >
                  <option value="">Оберіть тесткейс з automation key</option>
                  {automatedCases.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.automation_key} · {item.title}
                    </option>
                  ))}
                </select>
                <select
                  value={result}
                  onChange={(event) => setResult(event.target.value)}
                >
                  <option value="PASSED">PASSED</option>
                  <option value="FAILED">FAILED</option>
                  <option value="BLOCKED">BLOCKED</option>
                </select>
                <button className="primary" type="button" onClick={simulate}>
                  Симулювати CI-результат
                </button>
                {!automatedCases.length && (
                  <p className="warning-note">
                    Спершу вкажіть «Ключ автоматизації» хоча б для одного
                    тесткейсу.
                  </p>
                )}
              </div>
              <h3>Останні workflow runs</h3>
              <div className="compact-list">
                {data.recent_runs.map((item: any) => (
                  <div key={item.id}>
                    <span>
                      <strong>
                        {item.workflow_name || "GitHub Actions"} · #
                        {item.provider_run_id}
                      </strong>
                      <small>
                        {item.source === "LOCAL_SIMULATION"
                          ? "Локальна симуляція"
                          : `${item.branch || "—"} · ${item.commit_sha || "—"}`}{" "}
                        {item.unmatched_automation_keys?.length
                          ? ` · Не знайдено ключі: ${item.unmatched_automation_keys.join(", ")}`
                          : ""}
                      </small>
                    </span>
                    <span className="ci-run-status">
                      <Badge value={item.conclusion} />
                      {item.test_run_id && (
                        <Link to={`/test-runs`}>
                          Test Run #{item.test_run_id}
                        </Link>
                      )}
                    </span>
                  </div>
                ))}
                {!data.recent_runs.length && (
                  <Empty>CI-результатів для цього проєкту ще немає.</Empty>
                )}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
