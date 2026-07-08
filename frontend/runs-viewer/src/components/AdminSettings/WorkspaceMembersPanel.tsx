/**
 * WorkspaceMembersPanel — Admin panel: workspace member list + role assignment.
 *
 * Fetches GET /api/admin/workspace → { members: Array<{ user_id, email, role }>, workspace_id }
 * Role changes via PATCH /api/admin/members/{user_id}/role → 204 or { error: string }.
 *
 * GATE-901: if fetch fails or members array is null/absent → disabled panel with
 * "Member data unavailable" message.
 *
 * CSS: rv-admin-members-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: table headers with scope, keyboard nav on role dropdown,
 * visible focus on all interactive elements.
 */

import { useState, useEffect } from "react";
import { getLoopbackBase, getLoopbackAuthHeaders, ClientError } from "@/api/client";

// ── Types ─────────────────────────────────────────────────────────────────────

interface WorkspaceMember {
  user_id: string;
  email: string;
  role: string;
}

interface WorkspaceData {
  members: WorkspaceMember[] | null;
  workspace_id: string;
}

const AVAILABLE_ROLES = [
  "owner",
  "admin",
  "researcher",
  "reviewer",
  "viewer",
] as const;

// ── Component ─────────────────────────────────────────────────────────────────

export function WorkspaceMembersPanel() {
  const [data, setData] = useState<WorkspaceData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [savingUserId, setSavingUserId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setFetchError(null);
      try {
        const url = `${getLoopbackBase()}/admin/workspace`;
        const res = await fetch(url, {
          method: "GET",
          headers: getLoopbackAuthHeaders(),
        });
        if (!res.ok) {
          throw new ClientError(
            res.status,
            `GET /admin/workspace failed: ${res.statusText}`,
          );
        }
        const json = (await res.json()) as WorkspaceData;
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) {
          setFetchError(
            err instanceof ClientError
              ? err.message
              : "Failed to load workspace members",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleRoleChange(userId: string, newRole: string): Promise<void> {
    setSavingUserId(userId);
    setSaveError(null);
    try {
      const url = `${getLoopbackBase()}/admin/members/${encodeURIComponent(userId)}/role`;
      const res = await fetch(url, {
        method: "PATCH",
        headers: {
          ...getLoopbackAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ role: newRole }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        throw new ClientError(
          res.status,
          body.error ?? `Role update failed (HTTP ${res.status})`,
        );
      }
      setData((prev) => {
        if (!prev || !Array.isArray(prev.members)) return prev;
        return {
          ...prev,
          members: prev.members.map((m) =>
            m.user_id === userId ? { ...m, role: newRole } : m,
          ),
        };
      });
    } catch (err) {
      setSaveError(
        err instanceof ClientError ? err.message : "Failed to update role",
      );
    } finally {
      setSavingUserId(null);
    }
  }

  // GATE-901: fetch failed or members array null/absent → disabled panel
  if (!isLoading && (fetchError !== null || !Array.isArray(data?.members))) {
    return (
      <div
        className="rv-admin-members-panel rv-admin-members-panel--disabled"
        data-testid="admin-members-panel-disabled"
      >
        <p className="rv-admin-members-panel__unavailable" role="status">
          Member data unavailable
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="rv-admin-members-panel rv-admin-members-panel--loading"
        aria-busy="true"
        data-testid="admin-members-panel-loading"
      >
        <span>Loading members...</span>
      </div>
    );
  }

  const members = data!.members as WorkspaceMember[];

  return (
    <div className="rv-admin-members-panel" data-testid="admin-members-panel">
      {saveError !== null && (
        <div
          className="rv-admin-members-panel__error"
          role="alert"
          aria-live="assertive"
          data-testid="admin-members-save-error"
        >
          {saveError}
        </div>
      )}

      {members.length === 0 ? (
        <p
          className="rv-admin-members-panel__empty"
          data-testid="admin-members-empty"
        >
          No workspace members found.
        </p>
      ) : (
        <div className="rv-admin-members-panel__table-wrap">
          <table
            className="rv-admin-members-panel__table"
            aria-label={`Workspace members (${members.length})`}
          >
            <thead>
              <tr>
                <th scope="col">Email</th>
                <th scope="col">Current role</th>
                <th scope="col">Change role</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr
                  key={member.user_id}
                  data-testid={`member-row-${member.user_id}`}
                >
                  <td>{member.email}</td>
                  <td>
                    <span
                      className={`rv-admin-members-panel__role-badge rv-admin-members-panel__role-badge--${member.role}`}
                      data-testid={`member-role-${member.user_id}`}
                    >
                      {member.role}
                    </span>
                  </td>
                  <td>
                    {/* Label is visually hidden; aria-label on <select> covers AT users */}
                    <label
                      htmlFor={`role-select-${member.user_id}`}
                      className="rv-visually-hidden"
                    >
                      Change role for {member.email}
                    </label>
                    <div className="rv-admin-members-panel__select-wrap">
                      <select
                        id={`role-select-${member.user_id}`}
                        className="rv-settings__select rv-admin-members-panel__role-select"
                        value={member.role}
                        disabled={savingUserId === member.user_id}
                        onChange={(e) =>
                          void handleRoleChange(member.user_id, e.target.value)
                        }
                        data-testid={`role-select-${member.user_id}`}
                        aria-label={`Change role for ${member.email}`}
                      >
                        {AVAILABLE_ROLES.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      {savingUserId === member.user_id && (
                        <span
                          className="rv-admin-members-panel__saving"
                          aria-live="polite"
                        >
                          Saving...
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default WorkspaceMembersPanel;
