import os

import pybuilder_integration
import pybuilder_integration.directory_utility
import pybuilder_integration.properties
import pybuilder_integration.tasks
import pybuilder_integration.tool_utility
from parent_test_case import ParentTestCase

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class ToolInstallTestCase(ParentTestCase):

    def test_npm_install(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        pybuilder_integration.tool_utility.install_abao(logger=mock_logger,
                                                        project=self.project,
                                                        reactor=reactor)
        self._assert_npm_install(verify_mock)
        verify_execute.assert_called_with(["npm", "install", "abao"],
                                          f"{self.tmpDir}/target/logs/integration/abao_npm_install")
        pybuilder_integration.tool_utility.install_protractor(logger=mock_logger,
                                                              project=self.project,
                                                              reactor=reactor)
        self._assert_npm_install(verify_mock)
        verify_execute.assert_called_with(["npm", "install", "protractor"],
                                          f"{self.tmpDir}/target/logs/integration/protractor_npm_install")
