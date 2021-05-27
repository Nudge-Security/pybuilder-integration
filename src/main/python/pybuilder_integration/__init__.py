from pybuilder.core import task, Project, Logger, depends, after
from pybuilder.reactor import Reactor

import pybuilder_integration.tasks
from pybuilder_integration.properties import *


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


@task(description="Run integration tests using a protractor spec. Requires NPM installed.\n"
                  f"\t{INTEGRATION_TARGET_URL} - (required) Full URL target for protractor tests\n"
                  f"\t{PROTRACTOR_TEST_DIR} - directory for test specification (src/integrationtest/protractor)\n"
      )
def verify_protractor(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_protractor(project, logger, reactor)


@task(description="Run integration tests using tavern specifications.\n"
                  f"\t{TAVERN_TEST_DIR} - directory containing tavern specifications ({DEFAULT_TAVERN_TEST_DIR})")
def verify_tavern(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_tavern(project, logger, reactor)


@task(description="Run verify_tavern and verify_protractor")
@depends("publish","verify_tavern","verify_protractor")
def verify_package():
    pass