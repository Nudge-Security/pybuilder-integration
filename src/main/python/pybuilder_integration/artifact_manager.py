import os
import shutil
from typing import Dict

from pybuilder.core import Project, Logger
from pybuilder.errors import BuildFailedException
from pybuilder.reactor import Reactor

from pybuilder_integration import exec_utility
from pybuilder_integration.directory_utility import get_latest_distribution_directory, \
    get_latest_zipped_distribution_directory
from pybuilder_integration.properties import *


class ArtifactManager:
    def __init__(self, name, identifier):
        self.identifier = identifier
        self.friendly_name = name

    def upload(self, file: str, project: Project, logger: Logger, reactor: Reactor):
        pass

    def download_artifacts(self, project: Project, logger: Logger, reactor: Reactor):
        pass


class S3ArtifactManager(ArtifactManager):

    def __init__(self):
        super().__init__("AWS S3 Artifact Manager", "S3")

    def upload(self, file: str, project: Project, logger: Logger, reactor: Reactor):
        if project.get_property("abort_upload","false") != "false":
            return
        # First make sure bucket exists
        self.create_bucket(logger, project, reactor)
        relative_path = get_latest_artifact_destination(logger, project)
        self._s3_transfer(file, relative_path, project, reactor, logger, recursive=False)
        relative_path = get_versioned_artifact_destination(logger, project)
        self._s3_transfer(file, relative_path, project, reactor, logger, recursive=False)

    def download_artifacts(self, project: Project, logger: Logger, reactor: Reactor):
        # this is a noop if there is no bucket
        if not self.does_bucket_exist(logger, project, reactor):
            return
        s3_location = get_latest_artifact_destination(logger, project)
        zipped_directory = get_latest_zipped_distribution_directory(project)
        self._s3_transfer(source=s3_location,
                          destination=zipped_directory,
                          project=project,
                          logger=logger,
                          reactor=reactor)
        return _unzip_downloaded_artifacts(zipped_directory, get_latest_distribution_directory(project), logger, project)

    @staticmethod
    def _s3_transfer(source, destination, project, reactor, logger, recursive=True):
        logger.info(f"Proceeding to transfer {source} to {destination}")
        S3ArtifactManager.verify_aws_cli(reactor)
        #  aws s3 cp myDir s3://mybucket/ --recursive
        args = [
            's3',
            'cp',
            source,
            destination
        ]
        if recursive:
            args.append("--recursive")
        exec_utility.exec_command(command_name='aws',
                                  args=args,
                                  failure_message=f"Failed to transfer integration artifacts to {destination}",
                                  log_file_name='s3-artifact-transfer',
                                  project=project,
                                  reactor=reactor,
                                  logger=logger,
                                  report=False)

    @staticmethod
    def verify_aws_cli(reactor):
        reactor.pybuilder_venv.verify_can_execute(command_and_arguments=["aws", "--version"],
                                                  prerequisite="aws cli",
                                                  caller="integration_tests")

    def create_bucket(self, logger, project, reactor):
        app_group, app_name, bucket, environment, role = get_project_metadata(logger, project)
        S3ArtifactManager.verify_aws_cli(reactor)
        res = self.does_bucket_exist(logger, project, reactor)
        if res:
            return
        exec_utility.exec_command(command_name='aws',
                                  args=[
                                      's3api',
                                      'create-bucket',
                                      '--acl',
                                      'private',
                                      '--bucket',
                                      bucket
                                  ],
                                  failure_message=f"Failed to create bucket",
                                  log_file_name='s3-create-bucket',
                                  project=project,
                                  reactor=reactor,
                                  logger=logger,
                                  report=False)

    def does_bucket_exist(self, logger, project, reactor):
        app_group, app_name, bucket, environment, role = get_project_metadata(logger, project)
        return exec_utility.exec_command(command_name='aws',
                                         args=[
                                             's3api',
                                             'head-bucket',
                                             '--bucket',
                                             bucket
                                         ],
                                         failure_message=f"Failed to find bucket",
                                         log_file_name='s3-head-bucket',
                                         project=project,
                                         reactor=reactor,
                                         logger=logger,
                                         raise_exception=True,
                                         report=True)


