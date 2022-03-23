# Copyright 2018 Easymov Robotics
# Licensed under the Apache License, Version 2.0

import os
from pathlib import Path

from colcon_cargo.task.cargo import CARGO_EXECUTABLE
from colcon_core.event.test import TestFailure
from colcon_core.logging import colcon_logger
from colcon_core.plugin_system import satisfies_version
from colcon_core.shell import get_command_environment
from colcon_core.task import run
from colcon_core.task import TaskExtensionPoint

logger = colcon_logger.getChild(__name__)


class CargoTestTask(TaskExtensionPoint):
    """Test Cargo packages."""

    def __init__(self):  # noqa: D107
        super().__init__()
        satisfies_version(TaskExtensionPoint.EXTENSION_POINT_VERSION, '^1.0')

    def add_arguments(self, *, parser):  # noqa: D102
        pass

    async def test(self, *, additional_hooks=None):  # noqa: D102
        pkg = self.context.pkg
        args = self.context.args

        logger.info(
            "Testing Cargo package in '{args.path}'".format_map(locals()))

        assert os.path.exists(args.build_base), \
            'Has this package been built before?'

        test_results_path = os.path.join(args.build_base, 'test_results')
        os.makedirs(test_results_path, exist_ok=True)

        try:
            env = await get_command_environment(
                'test', args.build_base, self.context.dependencies)
        except RuntimeError as e:
            logger.error(str(e))
            return 1

        if CARGO_EXECUTABLE is None:
            raise RuntimeError("Could not find 'cargo' executable")

        env['CARGO_TARGET_DIR'] = args.build_base

        junit_xml_path = Path(
            self.context.args.test_result_base
            if self.context.args.test_result_base
            else self.context.args.build_base) / 'cargo_test.xml'

        junit_xml_path.parent.mkdir(parents=True, exist_ok=True)
        junit_xml_path.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="{self.context.pkg.name}" tests="1" failures="0" time="0" errors="1" skipped="0">
  <testcase classname="{self.context.pkg.name}" name="pytest.missing_result" time="0">
    <failure message="The test invocation failed without generating a result file."/>
  </testcase>
</testsuite>
""".format_map(locals()))  # noqa: E501

        # invoke cargo test
        completed = await run(
            self.context,
            [
                CARGO_EXECUTABLE,
                'test',
                '--all-targets',
                '-q',
            ],
            cwd=args.path, env=env)

        cmpstdout = completed.stderr

        if completed.returncode:
            self.context.put_event_into_queue(TestFailure(pkg.name))
            # the return code should still be 0
