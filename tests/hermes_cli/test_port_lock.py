import os
import subprocess
import sys
import textwrap

from hermes_cli.port_lock import release_port_lock, try_claim_port


def test_desktop_child_accepts_ports_locked_by_its_owner(tmp_path, monkeypatch):
    port = 54321
    holder_script = textwrap.dedent(
        """
        import os
        import sys

        from hermes_cli.port_lock import try_claim_port

        lock = try_claim_port(int(sys.argv[2]), sys.argv[1])
        if lock is None:
            raise SystemExit("failed to acquire test port lock")
        print(os.getpid(), flush=True)
        sys.stdin.read(1)
        """
    )
    child_env = os.environ.copy()
    child_env.pop("HERMES_PORT_LOCK_OWNER_PID", None)
    holder = subprocess.Popen(
        [sys.executable, "-c", holder_script, str(tmp_path), str(port)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=child_env,
    )

    try:
        assert holder.stdout is not None
        owner_line = holder.stdout.readline().strip()
        if not owner_line:
            assert holder.stderr is not None
            raise AssertionError(holder.stderr.read())

        monkeypatch.setenv("HERMES_PORT_LOCK_OWNER_PID", owner_line)
        inherited = try_claim_port(port, tmp_path)

        assert inherited is not None
        inherited.release()
    finally:
        release_port_lock(port)
        if holder.stdin is not None:
            holder.stdin.close()
        holder.wait(timeout=5)

