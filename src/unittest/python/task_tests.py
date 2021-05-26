import os
from zipfile import ZipFile

import pybuilder_integration
import pybuilder_integration.directory_utility
import pybuilder_integration.properties
import pybuilder_integration.tasks
import pybuilder_integration.tool_utility
from parent_test_case import ParentTestCase
from pybuilder_integration import directory_utility, artifact_manager

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class TaskTestCase(ParentTestCase):

    def test_verify_protractor(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        target_url = "foo"
        file_name = "test.json"
        test_file = self._configure_mock_test_files(file_name, "protractor")
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, target_url)
        pybuilder_integration.tasks.verify_protractor(project=self.project,
                                                      logger=mock_logger,
                                                      reactor=reactor)
        self._assert_protractor_run(f"{self.tmpDir}/src/integrationtest/protractor", target_url, verify_execute)
        self._validate_zip_file(file_name, "protractor")


    def _get_integration_distribution_zip(self, tool):
        return self.project.expand_path(
            f"$dir_dist/integration/{tool}-{self.project.name}.zip")

    def _validate_zip_file(self, file_name, tool):
        zip_location = self._get_integration_distribution_zip(tool)
        self.assertTrue(os.path.exists(zip_location), "Did not find bundled artifacts")
        with ZipFile(zip_location, 'r') as zipObj:
            listOfiles = zipObj.namelist()
            self.assertEqual(len(listOfiles), 1, "Found more entries in zip than expected")
            for elem in listOfiles:
                self.assertEqual(file_name, elem, "Did not find expected entry")

    def test_verify_tavern(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        target_url = "foo"
        # Configure default properties
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, target_url)
        file_name = "test.tavern.yaml"
        test_file = self._configure_mock_test_files(file_name, "tavern")
        pybuilder_integration.tasks.verify_tavern(project=self.project, logger=mock_logger, reactor=reactor)
        self._assert_called_tavern_execution(f"{self.tmpDir}/src/integrationtest/tavern", target_url, verify_execute)
        self._validate_zip_file(file_name, "tavern")

    def _assert_called_tavern_execution(self, test_dir, target_url, verify_execute):
        output_file, run_name = pybuilder_integration.tasks.get_test_report_file(project=self.project,
                                                                                 test_dir=test_dir)
        verify_execute.assert_any_call(
            [
                f"TARGET={target_url} pytest",
                "--junit-xml",
                f"{output_file}"
            ],
            f"{self.tmpDir}/target/reports/integration/{run_name}-tavern.txt",
            cwd=test_dir)

    def _assert_protractor_run(self, test_directory, target_url, verify_execute):
        verify_execute.assert_any_call([f"{self.tmpDir}/node_modules/protractor/bin/protractor",
                                        f"--baseUrl={target_url}"],
                                       f"{self.tmpDir}/target/logs/integration/protractor_run",
                                       cwd=test_directory)

    def test_verify_environment(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        target_url = "foo"
        # Configure default properties
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, target_url)
        self.project.set_property(pybuilder_integration.properties.ENVIRONMENT, "dev")
        distribution_directory = directory_utility.get_working_distribution_directory(self.project)
        protractor_test_dir, tavern_test_dir = self._configure_mock_tests(distribution_directory)
        pybuilder_integration.tasks.verify_environment(project=self.project, logger=mock_logger, reactor=reactor)
        self._assert_s3_transfer(source=directory_utility.prepare_dist_directory(self.project),
                                 destination=artifact_manager.get_versioned_artifact_destination(logger=mock_logger,
                                                                                                 project=self.project),
                                 verify_execute=verify_execute)
        self._assert_s3_transfer(source=directory_utility.prepare_dist_directory(self.project),
                                 destination=artifact_manager.get_latest_artifact_destination(logger=mock_logger,
                                                                                              project=self.project),
                                 verify_execute=verify_execute)
        self._assert_s3_transfer(destination=directory_utility.get_latest_zipped_distribution_directory(self.project),
                                 source=artifact_manager.get_latest_artifact_destination(logger=mock_logger,
                                                                                         project=self.project),
                                 verify_execute=verify_execute)
        self._assert_called_tavern_execution(os.path.dirname(tavern_test_dir), target_url, verify_execute)
        self._assert_protractor_run(os.path.dirname(protractor_test_dir), target_url, verify_execute)
