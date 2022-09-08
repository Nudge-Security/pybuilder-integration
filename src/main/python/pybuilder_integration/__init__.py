import os

from pybuilder.core import task, Project, Logger, depends, after, init
from pybuilder.reactor import Reactor

import pybuilder_integration.tasks
from pybuilder_integration.properties import *


@init
def init_plugin(project):
    project.set_property("tavern_addition_args", [])
    project.set_property_if_unset(CYPRESS_TEST_DIR, "src/integrationtest/cypress")
    os_default = os.environ.get(INTEGRATION_ARTIFACT_BUCKET,None)
    if os_default:
        project.set_property_if_unset(INTEGRATION_ARTIFACT_BUCKET, os_default)
    project.set_property_if_unset(TAVERN_TEST_DIR, DEFAULT_TAVERN_TEST_DIR)
    project.plugin_depends_on("pytest")
    project.build_depends_on('pytest-xdist')
    project.plugin_depends_on("tavern")


@task(description="Runs integration tests against a CI/Prod environment."
                  "\t1. Run current build integration tests found in ${dir_dist}\n"
                  f"\t2. Run integration tests found in 'LATEST-{ENVIRONMENT}' managed by ${ARTIFACT_MANAGER}\n"
                  f"\t3. Promote current build integration tests to 'LATEST-{ENVIRONMENT}' (disable with ${PROMOTE_ARTIFACT})\n"
                  f"\t${INTEGRATION_TARGET_URL} - (required) Full URL target for tests\n"
                  f"\t${ENVIRONMENT} - (required) Environment that is being tested (ci/prod)\n"
                  f"\t${PROMOTE_ARTIFACT} - Promote integration tests to LATEST-${ENVIRONMENT} (default TRUE)\n"
      )
def verify_environment(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_environment(project, logger, reactor)


@task(description="Run integration tests using a cypress spec. Requires NPM installed.\n"
                  f"\t{INTEGRATION_TARGET_URL} - (required) Full URL target for cypress tests\n"
                  f"\t{CYPRESS_TEST_DIR} - directory for test specification (src/integrationtest/cypress)\n"
      )
def verify_cypress(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_cypress(project, logger, reactor)


@task(description="Run integration tests using tavern specifications.\n"
                  f"\t{TAVERN_TEST_DIR} - directory containing tavern specifications ({DEFAULT_TAVERN_TEST_DIR})")
def verify_tavern(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_tavern(project, logger, reactor)


@task(description="Run verify_tavern and verify_cypress")
@depends("publish", "verify_tavern", "verify_cypress")
def verify_package():
    pass


@task(description="Package artifacts for publishing in integration tests")
def package_artifacts(project: Project):
    package_tavern_artifacts(project)
    package_cypress_artifacts(project)


@task(description="Package tavern artifacts for publishing in integration tests")
def package_tavern_artifacts(project: Project):
    test_dir = project.expand_path(f"${TAVERN_TEST_DIR}")
    tasks.package_artifacts(project, test_dir, "tavern", project.get_property(ROLE))


@task(description="Package cypress artifacts for publishing in integration tests")
def package_cypress_artifacts(project: Project):
    test_dir = project.expand_path(f"${CYPRESS_TEST_DIR}")
    tasks.package_artifacts(project, test_dir, "cypress",project.get_property(ROLE))
