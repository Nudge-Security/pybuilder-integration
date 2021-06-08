import os
import shutil
import tempfile
from typing import Optional, Union, List, Sequence
from unittest import TestCase
from unittest.mock import Mock

import py
import pytest
from pybuilder.core import Project, Logger
from pybuilder.plugins import core_plugin
from pybuilder.plugins.python.core_plugin import init_python_directories

from pybuilder_integration import ENVIRONMENT, init_plugin


def _pytest_main(args: Optional[Union[List[str], py.path.local]] = None,
                 plugins: Optional[Sequence[Union[str, object]]] = None,):
    return 0

fail = False

def _execute_create_files(command_and_arguments,
                          outfile_name=None,
                          env=None,
                          cwd=None,
                          error_file_name=None,
                          shell=False,
                          no_path_search=False,
                          inherit_env=True):
    if not error_file_name:
        error_file_name = "{0}.err".format(outfile_name)
    # touch the files to make sure they exist
    with open(outfile_name, "w") as of:
        pass
    with open(error_file_name, "w") as of:
        pass
    if fail:
        return 1
    else:
        return 0

class ParentTestCase(TestCase):

    def setUp(self) -> None:
        self.tmpDir = tempfile.mkdtemp()
        self.project = Project(basedir=self.tmpDir)
        self.project.set_property(ENVIRONMENT,"unit-test")
        core_plugin.init(self.project)
        init_plugin(self.project)
        init_python_directories(self.project)

    def tearDown(self):
        shutil.rmtree(self.tmpDir)

    def generate_mock(self):
        mock_logger = Mock(Logger)
        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        pyb_env.environ = {}
        pytest.main = pytest_main = Mock(side_effect=_pytest_main)
        self.pytest_main_mock = pytest_main
        verify_mock = pyb_env.verify_can_execute = Mock()
        verify_execute = pyb_env.execute_command = Mock(side_effect=_execute_create_files)
        reactor.pybuilder_venv = pyb_env
        return mock_logger, verify_mock, verify_execute, reactor

    def _assert_aws_check(self, verify_mock):
        verify_mock.assert_any_call(command_and_arguments=["aws", "--version"],
                                    prerequisite="aws cli",
                                    caller="integration_tests")

    def _assert_npm_install(self, verify_mock):
        verify_mock.assert_any_call(command_and_arguments=["npm", "--version"],
                                    prerequisite="npm",
                                    caller="integration_tests")

    def _assert_s3_transfer(self, source, destination, verify_execute, recursive=True):
        args = ["aws", "s3", "cp", source, destination]
        if recursive:
            args.append("--recursive")
        verify_execute.assert_any_call(args,
                                       f"{self.tmpDir}/target/logs/integration/s3-artifact-transfer")

    def _configure_mock_tests_dir(self, default_path, file_name):
        os.makedirs(f"{default_path}")
        test_file = f"{default_path}/{file_name}"
        with open(test_file, "w") as fp:
            # touch file
            pass
        return test_file

    def _configure_mock_test_files(self, file_name, tool):
        # Configure mock test files
        return self._configure_mock_tests_dir(f"{self.tmpDir}/src/integrationtest/{tool}", file_name)

    def _configure_mock_tests(self, distribution_directory):
        tavern_test_file_name = "test.tavern.yaml"
        cypress_test_file_name = "test.json"
        tavern_test_file_path = self._configure_mock_tests_dir(f"{distribution_directory}/tavern", tavern_test_file_name)
        cypress_test_file_path = self._configure_mock_tests_dir(f"{distribution_directory}/cypress",
                                                                   cypress_test_file_name)
        return cypress_test_file_path, tavern_test_file_path
