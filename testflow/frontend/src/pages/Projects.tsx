import { label } from "../labels";
import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
import api, { errorText } from "../services/api";
import type { Project } from "../types";
import { Empty, Loader, Modal, Notice } from "../components/ui";
import { useAuth } from "../context/AuthContext";
export function Projects() {
  const [list, setList] = useState<Project[]>([]),
    [q, setQ] = useState(""),
    [error, setError] = useState(""),
    [modal, setModal] = useState(false);
  const { user } = useAuth();
  const canManage = user?.role !== "TESTER";
  const load = () =>
    api
      .get("/projects/", { params: { search: q } })
      .then((r) => setList(r.data.results))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
  }, [q]);
  const create = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      await api.post(
        "/projects/",
        Object.fromEntries(new FormData(e.currentTarget)),
      );
      setModal(false);
      load();
    } catch (e) {
      setError(errorText(e));
    }
  };
  const remove = async (id: number) => {
    if (confirm("Видалити цей проєкт і всі пов’язані QA-дані?")) {
      try {
        await api.delete(`/projects/${id}/`);
        load();
      } catch (e) {
        setError(errorText(e));
      }
    }
  };
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Проєкти</h1>
          <p>
            Кожен проєкт - окремий робочий простір вимог, тестів, дефектів і
            звітів.
          </p>
        </div>
        {canManage && (
          <button type="button" className="primary" onClick={() => setModal(true)}>
            <Plus size={17} />
            Новий проєкт
          </button>
        )}
      </div>
      <div className="toolbar">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Пошук проєктів…"
        />
      </div>
      {error && <Notice text={error} />}
      <div className="project-grid">
        {!list.length ? (
          <Empty>За цим запитом проєктів не знайдено.</Empty>
        ) : (
          list.map((p) => (
            <article className="project-card" key={p.id}>
              <div>
                <h2>
                  <Link to={`/projects/${p.id}`}>{p.name}</Link>
                </h2>
                <p>{p.description || "Опис не вказано."}</p>
                <small>
                  {p.requirements_count || 0} вимог · {p.test_case_count || 0}{" "}
                  тесткейсів
                </small>
              </div>
              <footer>
                <span>{p.status || "ACTIVE"}</span>
                <strong>{Math.round(p.progress || 0)}% виконано</strong>
                {user?.role === "ADMIN" && (
                  <button
                    type="button"
                    className="danger icon-button"
                    onClick={() => remove(p.id)}
                    title="Видалити проєкт"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </footer>
            </article>
          ))
        )}
      </div>
      {modal && (
        <Modal title="Новий проєкт" onClose={() => setModal(false)}>
          <form onSubmit={create}>
            <label>
              Назва
              <input name="name" required minLength={3} />
            </label>
            <label>
              Опис продукту
              <textarea name="description" rows={3} />
            </label>
            <label>
              Контекст для AI
              <textarea
                name="ai_context"
                rows={5}
                placeholder="Користувачі, терміни, бізнес-правила, обмеження, критерії приймання…"
              />
              <small>Передається AI QA-помічнику лише для цього проєкту.</small>
            </label>
            <label>
              Статус
              <select name="status" defaultValue="ACTIVE">
                <option value="ACTIVE">Активний</option>
                <option value="ON_HOLD">Призупинено</option>
                <option value="ARCHIVED">Архів</option>
              </select>
            </label>
            <div className="form-actions">
              <button type="button" onClick={() => setModal(false)}>
                Скасувати
              </button>
              <button type="submit" className="primary">Створити проєкт</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
export function ProjectDetail() {
  const id = location.pathname.split("/").pop();
  const [p, setP] = useState<Project>(),
    [cases, setCases] = useState<any[]>([]),
    [err, setErr] = useState("");
  useEffect(() => {
    Promise.all([
      api.get(`/projects/${id}/`),
      api.get("/test-cases/", { params: { project: id } }),
    ])
      .then(([a, b]) => {
        setP(a.data);
        setCases(b.data.results);
      })
      .catch((e) => setErr(errorText(e)));
  }, [id]);
  if (err) return <Notice text={err} />;
  if (!p) return <Loader />;
  return (
    <>
      <div className="page-heading">
        <div>
          <Link className="back" to="/projects">
            Проєкти
          </Link>
          <h1>{p.name}</h1>
          <p>{p.description}</p>
        </div>
      </div>
      <section className="stats two">
        <div className="stat">
          <span>Тесткейси</span>
          <strong>{p.test_case_count || cases.length}</strong>
        </div>
        <div className="stat">
          <span>Прогрес</span>
          <strong>{Math.round(p.progress || 0)}%</strong>
        </div>
      </section>
      <section className="panel">
        <h2>Тесткейси проєкту</h2>
        <div className="compact-list">
          {cases.map((c) => (
            <Link className="list-link" to={`/test-cases/${c.id}`} key={c.id}>
              {c.title}
              <span>{label(c.status)}</span>
            </Link>
          ))}
          {!cases.length && <Empty>У проєкті немає тесткейсів.</Empty>}
        </div>
      </section>
    </>
  );
}
