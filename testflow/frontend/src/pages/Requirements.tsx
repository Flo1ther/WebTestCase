import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import api, { errorText } from "../services/api";
import { Empty, Loader, Notice } from "../components/ui";
import { useAuth } from "../context/AuthContext";

type Requirement = {
  id: number;
  key: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  project: number;
  project_name?: string;
  covered: boolean;
};
type Project = { id: number; name: string };
type TestCase = { id: number; title: string; project: number };
export function Requirements() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const preset = params.get("project") || "";
  const [items, setItems] = useState<Requirement[]>(),
    [projects, setProjects] = useState<Project[]>([]),
    [cases, setCases] = useState<TestCase[]>([]),
    [project, setProject] = useState(preset),
    [selected, setSelected] = useState<number[]>([]),
    [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const canManage = ["ADMIN", "MANAGER"].includes(user?.role || "");
  const load = () =>
    api
      .get("/requirements/", { params: preset ? { project: preset } : {} })
      .then((r) => setItems(r.data.results))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    setProject(preset);
    load();
    api
      .get("/projects/")
      .then((r) => setProjects(r.data.results))
      .catch((e) => setError(errorText(e)));
    api
      .get("/test-cases/", {
        params: { page_size: 100, project: preset || undefined },
      })
      .then((r) => setCases(r.data.results))
      .catch((e) => setError(errorText(e)));
  }, [preset]);
  const create = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    setSaving(true);
    setError("");
    const f = new FormData(form);
    try {
      await api.post("/requirements/", {
        project: Number(project),
        key: f.get("key"),
        title: f.get("title"),
        description: f.get("description"),
        priority: f.get("priority"),
        status: "DRAFT",
        test_case_ids: selected,
      });
      form.reset();
      if (!preset) setProject("");
      setSelected([]);
      await load();
    } catch (x) {
      setError(errorText(x));
    } finally {
      setSaving(false);
    }
  };
  if (!items) return <Loader />;
  const available = cases.filter((item) => String(item.project) === project);
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>{preset ? "Вимоги проєкту" : "Вимоги"}</h1>
          <p>Трасування Requirement → Test Case → Run → Result → Defect.</p>
        </div>
      </div>
      {error && <Notice text={error} />}{" "}
      {canManage && (
        <form className="form-panel" onSubmit={create}>
          <h2>Додати вимогу</h2>
          <label>
            Проєкт
            <select
              required
              value={project}
              onChange={(e) => {
                setProject(e.target.value);
                setSelected([]);
              }}
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
            Ідентифікатор
            <input name="key" required placeholder="REQ-101" />
          </label>
          <label>
            Назва
            <input name="title" required minLength={5} />
          </label>
          <label>
            Опис
            <textarea name="description" required minLength={10} rows={4} />
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
            Тесткейси для покриття
            <select
              multiple
              value={selected.map(String)}
              onChange={(e) =>
                setSelected(
                  Array.from(e.currentTarget.selectedOptions).map((option) =>
                    Number(option.value),
                  ),
                )
              }
              disabled={!project}
            >
              {available.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
            <small>
              Необов’язково: лише тесткейси обраного проєкту можна пов’язати з
              вимогою.
            </small>
          </label>
          <button type="submit" className="primary" disabled={saving || !project}>
            {saving ? "Збереження…" : "Створити вимогу"}
          </button>
        </form>
      )}
      <section className="panel">
        <h2>Матриця покриття</h2>
        {items.length ? (
          <div className="compact-list">
            {items.map((x) => (
              <div key={x.id}>
                <span>
                  <strong>
                    {x.key} · {x.title}
                  </strong>
                  <small>{x.project_name || `Проєкт #${x.project}`}</small>
                  <small>{x.description}</small>
                </span>
                <b
                  className={
                    x.covered ? "stability stable" : "stability unstable"
                  }
                >
                  {x.covered ? "Покрито тестами" : "Не покрито"}
                </b>
              </div>
            ))}
          </div>
        ) : (
          <Empty>Додайте вимоги, щоб побачити реальне покриття тестами.</Empty>
        )}
      </section>
    </>
  );
}
