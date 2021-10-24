from pybuilder.core import Logger, Project
from pybuilder.reactor import Reactor

from pybuilder_integration.exec_utility import exec_command


def install_cypress(logger: Logger, project: Project, reactor: Reactor, work_dir):
    _verify_npm(reactor)
    logger.info(f"Ensuring cypress is installed")
    exec_command('npm', ['install', "cypress"], f'Failed to install cypress - required for integration tests',
                 f'{"cypress"}_npm_install.log', project, reactor, logger, report=False, working_dir=work_dir)


def _verify_npm(reactor):
    reactor.pybuilder_venv.verify_can_execute(
        command_and_arguments=["npm", "--version"], prerequisite="npm", caller="integration_tests")


def install_npm_dependencies(work_dir, project, logger, reactor):
    _verify_npm(reactor)
    exec_command('npm', ['install'], f'Failed to install package.json - required for integration tests',
             f'package_json_npm_install.log', project, reactor, logger, report=False, working_dir=work_dir)


