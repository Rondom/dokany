#!/usr/bin/python3
"""
This parses IFSTest output from stdin or a file and submits test case results to the AppVeyor build worker API

Usage:
  ifstest_to_appveyor.py [<input-file>] [options]
  ifstest_to_appveyor.py -h | --help
  ifstest_to_appveyor.py --version

  <input-file>     File to read the test output from. Default is stdin.

Options:
  --prefix=<prefix>    Adds a prefix to every test case submitted. Useful to distinguish multiple invocations of the same tests.
  -h --help            Show this screen.
  --version            Show version.


Run with APPVEYOR_API_URL="http://httpbin.org/anything/:" for testing the HTTP sending locally.
Otherwise the AppVeyor test case data will be printed to stdout.
"""
import sys
import os

from docopt import docopt
from ifstest_parser import parse
from collections import deque
from appveyor_sender import AppVeyorSender

def main(args):
    test_case_queue = deque()
    prefix = args['--prefix']
    # spawn consuming thread for sending TCs to AppVeyor
    appveyor_sender = AppVeyorSender(test_case_queue, prefix=prefix, build_worker_api_url=os.environ.get('APPVEYOR_API_URL'))
    appveyor_sender.consumer_thread.start()

    if args['<input-file>']:
        with open(args['<input-file>']) as input_file:
            parse(input_file, test_case_queue)
    else:
        parse(sys.stdin, test_case_queue)

    print('Waiting for test result sending to finish.')
    #TODO: add timeout
    appveyor_sender.consumer_thread.join()
    print('Done')
    return 0

if __name__ == "__main__":
    args = docopt(__doc__, version='IFSTest to AppVeyor 0.1')
    main(args)