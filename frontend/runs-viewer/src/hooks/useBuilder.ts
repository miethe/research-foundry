/**
 * useBuilder — React Query hooks for the Report Builder (public-multiuser-p2p3,
 * Phase 3 / Wave F).
 *
 * Dual-mode aware via src/api/reportsClient.ts: loopback mode reads/writes
 * `/api/reports/*`; static mode reads a bundled demo draft and rejects every
 * mutation with BuilderStaticModeError (surfaced to the UI via isError +
 * error.message so BuilderScreen can render the disabled-state banner).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addReportBlock,
  addReportClaimLink,
  addReportSourceLink,
  createReportDraft,
  createReportVersion,
  deleteReportBlock,
  fetchReportDraft,
  fetchReportDraftList,
  isBuilderLoopbackEnabled,
  listReportVersions,
  publishPreviewReportDraft,
  removeReportClaimLink,
  removeReportSourceLink,
  reorderReportBlocks,
  restoreReportVersion,
  updateReportBlock,
  verifyReportDraft,
} from "@/api/reportsClient";
import type {
  AddBlockRequest,
  AddClaimLinkRequest,
  AddSourceLinkRequest,
  CreateDraftRequest,
  ReportDraft,
  UpdateBlockRequest,
} from "@/types/rf/report_draft";

export { isBuilderLoopbackEnabled };

// ── Query keys ────────────────────────────────────────────────────────────────

export const builderDraftListQueryKey = ["rf", "builder", "drafts"] as const;
export const builderDraftQueryKey = (reportDraftId: string) => ["rf", "builder", "draft", reportDraftId] as const;
export const builderVersionsQueryKey = (reportDraftId: string) => ["rf", "builder", "versions", reportDraftId] as const;

// ── Reads ─────────────────────────────────────────────────────────────────────

export function useReportDraftList() {
  return useQuery({
    queryKey: builderDraftListQueryKey,
    queryFn: fetchReportDraftList,
    staleTime: 30_000,
  });
}

export function useReportDraft(reportDraftId: string | null | undefined) {
  return useQuery({
    queryKey: builderDraftQueryKey(reportDraftId ?? ""),
    queryFn: () => fetchReportDraft(reportDraftId as string),
    enabled: Boolean(reportDraftId),
    staleTime: 10_000,
  });
}

export function useReportVersions(reportDraftId: string | null | undefined) {
  return useQuery({
    queryKey: builderVersionsQueryKey(reportDraftId ?? ""),
    queryFn: () => listReportVersions(reportDraftId as string),
    enabled: Boolean(reportDraftId),
    staleTime: 30_000,
  });
}

// ── Mutations ─────────────────────────────────────────────────────────────────
//
// Every draft-shaped mutation optimistically writes its ReportDraft result
// straight into the query cache (setQueryData) rather than just invalidating
// — the Builder needs edits (block text, claim links) to reflect immediately
// for a usable typing/insert experience, and the draft is cheap to replace
// wholesale (builder_service.py mutators always return the full draft).

function useDraftMutation<TArgs>(
  mutationFn: (reportDraftId: string, args: TArgs) => Promise<ReportDraft>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportDraftId, args }: { reportDraftId: string; args: TArgs }) => mutationFn(reportDraftId, args),
    onSuccess: (draft, { reportDraftId }) => {
      queryClient.setQueryData(builderDraftQueryKey(reportDraftId), draft);
      queryClient.invalidateQueries({ queryKey: builderDraftListQueryKey });
    },
  });
}

export function useCreateReportDraft() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDraftRequest) => createReportDraft(payload),
    onSuccess: (draft) => {
      queryClient.setQueryData(builderDraftQueryKey(draft.report_draft_id), draft);
      queryClient.invalidateQueries({ queryKey: builderDraftListQueryKey });
    },
  });
}

export function useAddReportBlock() {
  return useDraftMutation<AddBlockRequest>((reportDraftId, payload) => addReportBlock(reportDraftId, payload));
}

export function useUpdateReportBlock() {
  return useDraftMutation<{ blockId: string; payload: UpdateBlockRequest }>((reportDraftId, { blockId, payload }) =>
    updateReportBlock(reportDraftId, blockId, payload),
  );
}

export function useDeleteReportBlock() {
  return useDraftMutation<string>((reportDraftId, blockId) => deleteReportBlock(reportDraftId, blockId));
}

export function useReorderReportBlocks() {
  return useDraftMutation<string[]>((reportDraftId, blockIds) => reorderReportBlocks(reportDraftId, blockIds));
}

export function useAddReportClaimLink() {
  return useDraftMutation<AddClaimLinkRequest>((reportDraftId, payload) => addReportClaimLink(reportDraftId, payload));
}

export function useRemoveReportClaimLink() {
  return useDraftMutation<string>((reportDraftId, claimLinkId) => removeReportClaimLink(reportDraftId, claimLinkId));
}

export function useAddReportSourceLink() {
  return useDraftMutation<AddSourceLinkRequest>((reportDraftId, payload) => addReportSourceLink(reportDraftId, payload));
}

export function useRemoveReportSourceLink() {
  return useDraftMutation<string>((reportDraftId, sourceLinkId) => removeReportSourceLink(reportDraftId, sourceLinkId));
}

export function useRestoreReportVersion() {
  return useDraftMutation<string>((reportDraftId, versionId) => restoreReportVersion(reportDraftId, versionId));
}

export function useCreateReportVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reportDraftId, note }: { reportDraftId: string; note?: string }) => createReportVersion(reportDraftId, { note }),
    onSuccess: (_pointer, { reportDraftId }) => {
      queryClient.invalidateQueries({ queryKey: builderVersionsQueryKey(reportDraftId) });
      queryClient.invalidateQueries({ queryKey: builderDraftQueryKey(reportDraftId) });
    },
  });
}

export function useVerifyReportDraft() {
  return useMutation({
    mutationFn: (reportDraftId: string) => verifyReportDraft(reportDraftId),
  });
}

export function usePublishPreviewReportDraft() {
  return useMutation({
    mutationFn: (reportDraftId: string) => publishPreviewReportDraft(reportDraftId),
  });
}
