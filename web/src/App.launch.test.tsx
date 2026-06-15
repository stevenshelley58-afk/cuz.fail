import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

type ApiMock = {
  session: ReturnType<typeof vi.fn>;
  guestSession: ReturnType<typeof vi.fn>;
  magicLinkVerify: ReturnType<typeof vi.fn>;
  projects: ReturnType<typeof vi.fn>;
  searchAddress: ReturnType<typeof vi.fn>;
  createProject: ReturnType<typeof vi.fn>;
  resolveAddress: ReturnType<typeof vi.fn>;
};

type PlausibleWindow = Window & {
  plausible?: (
    eventName: string,
    options?: { props?: Record<string, string | number | boolean> },
  ) => void;
};

function installHead() {
  document.head.innerHTML = `
    <meta name="description" content="">
    <meta property="og:title" content="">
    <meta property="og:description" content="">
    <meta property="og:url" content="">
    <meta name="twitter:title" content="">
    <meta name="twitter:description" content="">
    <link rel="canonical" href="">
  `;
}

function setPath(path: string) {
  window.history.replaceState(null, "", path);
}

function installBrowserStorage() {
  const data = new Map<string, string>();
  const storage = {
    getItem: vi.fn((key: string) => data.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => data.set(key, value)),
    removeItem: vi.fn((key: string) => data.delete(key)),
    clear: vi.fn(() => data.clear()),
    key: vi.fn((index: number) => Array.from(data.keys())[index] ?? null),
    get length() {
      return data.size;
    },
  };
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: storage,
  });
}

async function renderApp(api: ApiMock) {
  vi.doMock("./api", () => ({ api }));
  vi.doMock("./views/wizard", () => ({
    WizardShell: ({ wizard }: { wizard: { address: string; projectId: string } }) => (
      <div data-testid="wizard-shell">{wizard.address} / {wizard.projectId}</div>
    ),
  }));
  vi.doMock("./views/projects", () => ({
    projectList: (r: { kind: string; data?: unknown }) => (r.kind === "ok" && Array.isArray(r.data) ? r.data : []),
    Projects: ({ onProjectOpen }: { onProjectOpen: (projectId: string) => void }) => (
      <div data-testid="projects-view">
        <button onClick={() => onProjectOpen("project-1")}>Open saved project</button>
      </div>
    ),
    ProjectDetail: ({ projectId }: { projectId: string }) => (
      <div data-testid="project-detail">Project detail {projectId}</div>
    ),
  }));
  vi.doMock("./views/library", () => ({
    Library: () => <div data-testid="library-view">Library browsing is coming soon.</div>,
  }));
  const { App } = await import("./App");
  render(<App />);
}

function makeApi(overrides: Partial<ApiMock> = {}): ApiMock {
  const api: ApiMock = {
    session: vi.fn().mockResolvedValue({ kind: "auth" }),
    guestSession: vi.fn().mockResolvedValue({ kind: "ok", data: { role: "guest" } }),
    magicLinkVerify: vi.fn().mockResolvedValue({ kind: "ok", data: {} }),
    projects: vi.fn().mockResolvedValue({ kind: "ok", data: [] }),
    searchAddress: vi.fn().mockResolvedValue({ kind: "ok", data: { items: [], count: 0 } }),
    createProject: vi.fn().mockResolvedValue({
      kind: "ok",
      data: { id: "project-1", address: "3 Black Swan Rise, Beeliar" },
    }),
    resolveAddress: vi.fn().mockResolvedValue({
      kind: "ok",
      data: {
        project_id: "project-1",
        resolution_status: "resolved",
        confidence: "high",
        target_crs: "EPSG:7844",
        issues: [],
        provenance: [],
        facts: [],
      },
    }),
    ...overrides,
  };
  return api;
}

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  sessionStorage.clear();
  installBrowserStorage();
  Object.defineProperty(window, "scrollTo", {
    configurable: true,
    value: vi.fn(),
  });
  installHead();
  setPath("/");
});

afterEach(() => {
  cleanup();
  vi.resetModules();
  vi.clearAllMocks();
  vi.doUnmock("./api");
  vi.doUnmock("./views/wizard");
  delete (window as PlausibleWindow).plausible;
  sessionStorage.clear();
});

