import { FormEvent, useEffect, useState } from "react";
import api, { errorText } from "../services/api";
import { Badge, Empty, Loader, Notice } from "../components/ui";
type Run = {
  id: number;
  name: string;
  project_name: string;
  status: string;
  description: string;
  progress: { total: number; completed: number; percent: number };
};
type Project = { id: number; name: string };
type Case = { id: number; title: string; project: number };
type Suite = {
  id: number;
  name: string;
  project: number;
  test_case_ids: number[];
};
export function TestRuns() {
  const [items, setItems] = useState<Run[]>(),
    [projects, setProjects] = useState<Project[]>([]),
    [cases, setCases] = useState<Case[]>([]),
    [suites, setSuites] = useState<Suite[]>([]),
    [project, setProject] = useState(""),
    [selected, setSelected] = useState<number[]>([]),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  const load = () =>
    api
      .get("/test-runs/")
      .then((r) => setItems(r.data.results))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
    api
      .get("/projects/")
      .then((r) => setProjects(r.data.results))
      .catch((e) => setError(errorText(e)));
    api
      .get("/test-cases/?page_size=100")
      .then((r) => setCases(r.data.results))
      .catch((e) => setError(errorText(e)));
    api
      .get("/test-suites/")
      .then((r) => setSuites(r.data.results))
      .catch((e) => setError(errorText(e)));
  }, []);
  const create = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSaving(true);
    const f = new FormData(e.currentTarget);
    try {
      await api.post("/test-runs/", {
        project: Number(project),
        name: f.get("name"),
        description: f.get("description"),
        status: "DRAFT",
        test_case_ids: selected,
      });
      e.currentTarget.reset();
      setSelected([]);
      await load();
    } catch (x) {
      setError(errorText(x));
    } finally {
      setSaving(false);
    }
  };
  const transition = async (id: number, command: "start" | "complete") => {
    setSaving(true);
    setError("");
    try {
      await api.post(`/test-runs/${id}/${command}/`);
      await load();
    } catch (x) {
      setError(errorText(x));
    } finally {
      setSaving(false);
    }
  };
  if (!items) return <Loader />;
  const filtered = cases.filter((x) => String(x.project) === project);
  const projectSuites = suites.filter((s) => String(s.project) === project);
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Тестові прогони</h1>
          <p>
            Чернетка → активний прогін → завершений історичний запис. Виконання
            додаються лише до активного прогону.
          </p>
        </div>
      </div>
      {error && <Notice text={error} />}
      <form className="form-panel" onSubmit={create}>
        <h2>Створити Test Run</h2>
        <label>
          Проєкт
          <select
            required
            value={project}
            onChange={(e) => {
              setProject(e.target.value);
              setSelected([]);
            }}
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
          Назва прогону
          <input
            name="name"
            required
            minLength={4}
            placeholder="Release 1.0 smoke"
          />
        </label>
        <label>
          Опис / версія / середовище
          <textarea name="description" rows={3} placeholder="v1.0 · staging" />
        </label>
        <label>
          Заповнити з Test Suite
          <select
            defaultValue=""
            disabled={!project}
            onChange={(e) => {
              const suite = projectSuites.find(
                (item) => item.id === Number(e.target.value),
              );
              if (suite) setSelected(suite.test_case_ids);
            }}
          >
            <option value="">Вибрати вручну</option>
            {projectSuites.map((suite) => (
              <option key={suite.id} value={suite.id}>
                {suite.name}
              </option>
            ))}
          </select>
          <small>
            Набір лише заповнює список нижче — склад прогону можна уточнити.
          </small>
        </label>
        <label>
          Тесткейси
          <select
            multiple
            value={selected.map(String)}
            onChange={(e) =>
              setSelected(
                Array.from(e.currentTarget.selectedOptions).map((x) =>
                  Number(x.value),
                ),
              )
            }
          >
            {filtered.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="primary"
          disabled={saving || !project || !selected.length}
        >
          {saving ? "Збереження…" : "Створити чернетку"}
        </button>
      </form>
      <section className="panel">
        {items.length ? (
          <div className="compact-list">
            {items.map((run) => (
              <div key={run.id}>
                <span>
                  <strong>{run.name}</strong>
                  <small>
                    {run.project_name} · {run.description || "Без опису"}
                  </small>
                  <small>
                    {run.progress.completed} з {run.progress.total} виконано
                  </small>
                  <div className="progress">
                    <i style={{ width: `${run.progress.percent}%` }} />
                  </div>
                  {run.status === "DRAFT" && (
                    <button
                      type="button"
                      className="secondary"
                      disabled={saving}
                      onClick={() => transition(run.id, "start")}
                    >
                      Запустити прогін
                    </button>
                  )}
                  {run.status === "ACTIVE" && (
                    <button
                      type="button"
                      className="secondary"
                      disabled={saving}
                      onClick={() => transition(run.id, "complete")}
                    >
                      Завершити прогін
                    </button>
                  )}
                </span>
                <Badge value={run.status} />
              </div>
            ))}
          </div>
        ) : (
          <Empty>Ще немає тестових прогонів.</Empty>
        )}
      </section>
    </>
  );
}
