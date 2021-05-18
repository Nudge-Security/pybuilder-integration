from pybuilder.core import task, Project, Logger
from pybuilder.reactor import Reactor

import pybuilder_integration.tasks
from pybuilder_integration.properties import *


@task(description="Runs integration tests against a CI/Prod environment."
                  "1. Run current build integration tests found in ${dir_dist}"
                  f"2. Run integration tests found in 'LATEST-{ENVIRONMENT}' managed by ${ARTIFACT_MANAGER}"
                  f"3. Promote current build integration tests to 'LATEST-{ENVIRONMENT}' (disable with ${PROMOTE_ARTIFACT})"
                  f"${INTEGRATION_TARGET_URL} - (required) Full URL target for tests"
                  f"${ENVIRONMENT} - (required) Environment that is being tested (ci/prod)"
                  f"${PROMOTE_ARTIFACT} - Promote integration tests to LATEST-${ENVIRONMENT} (default TRUE)"
      )
def verify_environment(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_environment(project, logger, reactor)


@task(description="Run integration tests using a protractor spec. Requires NPM installed."
                  f"{INTEGRATION_TARGET_URL} - (required) Full URL target for protractor tests"
                  f"{PROTRACTOR_TEST_DIR} - directory for test specification (src/integrationtest/protractor)"
      )
def verify_protractor(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_protractor(project, logger, reactor)


@task(description="Run integration tests using a RAML spec."
                  f"{RAML_TEST_DIR} - directory containing RAML specifications ({DEFAULT_RAML_TEST_DIR})"
                  f"{RAML_MODULE_GLOB} - search pattern for RAML tests ({DEFAULT_RAML_GLOB})")
def verify_raml(project: Project, logger: Logger, reactor: Reactor):
    tasks.verify_raml(project, logger, reactor)
