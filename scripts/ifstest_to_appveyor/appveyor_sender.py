import sys
from threading import Thread
import time
from enum import Enum
import re
from pprint import pprint

import requests

class AppVeyorTestOutcome(Enum):
    None_ = 'None'
    Running = 'Running'
    Passed = 'Passed'
    Failed = 'Failed'
    Ignored = 'Ignored'
    Skipped = 'Skipped'
    Inconclusive = 'Inconclusive'
    NotFound = 'NotFound'
    Cancelled = 'Cancelled'
    NotRunnable = 'NotRunnable'

def timedelta_to_milliseconds(td):
    return td.days * 1000 * 3600 * 24 + td.seconds * 1000 + td.microseconds / 1000

class AppVeyorSender():
    POLL_TIME_SECONDS = 0.5

    def __init__(self, test_case_queue, prefix=None, build_worker_api_url=None):
        self.consumer_thread = Thread(target=self.consumer_loop, name=f"{self}-ConsumerThread")
        self.queue = test_case_queue
        self.prefix = prefix or ''
        self.build_worker_api_url = build_worker_api_url
        self.finished = False

    def consumer_loop(self):
        while not self.finished:
            try:
                tests_to_send = self.__get_bulk_of_tests_from_queue()
                print("Got", len(tests_to_send), "from queue")
                if tests_to_send[-1].get('IsFinished'):
                    print("Got finished", file=sys.stderr)
                    self.finished = True
                    tests_to_send = tests_to_send[:-1]

                appveyor_data = [self.__convert_ifstest_data_to_appveyor(t) for t in tests_to_send]
                if self.build_worker_api_url:
                    response = requests.post(self.build_worker_api_url + 'api/tests/batch', json=appveyor_data)
                    response.raise_for_status()
                else:
                    pprint(appveyor_data)
            except:
                print("exception", file=sys.stderr)
        print("finsihed consumer loop", len(self.queue))

    def __get_bulk_of_tests_from_queue(self):
        tests_to_send = []
        while True:
            try:
                test = self.queue.popleft()
                tests_to_send.append(test)
            except IndexError:
                time.sleep(self.POLL_TIME_SECONDS)
                if tests_to_send:
                    break
        return tests_to_send


    def __convert_ifstest_data_to_appveyor(self, test):
        stderr_text = ''
        if 'ExpectedNtStatus' in test and 'LastNtStatus' in test:
            stderr_text = f"ExpectedNtStatus was {test['ExpectedNtStatus']}, but got LastNtStatus {test['LastNtStatus']}"

        duration = test['EndTime'] - test['StartTime']
        duration_milliseconds = timedelta_to_milliseconds(duration)

        stdout = '\n'.join([f"{k:<16}: {v}" for (k, v) in test.items() if k not in ('StartTime', 'EndTime')])
        # first three required, rest optional
        appveyor_test = {
            'testName': test.get('Test', '<no-name>'),
            'testFramework': 'IFSTest',
            'fileName': self.prefix + test.get('Group', '<no-group>'),
            'outcome': self.__convert_ifstest_status_to_appveyor(test.get('Status')).value,
            'durationMilliseconds': duration_milliseconds,
            'ErrorMessage': test.get('Description'),
            # 'ErrorStackTrace': '',
            'StdOut': stdout,
            'StdErr': stderr_text,
        }
        return appveyor_test

    # we can probably use the 8 most significant bits to determine the mapping, eg 0xC0000000 => failed
    # Given that there are some exceptions, we we will stay safe and look at each status on a case-by-case basis
    IFSTEST_TO_APPVEYOR_STATUS = {
        (0x00000000, 'IFSTEST_SUCCESS'): AppVeyorTestOutcome.Passed,
        (0x00000001, 'IFSTEST_SUCCESS_NOT_SUPPORTED'): AppVeyorTestOutcome.Skipped,

        # we could claim the test is passed, but better have a look at why the cleanup fails
        (0x4000000C, 'IFSTEST_INFO_PROBLEM_IN_CLEANUP'): AppVeyorTestOutcome.Failed,

        (0xC0000015, 'IFSTEST_TEST_ATTRIBUTE_ERROR'): AppVeyorTestOutcome.Failed,
        (0xC000001F, 'IFSTEST_TEST_IOSTATUSBLOCK_FAILURE'): AppVeyorTestOutcome.Failed,
        (0xC0000014, 'IFSTEST_TEST_ALLOCATION_SIZE_ERROR'): AppVeyorTestOutcome.Failed,
        (0xC000001E, 'IFSTEST_TEST_NTAPI_FAILURE_CODE'): AppVeyorTestOutcome.Failed,
        (0xC0000058, 'IFSTEST_TEST_WIN32_FAILURE'): AppVeyorTestOutcome.Failed,
        (0xC000002E, 'IFSTEST_TEST_UNICODE_NAME_PRESERVED'): AppVeyorTestOutcome.Failed,

        (0xC000005E, 'IFSTEST_TEST_QUOTA_TEST_NOT_RUN'): AppVeyorTestOutcome.NotRunnable,
        (0x80000010, 'IFSTEST_TEST_NOT_SUPPORTED'): AppVeyorTestOutcome.NotRunnable,
        # abusing None status here, because this error usually means that we did not start IFSTest from a clean dir
        (0xC0000092, 'IFSTEST_SETUP_NTAPI_CREATE_DIR_FAILURE'): AppVeyorTestOutcome.None_,
    }
    STATUS_RE = re.compile(r'^([0-9A-F]{8}) \(([A-Z0-9_]+)\)')

    def __convert_ifstest_status_to_appveyor(self, ifstest_status_str):
        # None | Running | Passed | Failed | Ignored | Skipped| Inconclusive | NotFound | Cancelled | NotRunnable}
        match_result = self.STATUS_RE.match(ifstest_status_str)
        if not match_result:
            return AppVeyorTestOutcome.Ignored
        ifstest_status = (int(match_result.groups()[0], base=16), match_result.groups()[1])

        if not ifstest_status in self.IFSTEST_TO_APPVEYOR_STATUS:
            print("Unknown status: " + ifstest_status_str, file=sys.stderr)
        return self.IFSTEST_TO_APPVEYOR_STATUS.get(ifstest_status, AppVeyorTestOutcome.Failed)
