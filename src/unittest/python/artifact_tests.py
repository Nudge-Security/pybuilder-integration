import os

from pybuilder.errors import BuildFailedException

from parent_test_case import ParentTestCase
from pybuilder_integration import directory_utility, properties
from pybuilder_integration.artifact_manager import S3ArtifactManager, get_artifact_manager, get_project_metadata, \
    _unzip_downloaded_artifacts

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class ArtifactManagerTestCase(ParentTestCase):

    def test_name_processing(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        expected_app_group = 'apples'
        expected_app_name = 'oranges'
        expected_role = 'bananas'
        # validate a well formed name in expected format
        self.project.name = f"{expected_app_group}-{expected_app_name}-{expected_role}"
        expected_environment = 'ci'
        expected_bucket = 'foo'
        self.project.set_property(properties.ENVIRONMENT, expected_environment)
        self.project.set_property(properties.INTEGRATION_ARTIFACT_BUCKET, expected_bucket)
        self.validate_metadata_processing(expected_app_group, expected_app_name, expected_bucket, expected_environment,
                                          expected_role, mock_logger)
        # validate a well formed name in expected format
        self.project.name = f"{expected_app_group}-{expected_app_name}-{expected_role}-blarney"
        expected_role = 'bananas-blarney'
        expected_environment = 'ci'
        expected_bucket = 'foo'
        self.project.set_property(properties.ENVIRONMENT, expected_environment)
        self.project.set_property(properties.INTEGRATION_ARTIFACT_BUCKET, expected_bucket)
        self.validate_metadata_processing(expected_app_group, expected_app_name, expected_bucket, expected_environment,
                                          expected_role, mock_logger)
        # validate a name in unexpected format
        self.project.name = f"{expected_app_name}"
        self.validate_metadata_processing('Unknown', expected_app_name, expected_bucket, expected_environment,
                                          'Unknown', mock_logger)
        # validate with properties instead of name
        expected_app_group = 'apples2'
        expected_app_name = 'oranges2'
        expected_role = 'bananas2'
        self.project.set_property(properties.APPLICATION, f"{expected_app_group}-{expected_app_name}")
        self.project.set_property(properties.ROLE, expected_role)
        self.validate_metadata_processing(expected_app_group, expected_app_name, expected_bucket, expected_environment,
                                          expected_role, mock_logger)
        # validate with full properties instead of name
        expected_app_group = 'apples3'
        expected_app_name = 'oranges3'
        expected_role = 'bananas3'
        self.project.set_property(properties.APPLICATION_GROUP, expected_app_group)
        self.project.set_property(properties.APPLICATION, expected_app_name)
        self.project.set_property(properties.ROLE, expected_role)
        self.validate_metadata_processing(expected_app_group, expected_app_name, expected_bucket, expected_environment,
                                          expected_role, mock_logger)

    def validate_metadata_processing(self, expected_app_group, expected_app_name, expected_bucket, expected_environment,
                                     expected_role, mock_logger):
        artifact_manager = S3ArtifactManager()
        app_group, app_name, bucket, environment, role = get_project_metadata(logger=mock_logger,
                                                                                               project=self.project)
        self.assertEqual(app_group, expected_app_group, "Did not extract app group")
        self.assertEqual(app_name, expected_app_name, "Did not extract app")
        self.assertEqual(role, expected_role, "Did not extract role")
        self.assertEqual(bucket, expected_bucket, "Did not extract bucket")
        self.assertEqual(environment, expected_environment, "Did not extract environment")

    def test_s3_artfact_upload(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        artifact_manager = S3ArtifactManager()
        dist_directory = directory_utility.prepare_logs_directory(self.project)
        relative_path = "foo"
        artifact_manager._s3_transfer(source=dist_directory, destination=relative_path, project=self.project,
                                      reactor=reactor, logger=mock_logger)
        self._assert_aws_check(verify_mock)

        self._assert_s3_transfer(dist_directory, relative_path, verify_execute)


    def test_s3_artfact_upload_abort(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        artifact_manager = S3ArtifactManager()
        relative_path = "foo"
        self.project.set_property("abort_upload","true")
        try:
            verify_mock.reset_mock()
            artifact_manager.upload(file=relative_path, project=self.project,
                                    reactor=reactor, logger=mock_logger)
            verify_mock.assert_not_called()
        finally:
            self.project.set_property("abort_upload","false")

    def test_artifact_manager(self):
        manager = get_artifact_manager(self.project)
        self.assertIsNotNone(manager, "Failed to find manager")
        self.project.set_property(properties.ARTIFACT_MANAGER, None)
        self.assertRaises(BuildFailedException, get_artifact_manager, self.project)

    def test_artifact_packaging(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        directory = f"{self.tmpDir}/artifact_packaging_test"
        cypress_test_file_path, tavern_test_file_path = self._configure_mock_tests(directory)
        role = "foo"
        directory_utility.package_artifacts(self.project, os.path.dirname(tavern_test_file_path), "tavern", role)
        directory_utility.package_artifacts(self.project, os.path.dirname(cypress_test_file_path), "cypress", role)
        directory = f"{self.tmpDir}/artifact_dest"
        os.makedirs(directory)
        _unzip_downloaded_artifacts(directory_utility.prepare_dist_directory(self.project),
                                    directory,
                                    mock_logger)
        listdir = os.listdir(directory)
        self.assertEqual(2,len(listdir) ,"Found unexpected directories")
        for pth in listdir:
            files = os.listdir(os.path.join(directory,pth))
            self.assertEqual(1,len(files),"Found unexpected files")
            if os.path.basename(pth) == 'tavern':
                role_dir = os.listdir(os.path.join(directory,pth,files[0]))
                self.assertEqual(1,len(role_dir),"Found unexpected files")
                if os.path.basename(files[0]  ) == 'foo':
                    self.assertEqual('test.tavern.yaml',os.path.basename(role_dir[0]),"Found unexpected file")
            elif os.path.basename(pth) == 'cypress':
                role_dir = os.listdir(os.path.join(directory,pth,files[0]))
                self.assertEqual(1,len(role_dir),"Found unexpected files")
                if os.path.basename(files[0]) == 'foo':
                    self.assertEqual('test.json',os.path.basename(role_dir[0]))
            else:
                self.fail(f"Found unexpected file {files}")

    def test_artifact_repackaging(self):
        mock_logger, verify_mock, verify_execute, reactor = self.generate_mock()
        directory = f"{self.tmpDir}/artifact_packaging_test"
        protractor_test_file_path, tavern_test_file_path = self._configure_mock_tests(directory)
        directory_utility.package_artifacts(self.project, os.path.dirname(tavern_test_file_path), "tavern","foo")
        directory_utility.package_artifacts(self.project, os.path.dirname(tavern_test_file_path), "tavern","foo")
        # we didn't fail we are good!!!




