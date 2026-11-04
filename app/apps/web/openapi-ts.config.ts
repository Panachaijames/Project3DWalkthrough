// Typed API client from FastAPI's OpenAPI (DESIGN.md 10.5). Run inside apps/web (`npm run gen:api` from app/ does):
// openapi-ts resolves `input` and `output` against the working folder. The output is generated: never edit it.
import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: './openapi.json',
  output: './src/api/generated',
  plugins: ['@hey-api/client-fetch', '@hey-api/typescript', '@hey-api/sdk', '@tanstack/react-query'],
});
