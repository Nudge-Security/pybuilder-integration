import os
import shutil

import pytest
from pybuilder.core import Project, Logger, init, RequirementsFile
from pybuilder.errors import BuildFailedException
from pybuilder.install_utils import install_dependencies
from pybuilder.reactor import Reactor

from pybuilder_integration import exec_utility, tool_utility
from pybuilder_integration.artifact_manager import get_artifact_manager
from pybuilder_integration.cloudwatchlogs_utility import  CloudwatchLogs
from pybuilder_integration.directory_utility import prepare_dist_directory, get_working_distribution_directory, \
    package_artifacts, prepare_reports_directory, get_local_zip_artifact_path, prepare_logs_directory
from pybuilder_integration.properties import *
from pybuilder_integration.tool_utility import install_cypress


def integration_artifact_push(project: Project, logger: Logger, reactor: Reactor):
    logger.info("Starting upload of integration artifacts")
    manager = get_artifact_manager(project)
    for tool in ["tavern", "cypress"]:
        artifact_file = get_local_zip_artifact_path(tool=tool, project=project, include_ending=True)
        if os.path.exists(artifact_file):
            logger.info(f"Starting upload of integration artifact: {os.path.basename(artifact_file)} to: {manager.friendly_name}")
            manager.upload(file=artifact_file, project=project, logger=logger, reactor=reactor)


def verify_environment(project: Project, logger: Logger, reactor: Reactor):
    dist_directory = project.get_property(WORKING_TEST_DIR, get_working_distribution_directory(project))
    logger.info(f"Preparing to run tests found in: {dist_directory}")
    _run_tests_in_directory(dist_directory, logger, project, reactor)
    artifact_manager = get_artifact_manager(project=project)
    latest_directory = artifact_manager.download_artifacts(project=project, logger=logger, reactor=reactor)
    _run_tests_in_directory(latest_directory, logger, project, reactor, latest=True)
    if project.get_property(PROMOTE_ARTIFACT, True):
        integration_artifact_push(project=project, logger=logger, reactor=reactor)


def _run_tests_in_directory(dist_directory, logger, project, reactor, latest=False):
    cypress_test_path = f"{dist_directory}/cypress"
    if os.path.exists(cypress_test_path):
        logger.info(f"Found cypress tests - starting run latest: {latest}")
        if latest:
            for dir in os.listdir(cypress_test_path):
                if os.path.isdir(f"{cypress_test_path}/{dir}"):
                    logger.info(f"Running {dir}")
                    _run_cypress_tests_in_directory(work_dir=f"{cypress_test_path}/{dir}",
                                                    logger=logger,
                                                    project=project,
                                                    reactor=reactor)
        else:
            _run_cypress_tests_in_directory(work_dir=cypress_test_path,
                                            logger=logger,
                                            project=project,
                                            reactor=reactor)
    tavern_test_path = f"{dist_directory}/tavern"
    if os.path.exists(tavern_test_path):
        logger.info(f"Found tavern tests - starting run latest: {latest}")
        if latest:
            for dir in os.listdir(tavern_test_path):
                if os.path.isdir(f"{tavern_test_path}/{dir}"):
                    logger.info(f"Running {dir}")
                    _run_tavern_tests_in_dir(test_dir=f"{tavern_test_path}/{dir}",
                                             logger=logger,
                                             project=project,
                                             reactor=reactor,
                                             role=os.path.basename(dir))
        else:
            _run_tavern_tests_in_dir(test_dir=f"{tavern_test_path}",
                                     logger=logger,
                                     project=project,
                                     reactor=reactor)

def verify_cypress(project: Project, logger: Logger, reactor: Reactor):
    # Get directories with test and cypress executable
    work_dir = project.expand_path(f"${CYPRESS_TEST_DIR}")
    if _run_cypress_tests_in_directory(work_dir=work_dir, logger=logger, project=project, reactor=reactor):
        package_artifacts(project, work_dir, "cypress",project.get_property(ROLE))


