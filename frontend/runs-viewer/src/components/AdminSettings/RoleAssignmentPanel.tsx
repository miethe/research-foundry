/**
 * RoleAssignmentPanel — Admin panel: read-only capability matrix.
 *
 * Displays a static table of capabilities by role (owner/admin/researcher/reviewer/viewer).
 * Capabilities are a frontend concern — not fetched from the API.
 * Actual role assignment for workspace members lives in WorkspaceMembersPanel.
 *
 * Graceful: always renders (no backend dependency). When identity.roles is absent
 * (AC-5c: normalised to []) → viewer-equivalent restricted notice shown.
 *
 * CSS: rv-admin-roles-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: table headers with scope, readable contrast, caption for AT.
 */

import { useAuth } from "@/auth/AuthContext";

// ── Types ─────────────────────────────────────────────────────────────────────

interface CapabilityRow {
  capability: string;
  owner: boolean;
  admin: boolean;
  researcher: boolean;
  reviewer: boolean;
  viewer: boolean;
}

// ── Static capability matrix ──────────────────────────────────────────────────

/**
 * Frontend-defined capability matrix — not fetched. Source of truth for the
 * display; server-side enforcement (P5.2 require_role) is the actual gate.
 */
const CAPABILITY_MATRIX: CapabilityRow[] = [
  { capability: "View runs",              owner: true,  admin: true,  researcher: true,  reviewer: true,  viewer: true  },
  { capability: "Create runs",            owner: true,  admin: true,  researcher: true,  reviewer: false, viewer: false },
  { capability: "Edit run metadata",      owner: true,  admin: true,  researcher: true,  reviewer: false, viewer: false },
  { capability: "View claims",            owner: true,  admin: true,  researcher: true,  reviewer: true,  viewer: true  },
  { capability: "Edit claims",            owner: true,  admin: true,  researcher: true,  reviewer: false, viewer: false },
  { capability: "Approve runs",           owner: true,  admin: true,  researcher: false, reviewer: true,  viewer: false },
  { capability: "Manage workspace",       owner: true,  admin: true,  researcher: false, reviewer: false, viewer: false },
  { capability: "Assign roles",           owner: true,  admin: false, researcher: false, reviewer: false, viewer: false },
  { capability: "Configure rate limits",  owner: true,  admin: true,  researcher: false, reviewer: false, viewer: false },
  { capability: "Delete workspace",       owner: true,  admin: false, researcher: false, reviewer: false, viewer: false },
];

const ROLES = ["owner", "admin", "researcher", "reviewer", "viewer"] as const;
type Role = typeof ROLES[number];

// ── Sub-components ────────────────────────────────────────────────────────────

function CapabilityCell({ allowed }: { allowed: boolean }) {
  return (
    <td
      className={`rv-admin-roles-panel__cell ${
        allowed
          ? "rv-admin-roles-panel__cell--allowed"
          : "rv-admin-roles-panel__cell--denied"
      }`}
    >
      {/* aria-hidden: the th[scope=row] carries the semantic; the cell value is
          decorative. Screen readers read row + header + cell together. */}
      <span
        className="rv-admin-roles-panel__cell-icon"
        aria-hidden="true"
      >
        {allowed ? "+" : "–"}
      </span>
      <span className="rv-visually-hidden">{allowed ? "allowed" : "not allowed"}</span>
    </td>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export function RoleAssignmentPanel() {
  const { identity } = useAuth();
  // AC-5c: identity.roles normalised to [] when absent — never elevates privilege.
  const userRoles: string[] = identity?.roles ?? [];
  const isPrivileged = userRoles.some((r) => ["owner", "admin"].includes(r));

  return (
    <div
      className="rv-admin-roles-panel"
      aria-label="Role capability matrix"
      data-testid="admin-roles-panel"
    >
      {!isPrivileged && (
        <div
          className="rv-admin-roles-panel__notice"
          role="note"
          data-testid="admin-roles-panel-restricted"
        >
          Viewing capability reference. Full matrix visible to admin and owner
          roles.
        </div>
      )}

      <div className="rv-admin-roles-panel__table-wrap">
        <table
          className="rv-admin-roles-panel__table"
          aria-label="Capability matrix by role"
        >
          <caption className="rv-visually-hidden">
            Role capability matrix: rows are capabilities, columns are roles.
            Plus sign means allowed; dash means not allowed.
          </caption>
          <thead>
            <tr>
              <th scope="col">Capability</th>
              {ROLES.map((role) => (
                <th
                  key={role}
                  scope="col"
                  className="rv-admin-roles-panel__role-header"
                >
                  {role}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CAPABILITY_MATRIX.map((row) => (
              <tr
                key={row.capability}
                data-testid={`capability-row-${row.capability
                  .replace(/\s+/g, "-")
                  .toLowerCase()}`}
              >
                <th
                  scope="row"
                  className="rv-admin-roles-panel__capability-name"
                >
                  {row.capability}
                </th>
                {ROLES.map((role) => (
                  <CapabilityCell
                    key={role}
                    allowed={row[role as Role]}
                  />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RoleAssignmentPanel;
