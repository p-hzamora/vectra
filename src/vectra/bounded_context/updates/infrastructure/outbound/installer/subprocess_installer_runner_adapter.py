"""Runs an upgrade plan as a child process."""

import subprocess

from vectra.bounded_context.updates.application.ports.installer import IInstallerRunner
from vectra.bounded_context.updates.domain.value_objects import UpgradePlan
from vectra.exceptions import UpgradeFailedError

_TAIL_LINES: int = 20


class SubprocessInstallerRunnerAdapter(IInstallerRunner):
    """`subprocess.run` over an argv list: no shell, output captured so `--json` stays clean."""

    def run(self, plan: UpgradePlan) -> None:
        try:
            done = subprocess.run(  # noqa: S603 - argv list built from validated values, no shell
                plan.argv, capture_output=True, text=True, check=False, shell=False
            )
        except OSError as failure:
            raise UpgradeFailedError(
                f"Could not start the installer: {failure}",
                {"command": plan.command},
                next_steps=[f"Run it yourself: {plan.command}"],
            ) from failure
        if done.returncode != 0:
            tail: str = "\n".join(done.stderr.splitlines()[-_TAIL_LINES:])
            raise UpgradeFailedError(
                f"The installer exited with code {done.returncode}.",
                {"command": plan.command, "exit_code": done.returncode, "stderr_tail": tail},
                next_steps=[
                    f"Fix the problem shown in stderr_tail, then run: {plan.command}",
                    "Your configuration and indexes were not touched.",
                ],
            )
