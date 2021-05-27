import os

import pytest
from _pytest.config import ExitCode
from pybuilder.core import Project, Logger, init
from pybuilder.errors import BuildFailedException
from pybuilder.reactor import Reactor

from pybuilder_integration import exec_utility
from pybuilder_integration.artifact_manager import get_artifact_manager
from pybuilder_integration.directory_utility import prepare_dist_directory, get_working_distribution_directory, \
    package_artifacts, prepare_reports_directory
from pybuilder_integration.properties import *
from pybuilder_integration.tool_utility import install_protractor


@init
def init_test_source_directory(project):
    project.plugin_depends_on("pytest")
    project.plugin_depends_on("tavern")


def integration_artifact_push(project: Project, logger: Logger, reactor: Reactor):
    logger.info("Starting upload of integration artifacts")
    manager = get_artifact_manager(project)
    dist_directory = prepare_dist_directory(project)
    logger.info(f"Starting upload of integration artifacts to {manager.friendly_name}")
    manager.upload(dist_directory=dist_directory, project=project, logger=logger, reactor=reactor)


def verify_environment(project: Project, logger: Logger, reactor: Reactor):
    dist_directory = get_working_distribution_directory(project)
    logger.info(f"Preparing to run tests found in {dist_directory}")
    _run_tests_in_directory(dist_directory, logger, project, reactor)
    artifact_manager = get_artifact_manager(project=project)
    latest_directory = artifact_manager.download_artifacts(project=project, logger=logger, reactor=reactor)
    _run_tests_in_directory(latest_directory, logger, project, reactor)
    if project.get_property(PROMOTE_ARTIFACT, "TRUE") == "TRUE":
        integration_artifact_push(project=project, logger=logger, reactor=reactor)


def _run_tests_in_directory(dist_directory, logger, project, reactor):
    protractor_test_path = f"{dist_directory}/protractor"
    if os.path.exists(protractor_test_path):
        logger.info(f"Found protractor tests - starting run")
        _run_protractor_tests_in_directory(work_dir=protractor_test_path,
                                           logger=logger,
                                           project=project,
                                           reactor=reactor)
    tavern_test_path = f"{dist_directory}/tavern"
    if os.path.exists(tavern_test_path):
        logger.info(f"Found tavern tests - starting run")
        _run_tavern_tests_in_dir(test_dir=tavern_test_path,
                                 logger=logger,
                                 project=project,
                                 reactor=reactor)


def verify_protractor(project: Project, logger: Logger, reactor: Reactor):
    project.set_property_if_unset(PROTRACTOR_TEST_DIR, "src/integrationtest/protractor")
    # Get directories with test and protractor executable
    work_dir = project.expand_path(f"${PROTRACTOR_TEST_DIR}")
    if _run_protractor_tests_in_directory(work_dir=work_dir, logger=logger, project=project,
                                          reactor=reactor):
        package_artifacts(project, work_dir, "protractor")


def _run_protractor_tests_in_directory(work_dir, logger, project, reactor: Reactor):
    target_url = project.get_mandatory_property(INTEGRATION_TARGET_URL)
    if not os.path.exists(work_dir):
        logger.info("Skipping protractor run: no tests")
        return False
    logger.info(f"Found {len(os.listdir(work_dir))} files in protractor test directory")
    # Validate NPM install and Install protractor
    install_protractor(project=project, logger=logger, reactor=reactor)
    executable = project.expand_path("./node_modules/protractor/bin/protractor")
    # Run the actual tests against the baseURL provided by ${integration_target}
    exec_utility.exec_command(command_name=executable, args=[f"--baseUrl={target_url}"],
                              failure_message="Failed to execute protractor tests", log_file_name='protractor_run',
                              project=project, reactor=reactor, logger=logger, working_dir=work_dir, report=False)
    return True

def verify_tavern(project: Project, logger: Logger, reactor: Reactor):
    # Set the default
    project.set_property_if_unset(TAVERN_TEST_DIR, DEFAULT_TAVERN_TEST_DIR)
    # Expand the directory to get full path
    test_dir = project.expand_path(f"${TAVERN_TEST_DIR}")
    # Run the tests in the directory
    if _run_tavern_tests_in_dir(test_dir, logger, project, reactor):
        package_artifacts(project, test_dir, "tavern")


def _run_tavern_tests_in_dir(test_dir: str, logger: Logger, project: Project, reactor: Reactor):
    logger.info("Running tavern tests: {}".format(test_dir))

    if not os.path.exists(test_dir):
        logger.info("Skipping tavern run: no tests")
        return False
    logger.info(f"Found {len(os.listdir(test_dir))} files in tavern test directory")
    # todo is this unique enough for each run?
    output_file, run_name = get_test_report_file(project, test_dir)
    args = ["--junit-xml",f"{output_file}", test_dir]
    os.environ['TARGET'] = project.get_property(INTEGRATION_TARGET_URL)
    ret = pytest.main(args)
    if ret != 0:
        raise BuildFailedException(f"Tavern tests failed see complete output here - {output_file}")
    return True


def get_test_report_file(project, test_dir):
    run_name = os.path.basename(os.path.realpath(os.path.join(test_dir, os.pardir)))
    output_file = os.path.join(prepare_reports_directory(project), f"tavern-{run_name}.out.xml")
    return output_file, run_name
