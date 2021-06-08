import os

import pytest
from pybuilder.core import Project, Logger, init
from pybuilder.errors import BuildFailedException
from pybuilder.reactor import Reactor

from pybuilder_integration import exec_utility
from pybuilder_integration.artifact_manager import get_artifact_manager
from pybuilder_integration.directory_utility import prepare_dist_directory, get_working_distribution_directory, \
    package_artifacts, prepare_reports_directory, get_local_zip_artifact_path
from pybuilder_integration.properties import *
from pybuilder_integration.tool_utility import install_cypress




def integration_artifact_push(project: Project, logger: Logger, reactor: Reactor):
    logger.info("Starting upload of integration artifacts")
    manager = get_artifact_manager(project)
    for tool in ["tavern","cypress"]:
        artifact = get_local_zip_artifact_path(tool=tool, project=project, include_ending=True)
        logger.info(f"Starting upload of integration artifacts to {manager.friendly_name}")
        manager.upload(dist_directory=artifact, project=project, logger=logger, reactor=reactor)


def verify_environment(project: Project, logger: Logger, reactor: Reactor):
    dist_directory = project.get_property(WORKING_TEST_DIR, get_working_distribution_directory(project))
    logger.info(f"Preparing to run tests found in: {dist_directory}")
    _run_tests_in_directory(dist_directory, logger, project, reactor)
    artifact_manager = get_artifact_manager(project=project)
    latest_directory = artifact_manager.download_artifacts(project=project, logger=logger, reactor=reactor)
    _run_tests_in_directory(latest_directory, logger, project, reactor)
    if project.get_property(PROMOTE_ARTIFACT, True) == True:
        integration_artifact_push(project=project, logger=logger, reactor=reactor)


def _run_tests_in_directory(dist_directory, logger, project, reactor):
    cypress_test_path = f"{dist_directory}/cypress"
    if os.path.exists(cypress_test_path):
        logger.info(f"Found cypress tests - starting run")
        _run_cypress_tests_in_directory(work_dir=cypress_test_path,
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


def verify_cypress(project: Project, logger: Logger, reactor: Reactor):
    project.set_property_if_unset(CYPRESS_TEST_DIR, "src/integrationtest/cypress")
    # Get directories with test and cypress executable
    work_dir = project.expand_path(f"${CYPRESS_TEST_DIR}")
    if _run_cypress_tests_in_directory(work_dir=work_dir, logger=logger, project=project,
                                       reactor=reactor):
        package_artifacts(project, work_dir, "cypress")


def _run_cypress_tests_in_directory(work_dir, logger, project, reactor: Reactor):
    target_url = project.get_mandatory_property(INTEGRATION_TARGET_URL)
    environment = project.get_mandatory_property(ENVIRONMENT)
    if not os.path.exists(work_dir):
        logger.info("Skipping cypress run: no tests")
        return False
    logger.info(f"Found {len(os.listdir(work_dir))} files in cypress test directory")
    # Validate NPM install and Install cypress
    install_cypress(project=project, logger=logger, reactor=reactor)
    executable = project.expand_path("./node_modules/cypress/bin/cypress")
    # Run the actual tests against the baseURL provided by ${integration_target}
    args = ["run","--env", f"host={target_url}"]
    config_file_path = f'{environment}-config.json'
    if os.path.exists(os.path.join(work_dir,config_file_path)):
        args.append("--config-file")
        args.append(config_file_path)
    logger.info(f"Running cypress on host: {target_url}")
    exec_utility.exec_command(command_name=executable, args=args,
                              failure_message="Failed to execute cypress tests", log_file_name='cypress_run.log',
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
    from sys import path as syspath
    syspath.insert(0, test_dir)
    extra_args = [project.expand(prop) for prop in project.get_property(TAVERN_ADDITIONAL_ARGS,[])]
    args = ["--junit-xml", f"{output_file}", test_dir] + extra_args
    if project.get_property("verbose"):
        args.append("-s")
        args.append("-v")
    os.environ['TARGET'] = project.get_property(INTEGRATION_TARGET_URL)
    ret = pytest.main(args)
    if ret != 0:
        raise BuildFailedException(f"Tavern tests failed see complete output here - {output_file}")
    return True


def get_test_report_file(project, test_dir):
    run_name = os.path.basename(os.path.realpath(os.path.join(test_dir, os.pardir)))
    output_file = os.path.join(prepare_reports_directory(project), f"tavern-{run_name}.out.xml")
    return output_file, run_name
