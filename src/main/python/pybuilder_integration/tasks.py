import os

from pybuilder.core import Project, Logger, task, depends
from pybuilder.errors import BuildFailedException
from pybuilder.reactor import Reactor
from pybuilder.utils import discover_files_matching

from pybuilder_integration import exec_utility
from pybuilder_integration.artifact_manager import get_artifact_manager
from pybuilder_integration.directory_utility import prepare_dist_directory, get_working_distribution_directory, \
    package_artifacts
from pybuilder_integration.properties import *
from pybuilder_integration.tool_utility import install_protractor, install_abao


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
    raml_test_path = f"{dist_directory}/raml"
    if os.path.exists(raml_test_path):
        logger.info(f"Found raml tests - starting run")
        _run_raml_tests_in_dir(test_dir=raml_test_path,
                               logger=logger,
                               project=project,
                               reactor=reactor)

def verify_protractor(project: Project, logger: Logger, reactor: Reactor):
    project.set_property_if_unset(PROTRACTOR_TEST_DIR, "src/integrationtest/protractor")
    # Get directories with test and protractor executable
    work_dir = project.expand_path(f"${PROTRACTOR_TEST_DIR}")
    _run_protractor_tests_in_directory(work_dir=work_dir, logger=logger, project=project,
                                       reactor=reactor)
    package_artifacts(project, work_dir, "protractor")


def _run_protractor_tests_in_directory(work_dir, logger, project, reactor: Reactor):
    target_url = project.get_mandatory_property(INTEGRATION_TARGET_URL)
    # Validate NPM install and Install protractor
    install_protractor(project=project, logger=logger, reactor=reactor)
    executable = project.expand_path("./node_modules/protractor/bin/protractor")
    # Run the actual tests against the baseURL provided by ${integration_target}
    exec_utility.exec_command(command_name=executable, args=[f"--baseUrl={target_url}"],
                              failure_message="Failed to execute protractor tests", log_file_name='protractor_run',
                              project=project, reactor=reactor, logger=logger, working_dir=work_dir, report=False)


def verify_raml(project: Project, logger: Logger, reactor: Reactor):
    # Set the default
    project.set_property_if_unset(RAML_TEST_DIR, DEFAULT_RAML_TEST_DIR)
    # Expand the directory to get full path
    test_dir = project.expand_path(f"${RAML_TEST_DIR}")
    # Run the tests in the directory
    _run_raml_tests_in_dir(test_dir, logger, project, reactor)
    package_artifacts(project, test_dir, "raml")


def _run_raml_tests_in_dir(test_dir: str, logger: Logger, project: Project, reactor: Reactor):
    # Install our RAML testing tool
    install_abao(logger, project, reactor)
    # Get our testing pattern
    search_pattern = project.get_property(RAML_MODULE_GLOB, DEFAULT_RAML_GLOB)
    logger.info(f"Searching for RAML specs {search_pattern}: {test_dir}")
    # Find all teh files that match
    raml_files = discover_files_matching(test_dir, search_pattern)
    # Incrementally run each spec
    status = True
    for file in raml_files:
        run_passed = do_raml_test(file, project, logger, reactor=reactor)
        if not run_passed:
            status = False
    if not status:
        raise BuildFailedException('Failed to pass all RAML integration tests')


def do_raml_test(file: str, project: Project, logger: Logger, reactor: Reactor):
    basename = os.path.basename(file)
    logger.info("Running raml spec: {}".format(basename))
    args = [
        file,
        '--timeout',
        '100000',
        '--server',
        project.get_property(INTEGRATION_TARGET_URL),
        "--reporter",
        "xunit"
    ]
    # Determine if there is a hookfile for the spec
    hookfile = file.replace(".raml", "-hooks.js")
    if os.path.exists(hookfile):
        # and use it if it exists
        args.append(f"--hookfiles={hookfile}")
    return exec_utility.exec_command(command_name='./node_modules/abao/bin/abao',
                                     args=args,
                                     failure_message=f'Failed to execute RAML spec: {basename}',
                                     log_file_name=f"INTEGRATIONTEST-RAML-{basename}.xml",
                                     project=project,
                                     reactor=reactor,
                                     logger=logger,
                                     raise_exception=False)
