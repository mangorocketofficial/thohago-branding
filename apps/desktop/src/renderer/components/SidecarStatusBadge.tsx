import { translateSidecarState } from "../lib/korean";

type Props = {
  status: BootstrapState["sidecar"];
};

export function SidecarStatusBadge({ status }: Props) {
  return (
    <div className={`status-badge status-${status.state}`}>
      <span className="status-dot" />
      <span>{translateSidecarState(status.state)}</span>
      {status.pid ? <code>프로세스 {status.pid}</code> : null}
    </div>
  );
}
