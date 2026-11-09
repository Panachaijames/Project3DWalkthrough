// Scaffold U0 (docs/upload/DESIGN.md U-14.3; WORK_BREAKDOWN U0 step 6): the section 5 shapes exist twice, generated from
// the API's OpenAPI (src/api/generated) and hand-written (src/upload/contracts.ts). They must be mutually assignable, so an
// optional-versus-nullable difference shows here, at the scaffold, not at integration. Type-level only (`npm run
// typecheck`); nothing here runs.
import type * as G from '@/api/generated';
import type * as C from '@/upload/contracts';

/** true only when A and B are assignable both ways. */
type Same<A, B> = [A] extends [B] ? ([B] extends [A] ? true : false) : false;

export const sameBuildSettings: Same<G.BuildSettings, C.BuildSettings> = true;
export const sameBuildDetail: Same<G.BuildDetail, C.BuildDetail> = true;
export const sameUploadSession: Same<G.UploadSession, C.UploadSession> = true;
export const sameSourceFile: Same<G.SourceFile, C.SourceFile> = true;

// and the other section 5 bodies the web app sends or reads through the generated client
export const sameNewProjectRequest: Same<G.NewProjectRequest, C.NewProjectRequest> = true;
export const sameOfficeList: Same<G.OfficeList, C.OfficeList> = true;
export const sameUploadRequest: Same<G.UploadRequest, C.UploadRequest> = true;
export const sameUploadPartResult: Same<G.UploadPartResult, C.UploadPartResult> = true;
export const sameNewBuildRequest: Same<G.NewBuildRequest, C.NewBuildRequest> = true;
export const sameBuildList: Same<G.BuildList, C.BuildList> = true;
export const sameRunInfo: Same<G.RunInfo, C.RunInfo> = true;
export const sameBuildSettingsUpdate: Same<G.BuildSettingsUpdate, C.BuildSettingsUpdate> = true;
export const sameSaveBuildRequest: Same<G.SaveBuildRequest, C.SaveBuildRequest> = true;
export const sameLayerSuggestion: Same<G.LayerSuggestion, C.LayerSuggestion> = true;

// the check itself bites: a nullable field is not an optional one
// @ts-expect-error `office?: string` is not `office: string | null`
export const differs: Same<Omit<C.BuildSettings, 'office'> & { office?: string }, C.BuildSettings> = true;
