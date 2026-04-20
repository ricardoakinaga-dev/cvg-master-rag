"use client";

import type { Route } from "next";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Building2, LogIn, ShieldCheck, UsersRound } from "lucide-react";
import { useEnterpriseSession } from "@/components/layout/enterprise-session-provider";
import { Badge, Button, Card, Input, Select, useToast } from "@/components/ui";

const DEFAULT_EMAILS: Record<string, string> = {
  admin: "admin@demo.local",
  operator: "operator@demo.local",
  viewer: "viewer@demo.local",
};

const DEFAULT_PASSWORD = "demo1234";

function LoginContent() {
  const router = useRouter();
  const { pushToast } = useToast();
  const { session, signIn } = useEnterpriseSession();
  const tenants = session?.available_tenants ?? [];
  const [role, setRole] = useState<"admin" | "operator" | "viewer">(session?.user.role ?? "viewer");
  const [email, setEmail] = useState(session?.user.email ?? DEFAULT_EMAILS.viewer);
  const [password, setPassword] = useState(DEFAULT_PASSWORD);
  const [tenantId, setTenantId] = useState(session?.active_tenant.tenant_id ?? "default");
  const [loading, setLoading] = useState(false);
  const [nextPath, setNextPath] = useState("/");
  const [formTouched, setFormTouched] = useState(false);

  useEffect(() => {
    if (!session || formTouched) return;
    setRole(session.user.role);
    setEmail(session.user.email || DEFAULT_EMAILS[session.user.role]);
    setPassword(DEFAULT_PASSWORD);
    setTenantId(session.active_tenant.tenant_id);
  }, [formTouched, session]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const next = new URLSearchParams(window.location.search).get("next");
    setNextPath(next && next.startsWith("/") ? next : "/");
  }, []);

  const tenantLabel = tenants.find((tenant) => tenant.tenant_id === tenantId)?.name ?? "Tenant ativo";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    try {
      await signIn({
        email: email.trim() || DEFAULT_EMAILS[role],
        password: password.trim() || DEFAULT_PASSWORD,
        tenant_id: tenantId,
      });
      pushToast({
        title: "Sessão carregada",
        description: "Você entrou no console enterprise com contexto de tenant.",
        intent: "success",
      });
      router.push(nextPath as Route);
    } catch (error) {
      pushToast({
        title: "Falha no login",
        description: error instanceof Error ? error.message : "Não foi possível abrir a sessão",
        intent: "error",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-shell">
        <Card className="auth-hero">
          <div className="auth-brand">
            <div className="brand-mark">RAG</div>
            <div className="card-title">
              <strong>Enterprise Console</strong>
              <span>Fase 3 · acesso, tenants e perfis</span>
            </div>
          </div>

          <div className="page-hero">
            <span className="eyebrow">Acesso</span>
            <h1>Entre com identidade, tenant e perfil ativos.</h1>
            <p>
              A fundação enterprise agora expõe sessão server-side, troca de tenant e navegação por role. Use as contas
              demo para validar o fluxo completo com o backend real.
            </p>
          </div>

          <div className="auth-metrics">
            <Badge variant="info">
              <ShieldCheck size={14} />
              sessão local
            </Badge>
            <Badge variant="neutral">
              <UsersRound size={14} />
              roles admin/operator/viewer
            </Badge>
            <Badge variant="neutral">
              <Building2 size={14} />
              tenant ativo {tenantLabel}
            </Badge>
            {session?.session_state === "expired" ? <Badge variant="warning">sessão expirada</Badge> : null}
          </div>

          <div className="auth-links">
            <Link href="/recover-access">Recuperar acesso</Link>
            <Link href="/onboarding">Ver onboarding</Link>
          </div>
        </Card>

        <Card className="auth-panel">
          <form className="form-grid" onSubmit={handleSubmit}>
            <div className="card-title">
              <strong>Entrar no console</strong>
              <span>Escolha role, tenant e a identidade de demonstração com credencial válida.</span>
            </div>

            <div className="grid cols-1">
              <label className="ui-label">
                Perfil
                <Select
                  value={role}
                  onChange={(event) => {
                    const nextRole = event.target.value as typeof role;
                    setFormTouched(true);
                    setRole(nextRole);
                    setEmail(DEFAULT_EMAILS[nextRole]);
                  }}
                >
                  <option value="admin">admin</option>
                  <option value="operator">operator</option>
                  <option value="viewer">viewer</option>
                </Select>
              </label>

              <label className="ui-label">
                E-mail
                <Input
                  value={email}
                  onChange={(event) => {
                    setFormTouched(true);
                    setEmail(event.target.value);
                  }}
                  placeholder={DEFAULT_EMAILS[role]}
                />
              </label>

              <label className="ui-label">
                Senha
                <Input
                  type="password"
                  value={password}
                  onChange={(event) => {
                    setFormTouched(true);
                    setPassword(event.target.value);
                  }}
                  placeholder={DEFAULT_PASSWORD}
                />
              </label>

              <label className="ui-label">
                Tenant
                <Select
                  value={tenantId}
                  onChange={(event) => {
                    setFormTouched(true);
                    setTenantId(event.target.value);
                  }}
                  disabled={!tenants.length}
                >
                  {tenants.map((tenant) => (
                    <option key={tenant.tenant_id} value={tenant.tenant_id}>
                      {tenant.name} · {tenant.workspace_id}
                    </option>
                  ))}
                </Select>
              </label>
            </div>

            <div className="auth-actions">
              <Button type="submit" disabled={loading}>
                <LogIn size={16} />
                {loading ? "Entrando..." : "Entrar"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => router.push("/onboarding")}>
                Próximo passo
                <ArrowRight size={16} />
              </Button>
            </div>

            <p className="helper-text">Credencial demo padrão: `demo1234`.</p>

            <div className="auth-quick-actions">
              {(["admin", "operator", "viewer"] as const).map((quickRole) => (
                <Button
                  key={quickRole}
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setFormTouched(true);
                    setRole(quickRole);
                    setEmail(DEFAULT_EMAILS[quickRole]);
                    setPassword(DEFAULT_PASSWORD);
                  }}
                >
                  Entrar como {quickRole}
                </Button>
              ))}
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="auth-page">
          <div className="auth-shell auth-shell-single">
            <Card className="auth-panel">
              <div className="state-box">
                <h3>Carregando login</h3>
                <p>Preparando sessão enterprise.</p>
              </div>
            </Card>
          </div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
