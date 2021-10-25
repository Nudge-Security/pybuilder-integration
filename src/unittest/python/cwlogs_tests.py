import os
from unittest.mock import Mock

from pybuilder.core import Logger

import pybuilder_integration
import pybuilder_integration.directory_utility
import pybuilder_integration.properties
import pybuilder_integration.tasks
import pybuilder_integration.tool_utility
from parent_test_case import ParentTestCase
from pybuilder_integration.cloudwatchlogs_utility import CloudwatchLogs

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class DummyClient:
    def get_log_events(self,logGroupName,logStreamName,startFromHead,nextToken=None):
        return {
            "events":[
                {
                    "timestamp":"fr",
                    "message":"br"
                }
            ]
        }
    def describe_log_streams(self, logGroupName, descending, limit, orderBy):
        return {
            "logStreams":[
                {
                    'logStreamName':"bar"
                }
            ]
        }

class CWTestCase(ParentTestCase):

    def test_cw(self):
        cwLogs = CloudwatchLogs('unit-test','foo','bar',Mock(Logger))
        cwLogs.cwclient = DummyClient()
        cwLogs.print_latest()
