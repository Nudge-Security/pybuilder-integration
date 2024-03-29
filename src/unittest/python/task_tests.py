import os
from zipfile import ZipFile

from pybuilder.errors import BuildFailedException

import parent_test_case
import pybuilder_integration
import pybuilder_integration.directory_utility
import pybuilder_integration.properties
import pybuilder_integration.tasks
import pybuilder_integration.tool_utility
from parent_test_case import ParentTestCase
from pybuilder_integration import directory_utility, artifact_manager, exec_utility, properties

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class TaskTestCase(ParentTestCase):

    def test_verify_cypress(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        target_url = "foo"
        file_name = "test.json"
        full_path = self._configure_mock_test_files(file_name, "cypress")
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, target_url)
        pybuilder_integration.tasks.verify_cypress(project=self.project,
                                                   logger=mock_logger,
                                                   reactor=reactor)
        self._assert_cypress_run(f"{self.tmpDir}/src/integrationtest/cypress", target_url, verify_execute)
        self._validate_zip_file(file_name, "cypress")
        test_dir = os.path.realpath(os.path.join(full_path, os.pardir))
        config_file = "unit-test-config.json"
        with open(os.path.join(test_dir, config_file), "w") as fp:
            pass  # touch
        pybuilder_integration.tasks.verify_cypress(project=self.project,
                                                   logger=mock_logger,
                                                   reactor=reactor)
        self._assert_cypress_run(f"{self.tmpDir}/src/integrationtest/cypress", target_url, verify_execute,
                                 config_file=True)

    def _get_integration_distribution_zip(self, tool):
        return self.project.expand_path(
            f"$dir_dist/integration/{tool}-{self.project.name}.zip")

    def _validate_zip_file(self, file_name, tool):
        zip_location = self._get_integration_distribution_zip(tool)
        self.assertTrue(os.path.exists(zip_location), "Did not find bundled artifacts")
        expected = ["None/",f"None/{file_name}"]
        with ZipFile(zip_location, 'r') as zipObj:
            listOfiles = zipObj.namelist()
            self.assertEqual(len(listOfiles), len(expected), "Found more entries in zip than expected")
            self.assertEqual(listOfiles, expected, "Did not find expected entry")

    def test_exec_fail(self):
        try:
            parent_test_case.fail = True
            mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
            self.assertRaises(BuildFailedException, exec_utility.exec_command,
                              **{"command_name": "foo", "args": [], "failure_message": "Failed", "log_file_name": "foo",
                                 "project": self.project, "reactor": reactor, "logger": mock_logger})
        finally:
            parent_test_case.fail = False

    def test_verify_no_files(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        before = verify_execute.call_count
        before_pytest = self.pytest_main_mock.call_count
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, "foo")

        pybuilder_integration.tasks._run_tavern_tests_in_dir(test_dir=os.path.join(self.tmpDir, "fake"),
                                                             logger=mock_logger, project=self.project, reactor=reactor)
        pybuilder_integration.tasks._run_cypress_tests_in_directory(work_dir=os.path.join(self.tmpDir, "fake"),
                                                                    logger=mock_logger, project=self.project,
                                                                    reactor=reactor)
        self.assertEqual(before, verify_execute.call_count, "Got unexpected execution")
        self.assertEqual(before_pytest, self.pytest_main_mock.call_count, "Got unexpected execution for tavern")

    def test_verify_tavern(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        pybuilder_integration.init_plugin(self.project)
        target_url = "foo"
        # Configure default properties
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, target_url)
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_PUBLIC_TARGET_URL, target_url)
        file_name = "test.tavern.yaml"
        self._configure_mock_test_files(file_name, "tavern")
        pybuilder_integration.tasks.verify_tavern(project=self.project, logger=mock_logger, reactor=reactor)
        self._assert_called_tavern_execution(f"{self.tmpDir}/src/integrationtest/tavern", target_url, verify_execute)
        self._validate_zip_file(file_name, "tavern")

    def _assert_called_tavern_execution(self, test_dir, target_url, verify_execute):
        output_file, run_name = pybuilder_integration.tasks.get_test_report_file(project=self.project,
                                                                                 test_dir=test_dir)
        self.pytest_main_mock.assert_any_call(
            [
                "--junit-xml",
                f"{output_file}",
                f"{test_dir}"
            ])

    def _assert_cypress_run(self, test_directory, target_url, verify_execute, config_file=False,env={}):
        results_file, run_name = pybuilder_integration.tasks.get_test_report_file(project=self.project,
                                                                                 test_dir=test_directory,
                                                                                 tool="cypress")
        test_report_folder = directory_utility.prepare_reports_directory(project=self.project)
        args = [f"{test_directory}/node_modules/cypress/bin/cypress","run",
                f"--config",
                f"baseUrl={target_url},"
                f"videosFolder={test_report_folder}/videos,"
                f"screenshotsFolder={test_report_folder}/screenshots",
                "--reporter-options",
                f"mochaFile={results_file}", "--record"]
        if config_file:
            environment = self.project.get_mandatory_property(properties.ENVIRONMENT)
            args.append("--config-file")
            args.append(f'{environment}-config.json')
        verify_execute.assert_any_call(args,
                                       f"{self.tmpDir}/target/logs/integration/cypress_run.log",
                                       cwd=test_directory,
                                       env=env)

    def test_verify_environment(self):
        # create mocks
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        target_url = "foo"
        # Configure default properties
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_TARGET_URL, target_url)
        self.project.set_property(pybuilder_integration.properties.INTEGRATION_PUBLIC_TARGET_URL, target_url)
        self.project.set_property(pybuilder_integration.properties.ENVIRONMENT, "dev")
        env_vars = {"dev": "foo"}
        self.project.set_property(pybuilder_integration.properties.ENVIRONMENT_VARIABLES, env_vars)
        # mock working tests
        distribution_directory = directory_utility.get_working_distribution_directory(self.project)
        cypress_test_dir, tavern_test_dir = self._configure_mock_tests(distribution_directory)
        # mock downloaded tests
        latest_dir = directory_utility.get_latest_distribution_directory(self.project)
        role = "foo"
        cypress_latest_test_dir, tavern_latest_test_dir = self._configure_mock_tests(latest_dir,role=role)
        # mock bundled integration artifacts for tavern not cypress
        zip_artifact_path = directory_utility.get_local_zip_artifact_path(tool='tavern', project=self.project,
                                                                          include_ending=True)
        with open(zip_artifact_path,'w+') as fp:
            pass #touch

        # Run actual task
        pybuilder_integration.tasks.verify_environment(project=self.project, logger=mock_logger, reactor=reactor)
        # Run cypress & tavern in local working directory
        self._assert_called_tavern_execution(os.path.dirname(tavern_test_dir), target_url, verify_execute)
        self._assert_cypress_run(os.path.dirname(cypress_test_dir), target_url, verify_execute,env=env_vars)
        # download latest
        self._assert_s3_transfer(destination=directory_utility.get_latest_zipped_distribution_directory(self.project),
                                 source=artifact_manager.get_latest_artifact_destination(logger=mock_logger,
                                                                                         project=self.project),
                                 verify_execute=verify_execute, recursive=True)
        # Run against latest
        self._assert_called_tavern_execution(os.path.dirname(tavern_latest_test_dir), target_url, verify_execute)
        self._assert_cypress_run(os.path.dirname(cypress_latest_test_dir), target_url, verify_execute, env=env_vars)
        # Promote local tavern archive to latest & upload local archive to versioned dir - cypress does not exist
        zip_artifact_path = directory_utility.get_local_zip_artifact_path(tool="tavern", project=self.project,
                                                                          include_ending=True)
        self._assert_s3_transfer(source=zip_artifact_path,
                                 destination=artifact_manager.get_versioned_artifact_destination(logger=mock_logger,
                                                                                                 project=self.project),
                                 verify_execute=verify_execute, recursive=False)
        self._assert_s3_transfer(source=zip_artifact_path,
                                     destination=artifact_manager.get_latest_artifact_destination(logger=mock_logger,
                                                                                                  project=self.project),
                                     verify_execute=verify_execute, recursive=False)