test("landing route renders and applies launch metadata", async () => {
  await renderApp(makeApi());

  expect(await screen.findByRole("heading", { name: /check a block/i })).toBeTruthy();
  await waitFor(() => {
    expect(document.title).toBe("LotFile - WA R-Code & Planning Compliance Checker");
  });
  expect(document.querySelector('meta[property="og:title"]')?.getAttribute("content")).toBe(
    "LotFile - WA R-Code & Planning Compliance Checker",
  );
  expect(document.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe("https://lotfile.app/");
});

test("privacy and terms navigation updates route metadata without a full reload", async () => {
  await renderApp(makeApi());

  const launchNav = await screen.findByRole("navigation", { name: /launch navigation/i });
  await userEvent.click(within(launchNav).getByRole("button", { name: /^privacy$/i }));
  await waitFor(() => expect(window.location.pathname).toBe("/privacy"));
  expect(await screen.findByRole("heading", { name: "Privacy" })).toBeTruthy();
  expect(document.title).toBe("Privacy - LotFile");
  expect(document.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe("https://lotfile.app/privacy");

  await userEvent.click(
    within(screen.getByRole("navigation", { name: /launch navigation/i })).getByRole("button", { name: /^terms$/i }),
  );
  await waitFor(() => expect(window.location.pathname).toBe("/terms"));
  expect(await screen.findByRole("heading", { name: "Terms of use" })).toBeTruthy();
  expect(document.title).toBe("Terms - LotFile");
  expect(document.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe("https://lotfile.app/terms");
});

test("landing address handoff stores address, opens app, creates guest project, and clears storage", async () => {
  const plausible = vi.fn();
  (window as PlausibleWindow).plausible = plausible as PlausibleWindow["plausible"];
  const api = makeApi({
    session: vi.fn()
      .mockResolvedValueOnce({ kind: "auth" })
      .mockResolvedValue({ kind: "ok", data: { role: "guest" } }),
    searchAddress: vi.fn().mockResolvedValue({
      kind: "ok",
      data: {
        items: [
          {
            address: "3 Black Swan Rise, Beeliar",
            address_point_id: "gnaf-1",
            gnaf_pid: "GNAF-1",
            lat: -32.1,
            lon: 115.8,
            score: 0.99,
          },
        ],
        count: 1,
      },
    }),
  });
  await renderApp(api);

  await userEvent.type(
    await screen.findByLabelText(/street address/i),
    "3 Black Swan Rise, Beeliar",
  );
  await userEvent.click(screen.getByRole("button", { name: /check an address free/i }));

  await waitFor(() => expect(window.location.pathname).toBe("/app"));
  await waitFor(() => expect(api.guestSession).toHaveBeenCalledOnce());
  await waitFor(() => expect(api.createProject).toHaveBeenCalledWith("3 Black Swan Rise, Beeliar"));
  expect(api.resolveAddress).toHaveBeenCalledWith("project-1", "3 Black Swan Rise, Beeliar");
  expect(plausible).toHaveBeenCalledWith("project_created", { props: { guest: true } });
  expect(sessionStorage.getItem("lotfile_launch_address")).toBeNull();
  expect((await screen.findByTestId("wizard-shell")).textContent).toContain(
    "3 Black Swan Rise, Beeliar / project-1",
  );
});

test("landing address input shows predictive address suggestions", async () => {
  const api = makeApi({
    session: vi.fn()
      .mockResolvedValueOnce({ kind: "auth" })
      .mockResolvedValue({ kind: "ok", data: { role: "guest" } }),
    searchAddress: vi.fn().mockResolvedValue({
      kind: "ok",
      data: {
        items: [
          {
            address: "14 Montague Street, Mount Lawley WA 6050",
            address_point_id: "gnaf-14",
            gnaf_pid: "GNAF-14",
            lat: -31.94,
            lon: 115.87,
            score: 0.91,
          },
        ],
        count: 1,
      },
    }),
    createProject: vi.fn().mockResolvedValue({
      kind: "ok",
      data: { id: "project-14", address: "14 Montague Street, Mount Lawley WA 6050" },
    }),
  });
  await renderApp(api);

  await userEvent.type(await screen.findByLabelText(/street address/i), "14 montague");

  expect(await screen.findByRole("listbox", { name: /address suggestions/i })).toBeTruthy();
  await userEvent.click(screen.getByRole("option", { name: /14 montague street/i }));

  await waitFor(() => expect(window.location.pathname).toBe("/app"));
  await waitFor(() => expect(api.createProject).toHaveBeenCalledWith("14 Montague Street, Mount Lawley WA 6050"));
});

test("landing address input suggests address-like street names without a house number", async () => {
  const api = makeApi({
    searchAddress: vi.fn().mockResolvedValue({
      kind: "ok",
      data: {
        items: [
          {
            address: "3 Black Swan Rise, Beeliar WA 6164",
            address_point_id: "gnaf-black-swan",
            gnaf_pid: "GNAF-BLACK-SWAN",
            lat: -32.13,
            lon: 115.81,
            score: 0.88,
          },
        ],
        count: 1,
      },
    }),
  });
  await renderApp(api);

  await userEvent.type(await screen.findByLabelText(/street address/i), "Black Swan Rise");

  expect(await screen.findByRole("listbox", { name: /address suggestions/i })).toBeTruthy();
  expect(screen.getByRole("option", { name: /3 black swan rise/i })).toBeTruthy();
});

test("app address box suggests address-like street names", async () => {
  const api = makeApi({
    session: vi.fn().mockResolvedValue({
      kind: "ok",
      data: { role: "owner", email: "owner@example.test" },
    }),
    searchAddress: vi.fn().mockResolvedValue({
      kind: "ok",
      data: {
        items: [
          {
            address: "3 Black Swan Rise, Beeliar WA 6164",
            address_point_id: "gnaf-black-swan",
            gnaf_pid: "GNAF-BLACK-SWAN",
            lat: -32.13,
            lon: 115.81,
            score: 0.88,
          },
        ],
        count: 1,
      },
    }),
  });
  setPath("/app");
  await renderApp(api);

  await userEvent.type(await screen.findByLabelText(/address or planning question/i), "Black Swan Rise");

  expect(await screen.findByRole("listbox", { name: /address suggestions/i })).toBeTruthy();
  expect(screen.getByRole("option", { name: /3 black swan rise/i })).toBeTruthy();
});

test("magic-link verify route verifies token and rewrites to app", async () => {
  const api = makeApi({
    session: vi.fn().mockResolvedValue({
      kind: "ok",
      data: { role: "owner", email: "owner@example.test" },
    }),
  });
  setPath("/auth/magic-link/verify?token=abc123");

  await renderApp(api);

  await waitFor(() => expect(api.magicLinkVerify).toHaveBeenCalledWith("abc123"));
  await waitFor(() => expect(window.location.pathname).toBe("/app"));
});

test("magic-link verify failure opens sign-in retry without leaving the app stuck", async () => {
  const api = makeApi({
    magicLinkVerify: vi.fn().mockResolvedValue({ kind: "auth" }),
    session: vi.fn()
      .mockResolvedValueOnce({ kind: "auth" })
      .mockResolvedValue({ kind: "ok", data: { role: "guest" } }),
  });
  setPath("/auth/magic-link/verify?token=expired");

  await renderApp(api);

  await waitFor(() => expect(api.magicLinkVerify).toHaveBeenCalledWith("expired"));
  await waitFor(() => expect(window.location.pathname).toBe("/app"));
  await waitFor(() => expect(api.guestSession).toHaveBeenCalledOnce());
  expect(await screen.findByText("That sign-in link has expired or could not be verified. Send yourself a new link.")).toBeTruthy();
  expect(screen.getByRole("button", { name: /send sign-in link/i })).toBeTruthy();
});

test("shell navigation clears an open project detail", async () => {
  setPath("/app");
  await renderApp(makeApi({
    session: vi.fn().mockResolvedValue({ kind: "ok", data: { role: "guest" } }),
  }));

  await waitFor(() => expect(screen.getAllByRole("button", { name: /^projects$/i }).length).toBeGreaterThan(0));
  await userEvent.click(screen.getAllByRole("button", { name: /^projects$/i })[0]);
  await userEvent.click(screen.getByRole("button", { name: /open saved project/i }));
  expect(await screen.findByTestId("project-detail")).toBeTruthy();

  await userEvent.click(screen.getAllByRole("button", { name: /^library$/i })[0]);

  expect(await screen.findByTestId("library-view")).toBeTruthy();
  expect(screen.queryByTestId("project-detail")).toBeNull();
});
