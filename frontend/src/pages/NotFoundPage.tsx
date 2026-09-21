import { Link } from 'react-router';
import { Empty, Panel } from '../components/common/UI';
export default function NotFoundPage() {
  return (
    <Panel>
      <Empty
        title="This page isn’t in the workspace"
        text="Return to the dashboard to continue your research."
        action={
          <Link className="button primary" to="/">
            Back to dashboard
          </Link>
        }
      />
    </Panel>
  );
}
