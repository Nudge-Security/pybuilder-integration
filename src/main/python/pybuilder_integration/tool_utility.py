from pybuilder.core import Logger, Project
from pybuilder.reactor import Reactor

from pybuilder_integration.exec_utility import exec_command


def install_cypress(logger: Logger, project: Project, reactor: Reactor):
    _install_npm_tool(tool_name="cypress", logger=logger, project=project, reactor=reactor)


def _install_npm_tool(tool_name: str, logger: Logger, project: Project, reactor: Reactor):
    reactor.pybuilder_venv.verify_can_execute(
        command_and_arguments=["npm", "--version"], prerequisite="npm", caller="integration_tests")
    logger.info(f"Ensuring {tool_name} is installed")
    exec_command('npm', ['install', tool_name], f'Failed to install {tool_name} - required for integration tests',
                 f'{tool_name}_npm_install', project, reactor, logger,report=False)
