import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock

from pybuilder.cli import StdOutLogger
from pybuilder.core import Project, Logger
from pybuilder.execution import ExecutionManager
from pybuilder.plugins import core_plugin
from pybuilder.reactor import Reactor

import pybuilder_integration

DIRNAME = os.path.dirname(os.path.abspath(__file__))


def _execute_create_files( command_and_arguments,
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
    return 0


class PybuilderIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpDir = tempfile.mkdtemp()
        self.project = Project(basedir=self.tmpDir)
        self.logger = StdOutLogger()
        self.execution_manager = ExecutionManager(self.logger)
        self.reactor = Reactor(self.logger, self.execution_manager)
        core_plugin.init(self.project)


    def tearDown(self):
        shutil.rmtree(self.tmpDir)

    def test_directory_preparation(self):
        pybuilder_integration.prepare_logs_directory(project=self.project)
        logs_dir = self.project.expand_path("$dir_logs")
        self.assertTrue(os.path.exists(f"{logs_dir}/integration"), "Failed to create logs directory")
        pybuilder_integration.prepare_reports_directory(project=self.project)
        reports_dir = self.project.expand_path("$dir_reports")
        self.assertTrue(os.path.exists(f"{reports_dir}/integration"), "Failed to create reports directory")

    def test_npm_install(self):
        mock_logger = Mock(Logger)
        reactor = Mock()
        reactor.python_env_registry = {}
        reactor.python_env_registry["pybuilder"] = pyb_env = Mock()
        pyb_env.environ = {}
        verify_mock = pyb_env.verify_can_execute = Mock()
        verify_execute = pyb_env.execute_command = Mock(side_effect=_execute_create_files)
        reactor.pybuilder_venv = pyb_env
        pybuilder_integration.install_abao(logger=mock_logger,
                                           project=self.project,
                                           reactor=reactor)
        verify_mock.assert_called_with(command_and_arguments=["npm", "--version"],
                                       prerequisite="npm",
                                       caller="integration_tests")
        verify_execute.assert_called_with(["npm","install","abao"],
                                          f"{self.tmpDir}/target/logs/integration/abao_npm_install")
        pybuilder_integration.install_protractor(logger=mock_logger,
                                                 project=self.project,
                                                 reactor=reactor)
        verify_mock.assert_called_with(command_and_arguments=["npm", "--version"],
                                       prerequisite="npm",
                                       caller="integration_tests")
        verify_execute.assert_called_with(["npm","install","protractor"],
                                          f"{self.tmpDir}/target/logs/integration/protractor_npm_install")