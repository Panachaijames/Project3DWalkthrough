// Types for tools/openapi-additive-rules.mjs (the rules of tools/check-openapi-additive.mjs; rooms scaffold R0).
/** Why a component schema's change is not additive, or null (deep-equal, or it only gained properties that are not required). */
export declare function schemaChange(old: unknown, now: unknown): string | null;
/** Why an exported symbol's change is not additive, or null (identical, or an interface / object type that only gained optional members). */
export declare function symbolChange(old: string, now: string): string | null;
