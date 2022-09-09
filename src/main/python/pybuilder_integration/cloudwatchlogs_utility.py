import boto3
from pybuilder.core import Logger


class CloudwatchLogs():

    def __init__(self, environment, application, role, logger:Logger) -> None:
        super().__init__()
        self.group_name = f"/{environment}/{application}/{role}"
        self.environment = environment
        self.application = application
        self.role = role
        self.logger = logger
        self.cwclient = None

    def _get_cloudwatch_logs_client(self):
        if not self.cwclient:
            self.cwclient = boto3.client('logs')
        return self.cwclient

    def print_latest(self):
        try:
            self.print_latest_for_group(self.group_name)
        except Exception as ex:
            self.logger.error(f"Error printing cloudwatch logs {str(ex)}")

    def print_latest_for_group(self, cloudwatchlogs_group_name):
        log_stream = self.find_latest_stream(cloudwatchlogs_group_name)
        events = self.get_events(cloudwatchlogs_group_name, log_stream)
        to_print = self._process_events(events)
        #         next_token = events.get('nextForwardToken', None)
        #         previous_token = None
        # while previous_token != next_token:
        #     events = self.get_events(cloudwatchlogs_group_name, log_stream, nextToken=next_token)
        #     previous_token = next_token
        #     next_token = events.get('nextForwardToken', None)
        #     to_print.extend(self._process_events(events))

        self.logger.warn(f"Cloudwatch Logs {cloudwatchlogs_group_name}")
        for event in to_print:
            message__format = "{message}".format(**event)
            if '/health' not in message__format:
                self.logger.warn(f"{cloudwatchlogs_group_name} - {message__format}")

    def get_events(self, cloudwatchlogs_group_name, log_stream, nextToken=None):
        params = {
            "logGroupName": cloudwatchlogs_group_name,
            "logStreamName": log_stream,
            "startFromHead": False
        }
        # if nextToken:
        #     params['nextToken'] = nextToken
        return self._get_cloudwatch_logs_client().get_log_events(**params)

    def find_latest_stream(self, cloudwatchlogs_group_name):
        streams = self._get_cloudwatch_logs_client().describe_log_streams(logGroupName=cloudwatchlogs_group_name,
                                                                          descending=True,
                                                                          limit=1,
                                                                          orderBy="LastEventTime")
        return streams['logStreams'][0]['logStreamName']

    def _process_events(self, events) -> list:
        return events['events']
