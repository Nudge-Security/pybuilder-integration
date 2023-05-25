import os

import pybuilder_integration
import pybuilder_integration.directory_utility
import pybuilder_integration.properties
import pybuilder_integration.tasks
import pybuilder_integration.tool_utility
from parent_test_case import ParentTestCase

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class DirectoryUtilityTestCase(ParentTestCase):

    def test_directory_preparation(self):
        pybuilder_integration.directory_utility.prepare_logs_directory(project=self.project)
        logs_dir = self.project.expand_path("$dir_logs")
        self.assertTrue(os.path.exists(f"{logs_dir}/integration"), "Failed to create logs directory")
        pybuilder_integration.directory_utility.prepare_reports_directory(project=self.project)
        reports_dir = self.project.expand_path("$dir_reports")
        self.assertTrue(os.path.exists(f"{reports_dir}/integration"), "Failed to create reports directory")
        pybuilder_integration.directory_utility.prepare_dist_directory(project=self.project)
        dist_dir = self.project.expand_path("$dir_dist")
        self.assertTrue(os.path.exists(f"{dist_dir}/integration"), "Failed to create dist directory")
        pybuilder_integration.directory_utility.get_latest_distribution_directory(project=self.project)
        self.assertTrue(os.path.exists(f"{dist_dir}/integration/LATEST-unit-test/"), "Failed to create dist directory")
        pybuilder_integration.directory_utility.get_latest_zipped_distribution_directory(project=self.project)
        self.assertTrue(os.path.exists(f"{dist_dir}/integration/LATEST-unit-test/zipped/"), "Failed to create dist directory")
        pybuilder_integration.directory_utility.get_working_distribution_directory(project=self.project)
        self.assertTrue(os.path.exists(f"{dist_dir}/integration/working"), "Failed to create dist directory")