artifact_managers: Dict[str, S3ArtifactManager] = {}
manager = S3ArtifactManager()
artifact_managers[manager.identifier] = manager


def get_artifact_manager(project: Project) -> ArtifactManager:
    manager_id = project.get_property(ARTIFACT_MANAGER, "S3")
    global artifact_managers
    manager = artifact_managers.get(manager_id)
    if not manager:
        raise BuildFailedException(f"Failed to find appropriate artifact manager for {manager_id}")
    return manager


def extract_application_role(logger, project):
    # expect a fully populated naming scheme
    app_group = project.get_property(APPLICATION_GROUP)
    app_name = project.get_property(APPLICATION)
    role = project.get_property(ROLE)
    #  if we do not have role set, assume it is all baked into the project name
    if not role:
        project_name = project.name
        if project_name.find("-") >= 0:
            split = project_name.split("-")
            if len(split) >= 3:
                app_group = split[0]
                app_name = split[1]
                if len(split) == 3:
                    role = split[2]
                else:
                    role = "-".join(split[2:])
            else:
                logger.info(
                    f"Unexpected naming format expected <Application Group>-<Application>-<Role> got {project_name}")
        else:
            app_name = project_name
            role = 'Unknown'
            logger.info(
                f"Unexpected naming format expected <Application Group>-<Application>-<Role> got {project_name}")
    if not app_group:
        if app_name and app_name.find("-") >= 0:
            # backwards compat for the simple days before app groups
            split = app_name.split("-")
            app_group = split[0]
            app_name = split[1]
        else:
            app_group = "Unknown"
    return app_group, app_name, role


def _unzip_downloaded_artifacts(dir_with_zips: str, destination: str, logger: Logger, project:Project) -> str:
    for file in os.listdir(dir_with_zips):
        # expect {tool}-{self.project.name}.zip
        if os.path.basename(file).find("tavern") >= 0:
            shutil.unpack_archive(filename=os.path.join(dir_with_zips, file), extract_dir=f"{destination}/tavern",
                                  format="zip")
        elif os.path.basename(file).find("cypress") >= 0:
            shutil.unpack_archive(filename=os.path.join(dir_with_zips, file), extract_dir=f"{destination}/cypress",
                                  format="zip")
        else:
            logger.warn(f"Unexpected file name in downloaded artifacts {file}")
    if project.get_property(CONSOLIDATE_TESTS,False):
        consolidated_folder = f"{destination}/tavern/consolidated"
        logger.debug(f"Consolidating test files into {consolidated_folder}")
        os.makedirs(consolidated_folder, exist_ok=True)
        logger.debug(f"Creating role file for log retrieval {consolidated_folder}/roles")
        open(f"{consolidated_folder}/roles", 'w').close()
        for dirn in os.listdir(f"{destination}/tavern"):
            if "consolidated" != dirn:
                logger.debug(f"Consolidating directory: {dirn}")
                shutil.copytree(f"{destination}/tavern/{dirn}", consolidated_folder, dirs_exist_ok=True)
                shutil.rmtree(f"{destination}/tavern/{dirn}")
                with open(f"{consolidated_folder}/roles", "a") as fp:
                    fp.writelines(dirn)
    return destination


def get_project_metadata(logger: Logger, project: Project):
    app_group, app_name, role = extract_application_role(logger, project)
    environment = project.get_mandatory_property(ENVIRONMENT)
    bucket = project.get_property(INTEGRATION_ARTIFACT_BUCKET, f"integration-artifacts-{app_group}-{app_name}")
    return app_group, app_name, bucket, environment, role


def get_versioned_artifact_destination(logger, project):
    app_group, app_name, bucket, environment, role = get_project_metadata(logger, project)
    return f"s3://{bucket}/{role}/{project.version}/"


def get_latest_artifact_destination(logger, project):
    app_group, app_name, bucket, environment, role = get_project_metadata(logger, project)
    return f"s3://{bucket}/LATEST-{environment}/"
