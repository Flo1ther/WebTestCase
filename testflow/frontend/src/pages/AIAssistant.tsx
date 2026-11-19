import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { errorText } from "../services/api";
import type { AIAnalysis, Project, AIFixProposal } from "../types";
import { Empty, Loader, Notice } from "../components/ui";
import { AIResult } from "../components/AIResult";
import { useAuth } from "../context/AuthContext";

type Requirement = { id: number; key: string; title: string; project: number };
type TestCase = { id: number; title: string; project: number };
type Suite = { id: number; name: string; project: number };
type Tab = "generate" | "review" | "scenario" | "history";
const tabs: [Tab, string][] = [
  ["generate", "Створити тесткейси"],
  ["review", "Перевірити тесткейс"],
  ["scenario", "Перевірити вимогу"],
  ["history", "Історія ШІ"],
];

export function AIAssistant() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const preset = params.get("project") || "";
  const [tab, setTab] = useState<Tab>("generate"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [config, setConfig] = useState<any>(),
    [history, setHistory] = useState<AIAnalysis[]>([]),
    [active, setActive] = useState<AIAnalysis>(),
    [projects, setProjects] = useState<Project[]>([]),
    [requirements, setRequirements] = useState<Requirement[]>([]),
    [cases, setCases] = useState<TestCase[]>([]),
    [suites, setSuites] = useState<Suite[]>([]),
    [project, setProject] = useState(preset),
    [suite, setSuite] = useState("");
  const canManage = user?.role !== "TESTER";
  const load = () =>
    api
      .get("/ai/analysis-history/", {
        params: { page_size: 50, project: preset || undefined },
      })
      .then((r) => setHistory(r.data.results));
  useEffect(() => {
    setProject(preset);
    setError("");
    load().catch((e) => setError(errorText(e)));
    api
      .get("/ai/config/")
      .then((r) => setConfig(r.data))
      .catch((e) => setError(errorText(e)));
    api
      .get("/projects/?page_size=100")
      .then((r) => setProjects(r.data.results))
      .catch((e) => setError(errorText(e)));
    api
      .get("/requirements/", {
        params: { page_size: 100, project: preset || undefined },
      })
      .then((r) => setRequirements(r.data.results))
      .catch((e) => setError(errorText(e)));
    api
      .get("/test-cases/", {
        params: { page_size: 100, project: preset || undefined },
      })
      .then((r) => setCases(r.data.results))
      .catch((e) => setError(errorText(e)));
    if (canManage)
      api
        .get("/test-suites/?page_size=100")
        .then((r) => setSuites(r.data.results))
        .catch((e) => setError(errorText(e)));
  }, [preset]);
  const request = async (path: string, payload: any) => {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post(path, payload);
      setActive(data);
      try {
        await load();
      } catch {
        /* The operation succeeded; history can be refreshed later without a false error. */
      }
      setError("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const generate = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    void request("/ai/generate-test-cases/", {
      project_id: Number(project),
      feature_description: f.get("description"),
      count: Number(f.get("count")),
      requirement_id: f.get("requirement")
        ? Number(f.get("requirement"))
        : null,
      test_type: f.get("test_type"),
      priority: f.get("priority"),
      detail_level: f.get("detail"),
      suite_id: null,
      api_test_id: null,
    });
  };
  const createCase = async (item: AIAnalysis, index: number) => {
    if (!project) return;
    setBusy(true);
    try {
      await api.post(`/ai/analyses/${item.id}/create-case/`, {
        index,
        project: Number(project),
        suite: suite ? Number(suite) : null,
      });
      await load();
      setActive(undefined);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const proposeFix = async (item: AIAnalysis, finding: any, after: string) => {
    setBusy(true);
    try {
      await api.post(`/ai/analyses/${item.id}/fixes/`, {
        finding_id: finding.id,
        after,
      });
      await load();
      setActive(undefined);
      setError("Пропозицію збережено. Її можна застосувати або відхилити.");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  const decideFix = async (fix: AIFixProposal, action: "apply" | "reject") => {
    setBusy(true);
    try {
      await api.post(`/ai/fixes/${fix.id}/${action}/`, {});
      await load();
      setActive(undefined);
      setError(
        action === "apply"
          ? "Виправлення застосовано. Запустіть review повторно для нової версії тесткейсу."
          : "Пропозицію відхилено — тесткейс не змінено.",
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>{preset ? "AI QA-помічник проєкту" : "AI QA-помічник"}</h1>
          <p>
            {preset
              ? "Усі створення та історія на цій сторінці обмежені вибраним проєктом."
              : "Створює чернетки тесткейсів за описом функції та знаходить перевірювані суперечності у вимогах і тесткейсах."}{" "}
            Рішення про збереження або виправлення завжди приймає тестувальник.
          </p>
        </div>
      </div>
      {error && <Notice text={error} />}
      <section className="panel ai-workspace">
        <div className="tabbar">
          {tabs
            .filter(([key]) => canManage || key !== "generate")
            .map(([key, label]) => (
              <button
                type="button"
                key={key}
                className={tab === key ? "active" : ""}
                onClick={() => setTab(key)}
              >
                {label}
              </button>
            ))}
        </div>
        {config && (
          <p className="muted">
            Модель: <strong>{config.model}</strong>. Якщо модель недоступна,
            генератор чесно формує лише структуровану чернетку з наданого опису,
            без вигаданих фактів.
          </p>
        )}
        {tab === "generate" && (
          <form className="ai-form" onSubmit={generate}>
            <h2>Створити тесткейси за описом</h2>
            <p>
              Оберіть проєкт: його AI context і обрана вимога будуть частиною
              обмеженого контексту чернетки.
            </p>
            <label>
              Проєкт
              <select
                value={project}
                onChange={(e) => {
                  setProject(e.target.value);
                  setSuite("");
                }}
                required
                disabled={Boolean(preset)}
              >
                <option value="">Оберіть проєкт</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Пов’язана вимога
              <select name="requirement" disabled={!project}>
                <option value="">Без зв’язку</option>
                {requirements
                  .filter((r) => !project || r.project === Number(project))
                  .map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.key} · {r.title}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Опис функції або вимоги
              <textarea
                name="description"
                required
                minLength={10}
                rows={7}
                placeholder="Наприклад: авторизований користувач оформлює замовлення; промокод SALE10 дає 10%; оплата з невалідною карткою повинна бути відхилена."
              />
            </label>
            <div className="form-grid">
              <label>
                Тип перевірок
                <select name="test_type">
                  <option value="MIXED">Змішаний</option>
                  <option value="POSITIVE">Позитивний</option>
                  <option value="NEGATIVE">Негативний</option>
                  <option value="BOUNDARY">Граничний</option>
                </select>
              </label>
              <label>
                Пріоритет
                <select name="priority" defaultValue="MEDIUM">
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
              <label>
                Деталізація
                <select name="detail">
                  <option value="STANDARD">Стандартна</option>
                  <option value="COMPACT">Коротка</option>
                  <option value="DETAILED">Детальна</option>
                </select>
              </label>
              <label>
                Кількість
                <select name="count" defaultValue="3">
                  <option value="1">1</option>
                  <option value="3">3</option>
                  <option value="5">5</option>
                </select>
              </label>
            </div>
            <button type="submit" className="primary" disabled={busy || !project}>
              {busy ? "Генерування…" : "Згенерувати чернетки"}
            </button>
          </form>
        )}
        {tab === "review" && (
          <section className="ai-form">
            <h2>Перевірити збережений тесткейс</h2>
            <p>
              Помічник аналізує назву, передумови, кроки та очікуваний
              результат. Він вказує лише на проблеми, для яких може показати
              фрагмент тексту: суперечності, відсутні обов’язкові дані,
              арифметичні помилки або некоректний успіх для невалідних даних.
            </p>
            <label>
              Тесткейс
              <select
                onChange={(e) =>
                  e.target.value &&
                  void request("/ai/analyze-test-case/", {
                    test_case_id: Number(e.target.value),
                  })
                }
                defaultValue=""
              >
                <option value="">Оберіть тесткейс</option>
                {cases
                  .filter((c) => !project || c.project === Number(project))
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
              </select>
            </label>
          </section>
        )}
        {tab === "scenario" && (
          <form
            className="ai-form"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void request("/ai/analyze-text/", { scenario: f.get("scenario") });
            }}
          >
            <h2>Перевірити вимогу до створення тесту</h2>
            <p>
              Вставте вимогу або сценарій. ШІ не створить дані в системі: він
              спочатку виділить неоднозначності, суперечливі правила, арифметику
              та ризики, які варто уточнити.
            </p>
            <label>
              Вимога або сценарій
              <textarea
                name="scenario"
                required
                minLength={10}
                rows={12}
                placeholder="Опишіть поведінку системи, передумови, правила, кроки та очікувані результати."
              />
            </label>
            <button type="submit" className="primary" disabled={busy}>
              {busy ? "Аналізування…" : "Перевірити вимогу"}
            </button>
          </form>
        )}
        {tab !== "history" && active && (
          <section className="ai-current-result">
            <h2>Результат поточної операції</h2>
            <CopilotCard
              item={active}
              project={project}
              setProject={setProject}
              suite={suite}
              setSuite={setSuite}
              projects={projects}
              suites={suites}
              busy={busy}
              onCreate={createCase}
              onProposeFix={proposeFix}
              onDecideFix={decideFix}
            />
          </section>
        )}
        {tab === "history" && (
          <section>
            <h2>Історія ШІ</h2>
            {!history.length && active ? (
              <CopilotCard
                item={active}
                project={project}
                setProject={setProject}
                suite={suite}
                setSuite={setSuite}
                projects={projects}
                suites={suites}
                busy={busy}
                onCreate={createCase}
                onProposeFix={proposeFix}
                onDecideFix={decideFix}
              />
            ) : !history.length ? (
              <Empty>Операцій ще немає.</Empty>
            ) : (
              history.map((item) => (
                <CopilotCard
                  key={item.id}
                  item={item}
                  project={project}
                  setProject={setProject}
                  suite={suite}
                  setSuite={setSuite}
                  projects={projects}
                  suites={suites}
                  busy={busy}
                  onCreate={createCase}
                  onProposeFix={proposeFix}
                  onDecideFix={decideFix}
                />
              ))
            )}
          </section>
        )}
      </section>
    </>
  );
}

function CopilotCard({
  item,
  project,
  setProject,
  suite,
  setSuite,
  projects,
  suites,
  busy,
  onCreate,
  onProposeFix,
  onDecideFix,
}: {
  item: AIAnalysis;
  project: string;
  setProject: (v: string) => void;
  suite: string;
  setSuite: (v: string) => void;
  projects: Project[];
  suites: Suite[];
  busy: boolean;
  onCreate: (i: AIAnalysis, n: number) => void;
  onProposeFix: (i: AIAnalysis, f: any, after: string) => void;
  onDecideFix: (f: AIFixProposal, a: "apply" | "reject") => void;
}) {
  const r: any = item.result;
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const proposal = (finding: any) =>
    item.fixes?.find((f) => f.finding_id === finding.id);
  return (
    <article className="ai-copilot-card">
      <header>
        <strong>{item.analysis_type}</strong>
        <small>{new Date(item.created_at).toLocaleString("uk-UA")}</small>
      </header>
      {r.quality_score !== undefined && (
        <div className="quality-score">
          <strong>{r.quality_score}/100</strong>
          <span>
            <b>
              {r.semantic_status === "no_cited_findings"
                ? "Структурна оцінка: LLM не дала підтверджених цитат. "
                : ""}
            </b>
            {r.quality_formula}
          </span>
        </div>
      )}
      <AIResult analysis={item} />
      {r.context?.limitations?.map((x: string) => <Notice key={x} text={x} />)}
      {r.failure_explanation && (
        <div className="ai-fix">
          <strong>Пояснення невдалого API-тесту</strong>
          <span>
            Очікувалося HTTP {r.failure_explanation.expected_status}, фактично
            HTTP {r.failure_explanation.actual_status}.
          </span>
          {r.failure_explanation.failed_assertions?.map((x: any, i: number) => (
            <span key={i}>
              {x.name}: очікувалося {String(x.expected)}, отримано{" "}
              {String(x.actual)}
            </span>
          ))}
        </div>
      )}
      {r.suggested_assertions?.length > 0 && (
        <div className="ai-fix">
          <strong>Пропоновані assertions</strong>
          <pre>{JSON.stringify(r.suggested_assertions, null, 2)}</pre>
        </div>
      )}
      {r.findings
        ?.filter((f: any) => f.fix?.after)
        .map((f: any) => {
          const fix = proposal(f);
          const value = drafts[f.id] ?? f.fix.after;
          return (
            <div className="ai-fix" key={f.id}>
              <strong>{f.title}</strong>
              <div>
                <span>Before: {f.fix.before}</span>
                <textarea
                  aria-label={`Виправлення ${f.title}`}
                  value={value}
                  onChange={(e) =>
                    setDrafts({ ...drafts, [f.id]: e.target.value })
                  }
                />
              </div>
              {!fix ? (
                <button
                  type="button"
                  disabled={busy || !value.trim()}
                  onClick={() => onProposeFix(item, f, value)}
                >
                  Запропонувати виправлення
                </button>
              ) : fix.status === "PROPOSED" ? (
                <div className="form-actions">
                  <span className="badge">Очікує рішення</span>
                  <button
                    type="button"
                    className="primary"
                    disabled={busy}
                    onClick={() => onDecideFix(fix, "apply")}
                  >
                    Застосувати
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => onDecideFix(fix, "reject")}
                  >
                    Відхилити
                  </button>
                </div>
              ) : (
                <span className="badge">
                  {fix.status === "APPLIED" ? "Застосовано" : "Відхилено"}
                </span>
              )}
            </div>
          );
        })}
      {r.suggestions?.map((s: any, index: number) => (
        <div className="ai-proposal" key={index}>
          <h3>{s.title}</h3>
          <p>{s.description}</p>
          <ol>
            {s.steps?.map((step: any, n: number) => (
              <li key={n}>
                {step.action}
                <small>Очікується: {step.expected_result}</small>
              </li>
            ))}
          </ol>
          {!r.created_cases?.[String(index)] ? (
            <div className="form-actions">
              <select
                value={project}
                onChange={(e) => {
                  setProject(e.target.value);
                  setSuite("");
                }}
              >
                <option value="">Проєкт для нового тесту</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <select
                value={suite}
                onChange={(e) => setSuite(e.target.value)}
                disabled={!project}
              >
                <option value="">Без Test Suite</option>
                {suites
                  .filter((s) => s.project === Number(project))
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
              </select>
              <button
                type="button"
                className="primary"
                disabled={!project || busy}
                onClick={() => onCreate(item, index)}
              >
                Створити Test Case
              </button>
            </div>
          ) : (
            <Link to={`/test-cases/${r.created_cases[String(index)]}`}>
              Відкрити створений Test Case
            </Link>
          )}
        </div>
      ))}
    </article>
  );
}
