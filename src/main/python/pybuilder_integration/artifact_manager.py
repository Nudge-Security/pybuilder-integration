import os
import shutil
from typing import Dict

from pybuilder.core import Project, Logger
from pybuilder.errors import BuildFailedException
from pybuilder.reactor import Reactor

from pybuilder_integration import exec_utility
from pybuilder_integration.directory_utility import get_latest_distribution_directory, \
    get_latest_zipped_distribution_directory
from pybuilder_integration.properties import INTEGRATION_ARTIFACT_BUCKET, ENVIRONMENT, ROLE, APPLICATION, \
    APPLICATION_GROUP, ARTIFACT_MANAGER


class ArtifactManager:
    def __init__(self, name, identifier):
        self.identifier = identifier
        self.friendly_name = name

    def upload(self, dist_directory: str, project: Project, logger: Logger, reactor: Reactor):
        pass

    def download_artifacts(self, project: Project, logger: Logger, reactor: Reactor):
        pass



class S3ArtifactManager(ArtifactManager):

    def __init__(self):
        super().__init__("AWS S3 Artifact Manager", "S3")

    def upload(self, dist_directory: str, project: Project, logger: Logger, reactor: Reactor):
        relative_path = get_latest_artifact_destination(logger, project)
        self._s3_transfer(dist_directory, relative_path, project, reactor, logger)
        relative_path = get_versioned_artifact_destination(logger, project)
        self._s3_transfer(dist_directory, relative_path, project, reactor, logger)

    def download_artifacts(self, project: Project, logger: Logger, reactor: Reactor):
        s3_location = get_latest_artifact_destination(logger, project)
        zipped_directory = get_latest_zipped_distribution_directory(project)
        self._s3_transfer(source=s3_location,
                          destination=zipped_directory,
                          project=project,
                          logger=logger,
                          reactor=reactor)
        return _unzip_downloaded_artifacts(zipped_directory, get_latest_distribution_directory(project), logger)

    @staticmethod
    def _s3_transfer(source, destination, project, reactor, logger):
        logger.info(f"Proceeding to upload {source} to {destination}")
        reactor.pybuilder_venv.verify_can_execute(command_and_arguments=["aws", "--version"],
                                                  prerequisite="aws cli",
                                                  caller="integration_tests")
        args = [
            's3',
            'cp',
            source,
            destination,
            "--recursive"
        ]
        #  aws s3 cp myDir s3://mybucket/ --recursive
        exec_utility.exec_command(command_name='aws',
                                  args=args,
                                  failure_message=f"Failed to transfer integration artifacts to {destination}",
                                  log_file_name='s3-artifact-transfer',
                                  project=project,
                                  reactor=reactor,
                                  logger=logger,
                                  report=False)


artifact_managers: Dict[str, S3ArtifactManager] = {}
manager = S3ArtifactManager()
artifact_managers[manager.identifier] = manager


def get_latest_artifact_destination(logger, project):
    app_group, app_name, bucket, environment, role = get_project_metadata(logger, project)
    return f"s3://{bucket}/{app_group}-{app_name}/LATEST-{environment}/"


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
            if len(split) == 3:
                app_group = split[0]
                app_name = split[1]
                role = split[2]
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


def _unzip_downloaded_artifacts(dir_with_zips: str, destination: str, logger: Logger) -> str:
    for file in os.listdir(dir_with_zips):
        # expect {tool}-{self.project.name}.zip
        if os.path.basename(file).find("raml") >= 0:
            shutil.unpack_archive(filename=os.path.join(dir_with_zips,file), extract_dir=f"{destination}/raml", format="zip")
        elif os.path.basename(file).find("protractor") >= 0:
            shutil.unpack_archive(filename=os.path.join(dir_with_zips,file), extract_dir=f"{destination}/protractor", format="zip")
        else:
            logger.warn(f"Unexpected file name in downloaded artifacts {file}")
    return destination


def get_project_metadata(logger: Logger, project: Project):
    bucket = project.get_property(INTEGRATION_ARTIFACT_BUCKET)
    environment = project.get_property(ENVIRONMENT)
    app_group, app_name, role = extract_application_role(logger, project)
    return app_group, app_name, bucket, environment, role


def get_versioned_artifact_destination(logger, project):
    app_group, app_name, bucket, environment, role = get_project_metadata(logger, project)
    return f"s3://{bucket}/{app_group}-{app_name}/{role}/{project.version}/"