def _run_cypress_tests_in_directory(work_dir, logger, project, reactor: Reactor):
    target_url = project.get_mandatory_property(INTEGRATION_TARGET_URL)
    environment = project.get_mandatory_property(ENVIRONMENT)
    if not os.path.exists(work_dir):
        logger.info("Skipping cypress run: no tests")
        return False
    logger.info(f"Found {len(os.listdir(work_dir))} files in cypress test directory")
    # Validate NPM install and Install cypress
    package_json = os.path.join(work_dir, "package.json")
    if os.path.exists(package_json):
        logger.info("Found package.json installing dependencies")
        tool_utility.install_npm_dependencies(work_dir, project=project, logger=logger, reactor=reactor)
    else:
        install_cypress(logger=logger, project=project, reactor=reactor, work_dir=work_dir)
    executable = os.path.join(work_dir, "node_modules/cypress/bin/cypress")
    results_file, run_name = get_test_report_file(project=project,test_dir=work_dir,tool="cypress")
    # Run the actual tests against the baseURL provided by ${integration_target}
    args = ["run", "--config", f"baseUrl={target_url}", "--reporter-options",
            f"mochaFile={results_file}" ]
    config_file_path = f'{environment}-config.json'
    if os.path.exists(os.path.join(work_dir, config_file_path)):
        args.append("--config-file")
        args.append(config_file_path)
    logger.info(f"Running cypress on host: {target_url}")
    exec_utility.exec_command(command_name=executable, args=args,
                              failure_message="Failed to execute cypress tests", log_file_name='cypress_run.log',
                              project=project, reactor=reactor, logger=logger, working_dir=work_dir, report=False)
    # workaround but cypress output are relative to location of cypress.json so we need to collapse
    if os.path.exists(f"{work_dir}/target"):
        shutil.copytree(f"{work_dir}/target","./target",dirs_exist_ok=True)
    return True


def verify_tavern(project: Project, logger: Logger, reactor: Reactor):
    # Expand the directory to get full path
    test_dir = project.expand_path(f"${TAVERN_TEST_DIR}")
    # Run the tests in the directory
    if _run_tavern_tests_in_dir(test_dir, logger, project, reactor):
        package_artifacts(project, test_dir, "tavern",project.get_property(ROLE))


def _run_tavern_tests_in_dir(test_dir: str, logger: Logger, project: Project, reactor: Reactor, role=None):
    logger.info("Running tavern tests: {}".format(test_dir))
    if not os.path.exists(test_dir):
        logger.info("Skipping tavern run: no tests")
        return False
    logger.info(f"Found {len(os.listdir(test_dir))} files in tavern test directory")
    # todo is this unique enough for each run?
    output_file, run_name = get_test_report_file(project, test_dir)
    from sys import path as syspath
    syspath.insert(0, test_dir)
    # install any requirements that my exist
    requirements_file = os.path.join(test_dir, "requirements.txt")
    if os.path.exists(requirements_file):
        dependency = RequirementsFile(requirements_file)
        install_dependencies(logger, project, dependency, reactor.pybuilder_venv, f"{prepare_logs_directory(project)}/install_tavern_pip_dependencies.log")
    extra_args = [project.expand(prop) for prop in project.get_property(TAVERN_ADDITIONAL_ARGS, [])]
    args = ["--junit-xml", f"{output_file}", test_dir] + extra_args
    if project.get_property("verbose"):
        args.append("-s")
        args.append("-v")
    os.environ['TARGET'] = project.get_property(INTEGRATION_TARGET_URL)
    os.environ['environment'] = project.get_property(ENVIRONMENT)
    logger.info(f"Running against: {project.get_property(INTEGRATION_TARGET_URL)} ")
    ret = pytest.main(args)
    if role:
        CloudwatchLogs(project.get_property(ENVIRONMENT), project.get_property(APPLICATION), role, logger).print_latest()
    if ret != 0:
        raise BuildFailedException(f"Tavern tests failed see complete output here - {output_file}")
    return True


def get_test_report_file(project, test_dir,tool="tavern"):
    run_name = os.path.basename(os.path.realpath(os.path.join(test_dir, os.pardir)))
    output_file = os.path.join(prepare_reports_directory(project), f"{tool}-{run_name}.out.xml")
    return output_file, run_name
