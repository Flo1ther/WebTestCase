import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api, { errorText } from "../services/api";
import { Badge, Empty, Loader, Notice } from "../components/ui";
type Project = { id: number; name: string };
type APITest = {
  id: number;
  name: string;
  method: string;
  url: string;
  expected_status: number;
  project: number;
};
type Result = {
  status: string;
  actual_status: number;
  duration_ms: number;
  response_preview: string;
  assertion_results: {
    name: string;
    passed: boolean;
    expected: any;
    actual: any;
  }[];
};
export function APITesting() {
  const [params] = useSearchParams();
  const preset = params.get("project") || "";
  const [items, setItems] = useState<APITest[]>(),
    [projects, setProjects] = useState<Project[]>([]),
    [requirements, setRequirements] = useState<any[]>([]),
    [project, setProject] = useState(preset),
    [result, setResult] = useState<Result>(),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const load = () =>
    api
      .get("/api-tests/", { params: preset ? { project: preset } : {} })
      .then((r) => setItems(r.data.results))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    setProject(preset);
    load();
    api
      .get("/projects/")
      .then((r) => setProjects(r.data.results))
      .catch((e) => setError(errorText(e)));
  }, [preset]);
  useEffect(() => {
    if (project)
      api
        .get("/requirements/", { params: { project, page_size: 100 } })
        .then((r) => setRequirements(r.data.results))
        .catch((e) => setError(errorText(e)));
    else setRequirements([]);
  }, [project]);
  const create = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    setError("");
    const f = new FormData(form);
    try {
      const parseObject = (value: FormDataEntryValue | null, label: string) => {
        try {
          const parsed = JSON.parse(String(value || "{}"));
          if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
            throw new Error();
          return parsed;
        } catch {
          throw new Error(`${label} має бути коректним JSON-об’єктом.`);
        }
      };
      const assertions = String(f.get("assertions") || "")
        .split("\n")
        .filter(Boolean)
        .map((line) => {
          const [path, ...raw] = line.split("=");
          if (!path?.trim() || !raw.length)
            throw new Error("Кожна assertion має формат path = значення.");
          const joined = raw.join("=").trim();
          let equals: any = joined;
          try {
            equals = JSON.parse(joined);
          } catch {}
          return { path: path.trim(), equals };
        });
      await api.post("/api-tests/", {
        project: Number(project),
        requirement: f.get("requirement") ? Number(f.get("requirement")) : null,
        name: f.get("name"),
        method: f.get("method"),
        url: f.get("url"),
        expected_status: Number(f.get("expected_status")),
        headers: parseObject(f.get("headers"), "Headers"),
        request_body: parseObject(f.get("request_body"), "Request body"),
        json_assertions: assertions,
      });
      form.reset();
      if (!preset) setProject("");
      await load();
    } catch (x) {
      setError(x instanceof Error ? x.message : errorText(x));
    } finally {
      setBusy(false);
    }
  };
  const run = async (t: APITest) => {
    setBusy(true);
    setError("");
    try {
      const r = await api.post(`/api-tests/${t.id}/run/`);
      setResult(r.data);
    } catch (x) {
      setError(errorText(x));
    } finally {
      setBusy(false);
    }
  };
  if (!items) return <Loader />;
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>{preset ? "API-тести проєкту" : "API Testing"}</h1>
          <p>
            Реальні локальні HTTP-перевірки та assertions. PASS/FAIL
            визначається відповіддю API.
          </p>
        </div>
      </div>
      {error && <Notice text={error} />}
      <form className="form-panel" onSubmit={create}>
        <h2>Створити API-тест</h2>
        <p>Для безпеки доступні лише localhost та 127.0.0.1.</p>
        <label>
          Проєкт
          <select
            value={project}
            required
            onChange={(e) => setProject(e.target.value)}
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
          Вимога
          <select name="requirement" disabled={!project}>
            <option value="">Без прямого зв’язку</option>
            {requirements.map((r) => (
              <option key={r.id} value={r.id}>
                {r.key} · {r.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Назва
          <input name="name" required minLength={4} />
        </label>
        <label>
          Метод
          <select name="method" defaultValue="GET">
            <option>GET</option>
            <option>POST</option>
            <option>PUT</option>
            <option>PATCH</option>
            <option>DELETE</option>
          </select>
        </label>
        <label>
          Локальний URL
          <input
            name="url"
            required
            defaultValue="http://127.0.0.1:8000/api/demo-store/health/"
          />
        </label>
        <label>
          Очікуваний HTTP-статус
          <input
            name="expected_status"
            type="number"
            min="100"
            max="599"
            defaultValue="200"
            required
          />
        </label>
        <label>
          Headers (JSON)
          <textarea name="headers" rows={2} defaultValue="{}" />
        </label>
        <label>
          Request body (JSON)
          <textarea
            name="request_body"
            rows={3}
            defaultValue="{}"
            placeholder={'{"items": [], "payment_token": "invalid"}'}
          />
        </label>
        <label>
          JSON assertions, по одному на рядок
          <textarea
            name="assertions"
            rows={3}
            placeholder={'status = "ok"\norder.status = "paid"'}
          />
          <small>
            Формат: шлях до поля = очікуване значення. Значення `true`, числа та
            JSON розпізнаються.
          </small>
        </label>
        <button type="submit" className="primary" disabled={busy || !project}>
          {busy ? "Збереження…" : "Зберегти тест"}
        </button>
      </form>
      <section className="panel">
        <h2>Збережені API-тести</h2>
        {items.length ? (
          <div className="compact-list">
            {items.map((t) => (
              <div key={t.id}>
                <span>
                  <strong>
                    {t.method} · {t.name}
                  </strong>
                  <small>{t.url}</small>
                  <small>Очікувано: HTTP {t.expected_status}</small>
                </span>
                <button
                  type="button"
                  className="primary"
                  disabled={busy}
                  onClick={() => run(t)}
                >
                  Запустити
                </button>
              </div>
            ))}
          </div>
        ) : (
          <Empty>Створіть перший API-тест для проєкту.</Empty>
        )}
      </section>
      {result && (
        <section className="panel">
          <h2>Останній результат</h2>
          <Badge value={result.status} />
          <p>
            HTTP {result.actual_status} · {result.duration_ms} мс
          </p>
          {result.assertion_results.map((a, i) => (
            <p key={i}>
              {a.passed ? "✓" : "✕"} {a.name}: очікувалося {String(a.expected)},
              отримано {String(a.actual)}
            </p>
          ))}
          <pre>{result.response_preview}</pre>
        </section>
      )}
    </>
  );
}
