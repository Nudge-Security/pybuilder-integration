from pybuilder.errors import BuildFailedException
from pybuilder.pluginhelper.external_command import ExternalCommandBuilder, ExternalCommandResult
from pybuilder.utils import read_file

from pybuilder_integration.directory_utility import prepare_logs_directory, prepare_reports_directory


def exec_command(command_name,
                 args,
                 failure_message,
                 log_file_name,
                 project,
                 reactor,
                 logger,
                 working_dir=None,
                 raise_exception=True,
                 report=True,
                 env_vars=None):
    if working_dir:
        command = WorkingDirCommandBuilder(command_name=command_name,
                                           project=project,
                                           reactor=reactor,
                                           env=env_vars,
                                           cwd=working_dir)
    else:
        command = ExternalCommandBuilder(command_name=command_name,
                                         project=project,
                                         reactor=reactor)

    for arg in args:
        command.use_argument(arg)
    if report:
        directory = prepare_reports_directory(project)
    else:
        directory = prepare_logs_directory(project)
    outfile_name = f"{directory}/{log_file_name}"
    res = command.run(outfile_name)
    if res.exit_code != 0:
        if raise_exception:
            raise BuildFailedException(failure_message)
        else:
            logger.warn(failure_message)
            return False
    return True


class WorkingDirCommandBuilder(ExternalCommandBuilder):

    def __init__(self, command_name, project, cwd, reactor, env=None):
        super(WorkingDirCommandBuilder, self).__init__(command_name, project, reactor)
        self.env = env if env else {}
        self.cwd = cwd

    def run(self, outfile_name):
        error_file_name = "{0}.err".format(outfile_name)
        return_code = self._env.execute_command(self.parts, outfile_name, env=self.env, cwd=self.cwd)
        error_file_lines = read_file(error_file_name)
        outfile_lines = read_file(outfile_name)

        return ExternalCommandResult(return_code,
                                     outfile_name, outfile_lines,
                                     error_file_name, error_file_lines)
