import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";
import {
  Check,
  Eye,
  EyeOff,
  LoaderCircle,
  Moon,
  Sun,
  ShieldCheck,
} from "lucide-react";
export function Brand() {
  return (
    <div className="brand">
      <span>
        <ShieldCheck size={24} />
      </span>
      <strong>
        WebTestCase<span>УПРАВЛІННЯ ТЕСТ-КЕЙСАМИ</span>
      </strong>
    </div>
  );
}
export function Spinner() {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" /> Завантаження…
    </div>
  );
}
export function Button({
  children,
  busy = false,
  type = "button",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean }) {
  return (
    <button
      type={type}
      {...props}
      disabled={busy || props.disabled}
      className={`btn ${props.className ?? ""}`}
    >
      {busy && <LoaderCircle size={16} className="spin" />}
      {children}
    </button>
  );
}
export function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {error && <small className="error">{error}</small>}
    </label>
  );
}
export function PasswordInput({
  registration,
  id,
  autoComplete = "current-password",
}: {
  registration: UseFormRegisterReturn;
  id?: string;
  autoComplete?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="password-input">
      <input
        id={id}
        {...registration}
        type={show ? "text" : "password"}
        autoComplete={autoComplete}
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        aria-label={show ? "Приховати пароль" : "Показати пароль"}
      >
        {show ? <EyeOff size={18} /> : <Eye size={18} />}
      </button>
    </div>
  );
}
export const passwordRules = [
  { test: (p: string) => p.length >= 8, label: "8 або більше символів" },
  { test: (p: string) => /\p{Lu}/u.test(p), label: "Велика літера" },
  { test: (p: string) => /\p{Ll}/u.test(p), label: "Мала літера" },
  { test: (p: string) => /\p{Nd}/u.test(p), label: "Цифра" },
  {
    test: (p: string) => /[^\p{L}\p{N}\s]/u.test(p),
    label: "Спеціальний символ",
  },
];
export function PasswordStrength({ password }: { password: string }) {
  const score = passwordRules.filter((r) => r.test(password)).length;
  return (
    <div className="password-strength">
      <div className="strength-bar">
        {passwordRules.map((_, i) => (
          <span key={i} className={i < score ? "filled" : ""} />
        ))}
      </div>
      <div className="rule-grid">
        {passwordRules.map((rule) => (
          <span key={rule.label} className={rule.test(password) ? "met" : ""}>
            <Check size={12} />
            {rule.label}
          </span>
        ))}
      </div>
    </div>
  );
}
export function ThemeToggle() {
  const [dark, setDark] = useState(
    () => localStorage.getItem("theme") === "dark",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  return (
    <button
      type="button"
      className="icon-button"
      aria-label={dark ? "Світла тема" : "Темна тема"}
      onClick={() => setDark(!dark)}
    >
      {dark ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}
export function Badge({
  children,
  tone = "good",
}: {
  children: ReactNode;
  tone?: "good" | "warn" | "bad" | "neutral";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);
  return (
    <div className="modal-backdrop">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="card-title">
          <h2>{title}</h2>
          <button
            type="button"
            className="icon-button"
            aria-label="Закрити"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
export function Pagination({
  page,
  count,
  onPage,
}: {
  page: number;
  count: number;
  onPage: (p: number) => void;
}) {
  const total = Math.max(1, Math.ceil(count / 12));
  return (
    <div className="pagination">
      <span>
        {count} записів · Сторінка {page} з {total}
      </span>
      <div>
        <Button
          className="secondary"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          Назад
        </Button>
        <Button
          className="secondary"
          disabled={page >= total}
          onClick={() => onPage(page + 1)}
        >
          Далі
        </Button>
      </div>
    </div>
  );
}
export function date(value: string | null) {
  return value
    ? new Intl.DateTimeFormat("uk-UA", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "—";
}

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: Record<string, unknown>,
      ) => string;
      remove: (id: string) => void;
      reset: (id: string) => void;
    };
  }
}
export function Captcha({
  siteKey,
  onToken,
  resetKey,
}: {
  siteKey: string;
  onToken: (token: string) => void;
  resetKey: number;
}) {
  const node = useRef<HTMLDivElement>(null),
    widget = useRef<string | null>(null);
  useEffect(() => {
    let live = true;
    const mount = () => {
      if (live && node.current && window.turnstile && widget.current === null)
        widget.current = window.turnstile.render(node.current, {
          sitekey: siteKey,
          action: "register",
          language: "uk",
          callback: onToken,
          "expired-callback": () => onToken(""),
          "error-callback": () => onToken(""),
        });
    };
    let script = document.querySelector<HTMLScriptElement>(
      "script[data-turnstile]",
    );
    if (!script) {
      script = document.createElement("script");
      script.dataset.turnstile = "true";
      script.src =
        "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener("load", mount);
    mount();
    return () => {
      live = false;
      script?.removeEventListener("load", mount);
      if (widget.current !== null) {
        window.turnstile?.remove(widget.current);
        widget.current = null;
      }
    };
  }, [siteKey, onToken]);
  useEffect(() => {
    if (widget.current !== null && resetKey > 0)
      window.turnstile?.reset(widget.current);
  }, [resetKey]);
  return <div className="captcha-container" ref={node} />;
}
