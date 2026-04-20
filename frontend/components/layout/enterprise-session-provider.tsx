"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { loadStoredJson, saveStoredJson } from "@/lib/storage";
import type { EnterpriseSession, LoginRequest, RecoveryRequest } from "@/types";

const SESSION_STORAGE_KEY = "frontend.enterprise.session";

const ANONYMOUS_USER: EnterpriseSession["user"] = {
  user_id: "anonymous",
  name: "Visitante",
  email: "",
  role: "viewer",
  permissions: [],
};

const EMPTY_TENANT: EnterpriseSession["active_tenant"] = {
  tenant_id: "default",
  name: "Workspace Principal",
  workspace_id: "default",
  plan: "enterprise",
  status: "active",
  operational_retention_mode: "keep_latest",
  operational_retention_hours: 24,
  document_count: 0,
};

const LOCAL_TENANTS: EnterpriseSession["available_tenants"] = [
  EMPTY_TENANT,
  {
    tenant_id: "acme-lab",
    name: "Acme Lab",
    workspace_id: "acme-lab",
    plan: "business",
    status: "active",
    operational_retention_mode: "keep_latest",
    operational_retention_hours: 24,
    document_count: 0,
  },
  {
    tenant_id: "northwind",
    name: "Northwind Pilot",
    workspace_id: "northwind",
    plan: "starter",
    status: "active",
    operational_retention_mode: "keep_latest",
    operational_retention_hours: 24,
    document_count: 0,
  },
];

function isExpired(expiresAt?: string | null) {
  if (!expiresAt) return false;
  const parsed = Date.parse(expiresAt);
  return Number.isFinite(parsed) && parsed <= Date.now();
}

function normalizeSession(source: EnterpriseSession | null): EnterpriseSession {
  if (!source) {
    return asAnonymousSession(null);
  }

  if (source.session_state === "expired" || isExpired(source.expires_at)) {
    return {
      ...asAnonymousSession(source),
      session_state: "expired",
      message: "Sessão expirada. Faça login novamente para continuar.",
    };
  }

  return source;
}

type EnterpriseSessionContextValue = {
  session: EnterpriseSession | null;
  ready: boolean;
  signIn: (request: LoginRequest) => Promise<EnterpriseSession>;
  signOut: () => Promise<void>;
  switchTenant: (tenantId: string) => Promise<void>;
  requestRecovery: (request: RecoveryRequest) => Promise<string>;
  refresh: () => Promise<void>;
};

const EnterpriseSessionContext = createContext<EnterpriseSessionContextValue | null>(null);

function asAnonymousSession(source: EnterpriseSession | null): EnterpriseSession {
  return {
    authenticated: false,
    session_state: "anonymous",
    expires_at: null,
    session_token: null,
    user: ANONYMOUS_USER,
    active_tenant: source?.active_tenant ?? EMPTY_TENANT,
    available_tenants: source?.available_tenants ?? LOCAL_TENANTS,
    message: "Sessão expirada. Faça login para continuar.",
  };
}

export function EnterpriseSessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<EnterpriseSession | null>(null);
  const [ready, setReady] = useState(false);
  const bootstrapRequestRef = useRef(0);

  useEffect(() => {
    let active = true;
    const stored = loadStoredJson<EnterpriseSession | null>(SESSION_STORAGE_KEY, null);
    if (stored) {
      setSession(normalizeSession(stored));
      setReady(true);
    }

    const requestId = bootstrapRequestRef.current + 1;
    bootstrapRequestRef.current = requestId;

    api.session
      .current()
      .then((response) => {
        if (!active || bootstrapRequestRef.current !== requestId) return;
        setSession(normalizeSession(response));
      })
      .catch(() => {
        if (!active || bootstrapRequestRef.current !== requestId) return;
        setSession(asAnonymousSession(null));
      })
      .finally(() => {
        if (active && bootstrapRequestRef.current === requestId) setReady(true);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!ready || !session) return;
    saveStoredJson(SESSION_STORAGE_KEY, session);
  }, [ready, session]);

  const value = useMemo<EnterpriseSessionContextValue>(() => {
    return {
      session,
      ready,
      signIn: async (request: LoginRequest) => {
        bootstrapRequestRef.current += 1;
        const response = await api.session.login(request);
        const normalized = normalizeSession(response);
        setSession(normalized);
        saveStoredJson(SESSION_STORAGE_KEY, normalized);
        return normalized;
      },
      signOut: async () => {
        bootstrapRequestRef.current += 1;
        try {
          await api.session.logout();
        } catch {
          // Best effort only.
        }
        setSession((current) => {
          const next = asAnonymousSession(current);
          saveStoredJson(SESSION_STORAGE_KEY, next);
          return next;
        });
      },
      switchTenant: async (tenantId: string) => {
        bootstrapRequestRef.current += 1;
        const response = await api.session.switchTenant(tenantId);
        const normalized = normalizeSession(response);
        setSession(normalized);
        saveStoredJson(SESSION_STORAGE_KEY, normalized);
      },
      requestRecovery: async (request: RecoveryRequest) => {
        const response = await api.session.recovery(request);
        return response.message;
      },
      refresh: async () => {
        bootstrapRequestRef.current += 1;
        const response = await api.session.current();
        const normalized = normalizeSession(response);
        setSession(normalized);
        saveStoredJson(SESSION_STORAGE_KEY, normalized);
      },
    };
  }, [ready, session]);

  return <EnterpriseSessionContext.Provider value={value}>{children}</EnterpriseSessionContext.Provider>;
}

export function useEnterpriseSession() {
  const context = useContext(EnterpriseSessionContext);
  if (!context) {
    throw new Error("useEnterpriseSession must be used within EnterpriseSessionProvider");
  }
  return context;
}
