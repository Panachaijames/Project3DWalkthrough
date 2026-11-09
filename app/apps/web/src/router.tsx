// The staff app's routes (DESIGN.md 15.1): React Router 8 in data mode (createBrowserRouter; RouterProvider from
// react-router/dom in main.tsx), loaders on TanStack Query's cache.
//   /                           -> /projects
//   /projects                   project list (loader: ensureQueryData(listProjectsOptions()), not awaited)
//   /projects/:projectId        -> /projects/:projectId/v/<latestVersion> (loader: getProject)
//   /projects/:projectId/v/:n   project page (loader: getVersion, then model and stages)
//   /projects/new                         New project (loader: listOffices, not awaited)      docs/upload/DESIGN.md
//   /projects/:projectId/builds/new       Upload (loader: getProject; listBuilds not awaited)  U-14.1; static routes
//   /projects/:projectId/builds/:buildId  Build, ?step= (loader: getBuild with settings,       before :projectId
//                                         getProject)
//   *                           not found
// createRoutes is also what the unit tests mount, in a memory router.
import type { QueryClient } from '@tanstack/react-query';
import { createBrowserRouter, Navigate, type RouteObject } from 'react-router';
import { NotFound, RouteError } from './pages/NotFound';
import { ProjectPageFallback, ProjectRedirect, projectRedirectLoader } from './pages/ProjectRedirect';
import { BuildPage, buildLoader } from './pages/BuildPage';
import { NewProjectPage, newProjectLoader } from './pages/NewProjectPage';
import { ProjectsPage, ProjectsPageFallback, projectsLoader } from './pages/ProjectsPage';
import { ProjectVersionPage, versionLoader } from './pages/ProjectVersionPage';
import { UploadPage, uploadLoader } from './pages/UploadPage';

export function createRoutes(queryClient: QueryClient): RouteObject[] {
  return [
    { path: '/', element: <Navigate to="/projects" replace />, ErrorBoundary: RouteError },
    {
      path: '/projects',
      loader: projectsLoader(queryClient),
      Component: ProjectsPage,
      HydrateFallback: ProjectsPageFallback,
      ErrorBoundary: RouteError,
    },
    { path: '/projects/new', loader: newProjectLoader(queryClient), Component: NewProjectPage, ErrorBoundary: RouteError },
    {
      path: '/projects/:projectId/builds/new',
      loader: uploadLoader(queryClient),
      Component: UploadPage,
      HydrateFallback: ProjectPageFallback,
      ErrorBoundary: RouteError,
    },
    {
      path: '/projects/:projectId/builds/:buildId',
      loader: buildLoader(queryClient),
      Component: BuildPage,
      HydrateFallback: ProjectPageFallback,
      ErrorBoundary: RouteError,
    },
    {
      path: '/projects/:projectId',
      loader: projectRedirectLoader(queryClient),
      Component: ProjectRedirect,
      HydrateFallback: ProjectPageFallback,
      ErrorBoundary: RouteError,
    },
    {
      path: '/projects/:projectId/v/:n',
      loader: versionLoader(queryClient),
      Component: ProjectVersionPage,
      HydrateFallback: ProjectPageFallback,
      ErrorBoundary: RouteError,
    },
    { path: '*', Component: NotFound, ErrorBoundary: RouteError },
  ];
}

export function createAppRouter(queryClient: QueryClient) {
  return createBrowserRouter(createRoutes(queryClient));
}
