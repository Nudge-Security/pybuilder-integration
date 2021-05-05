import os

from pybuilder.core import depends, task, Project, Logger
from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder, ExternalCommandResult
from pybuilder.reactor import Reactor
from pybuilder.utils import discover_files_matching, read_file, execute_command

RAML_MODULE_GLOB = 'raml_module_glob'
PROTRACTOR_TEST_DIR = "protractor_test_dir"
INTEGRATION_TARGET_URL = "integration_target_url"
RAML_TEST_DIR = "raml_test_dir"
DEFAULT_RAML_GLOB = "*.raml"
DEFAULT_RAML_TEST_DIR = "src/integrationtest/raml"


@task(description="Run integration tests")
@depends("verify_raml", "verify_protractor")
def verify(project, logger):
    # The @depends makes pyb run the other two tasks first so this is not really a noop
    pass


@task(description="Run integration tests using a protractor spec. Requires NPM installed."
                  f"{INTEGRATION_TARGET_URL} - (required) Full URL target for protractor tests"
                  f"{PROTRACTOR_TEST_DIR} - directory for test specification (src/integrationtest/protractor)"
      )
def verify_protractor(project: Project, logger: Logger, reactor: Reactor):
    project.set_property_if_unset(PROTRACTOR_TEST_DIR, "src/integrationtest/protractor")
    target_url = project.get_mandatory_property(INTEGRATION_TARGET_URL)
    # Get directories with test and protractor executable
    work_dir = project.expand_path(f"${PROTRACTOR_TEST_DIR}")
    _run_protractor_tests_in_directory(target_url=target_url, work_dir=work_dir, logger=logger, project=project,
                                       reactor=reactor)


def _run_protractor_tests_in_directory(target_url, work_dir, logger, project, reactor: Reactor):
    # Validate NPM install and Install protractor
    install_protractor(project=project, logger=logger, reactor=reactor)
    executable = project.expand_path("./node_modules/protractor/bin/protractor")
    # Run the actual tests against the baseURL provided by ${integration_target}
    command = WorkingDirCommandBuilder(executable, project, work_dir, reactor)
    command.use_argument("--baseUrl={}").formatted_with(target_url)
    res = command.run("{}/{}".format(prepare_logs_directory(project), 'protractor_run'))
    if res.exit_code != 0:
        raise BuildFailedException('Failed to execute protractor tests')


def install_protractor(logger: Logger, project: Project, reactor: Reactor):
    _install_npm_tool(tool_name="protractor", logger=logger, project=project, reactor=reactor)


def install_abao(logger: Logger, project: Project, reactor: Reactor):
    _install_npm_tool(tool_name="abao", logger=logger, project=project, reactor=reactor)


def _install_npm_tool(tool_name: str, logger: Logger, project: Project, reactor: Reactor):
    reactor.pybuilder_venv.verify_can_execute(
        command_and_arguments=["npm", "--version"], prerequisite="npm", caller="integration_tests")
    logger.info(f"Ensuring {tool_name} is installed")
    command = ExternalCommandBuilder('npm', project=project, reactor=reactor)
    command.use_argument('install')
    command.use_argument(tool_name)
    res = command.run("{}/{}".format(prepare_logs_directory(project), f'{tool_name}_npm_install'))
    if res.exit_code != 0:
        raise BuildFailedException(f'Failed to install {tool_name} - required for integration tests')


class WorkingDirCommandBuilder(ExternalCommandBuilder):

    def __init__(self, command_name, project, cwd, reactor):
        super(WorkingDirCommandBuilder, self).__init__(command_name, project, reactor)
        self.cwd = cwd

    def run(self, outfile_name):
        error_file_name = "{0}.err".format(outfile_name)
        return_code = self._env.execute_command(self.parts, outfile_name, cwd=self.cwd)
        error_file_lines = read_file(error_file_name)
        outfile_lines = read_file(outfile_name)

        return ExternalCommandResult(return_code,
                                     outfile_name, outfile_lines,
                                     error_file_name, error_file_lines)


@task(description="Run integration tests using a RAML spec."
                  f"{RAML_TEST_DIR} - directory containing RAML specifications ({DEFAULT_RAML_TEST_DIR})"
                  f"{RAML_MODULE_GLOB} - search pattern for RAML tests ({DEFAULT_RAML_GLOB})")
def verify_raml(project: Project, logger: Logger, reactor: Reactor):
    # Set the default
    project.set_property_if_unset(RAML_TEST_DIR, DEFAULT_RAML_TEST_DIR)
    # Expand the directory to get full path
    test_dir = project.expand_path(f"${RAML_TEST_DIR}")
    # Run the tests in the directory
    _run_raml_tests_in_dir(test_dir, logger, project,reactor)


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
        run_passed = do_raml_test(file, project, logger,reactor=reactor)
        if not run_passed:
            status = False
    if not status:
        raise BuildFailedException('Failed to pass all RAML integration tests')


def do_raml_test(file: str, project: Project, logger: Logger, reactor:Reactor):
    basename = os.path.basename(file)
    logger.info("Running raml spec: {}".format(basename))
    command = ExternalCommandBuilder('./node_modules/abao/bin/abao', project,reactor=reactor)
    command.use_argument('{}').formatted_with(file)
    command.use_argument('--timeout')
    command.use_argument('100000')
    command.use_argument('--server')
    command.use_argument('{}').formatted_with_property(INTEGRATION_TARGET_URL)
    command.use_argument('--reporter')
    command.use_argument('xunit')
    # Determine if there is a hookfile for the spec
    hookfile = file.replace(".raml", "-hooks.js")
    if os.path.exists(hookfile):
        # and use it if it exists
        command.use_argument("--hookfiles={}").formatted_with(hookfile)
    res = command.run(
        "{}/{}".format(prepare_reports_directory(project), "INTEGRATIONTEST-RAML-{}.xml".format(basename)))
    if res.exit_code > 0:
        logger.warn('Failed to execute RAML spec: {}'.format(basename))
        return False
    else:
        return True


def prepare_reports_directory(project):
    return prepare_directory("$dir_reports", project)


def prepare_logs_directory(project):
    return prepare_directory("$dir_logs", project)


def prepare_directory(dir_variable, project):
    package__format = "{}/integration".format(dir_variable)
    reports_dir = project.expand_path(package__format)
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    return reports_dir
