import { useEffect, useState } from "react";
import { api, type ApiResult } from "../api";
import { Icon } from "../components/common";

/* ── library view ── */

export function Library({ onNeedSignIn }: { onNeedSignIn: () => void }) {
  const [result, setResult] = useState<ApiResult<unknown> | null>(null);
  useEffect(() => { void api.rules().then(setResult); }, []);
  return (
    <div className="view">
      <div className="panel">
        <h3><Icon name="menu_book" />Approved library</h3>
        <p>R-Codes, local planning policies and council checklists — versioned, citable, and the only sources LotFile answers from.</p>
        {result?.kind === "ok" && (
          <div className="state okay"><Icon name="check_circle" /><span>The approved source library is being loaded and reviewed.</span></div>
        )}
        {result?.kind === "auth" && (
          <div className="state"><Icon name="lock" /><span>Sign in to browse the library. <button className="btn alt" style={{ marginLeft: 8 }} onClick={onNeedSignIn}>Go to sign in</button></span></div>
        )}
        {result?.kind === "notBuilt" && (
          <div className="state"><Icon name="construction" /><span>Library browsing is coming soon.</span></div>
        )}
        {(result?.kind === "down" || result?.kind === "error" || result?.kind === "missing") && result !== null && (
          <div className="state"><Icon name="error" /><span>Couldn't reach the library ({result.kind}).</span></div>
        )}
      </div>
    </div>
  );
}
