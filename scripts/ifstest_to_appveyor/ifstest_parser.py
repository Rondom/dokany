import sys
import re
from pprint import pprint
from collections import OrderedDict
from datetime import datetime

class ParseError(RuntimeError):
    pass

class State:
    BLANK_LINE_RE = re.compile(r"^$")
    DASHED_LINE_RE = re.compile("^-{50}$")

    is_final = False

    def __init__(self, previous_state, **kwargs):
        self.test_case_queue = previous_state.test_case_queue
        if not getattr(self, 'transition_map', None):
            self.transition_map = {}

    def transition(self, line):
        """
        default implementation uses self.transition_map to determine the next state
        :param line: current line without \n, None if EOF
        :return: the next state
        """
        for (line_re, next_state) in self.transition_map.items():
            if line_re and line is not None:
                match = line_re.match(line)
                if match:
                    return next_state(self, **match.groupdict())
            elif line is None:
                return self.transition_map[None](self)

        if line is None:
            raise ParseError(f'State {self.__class__.__name__}: Unexpected end of file')
        else:
            raise ParseError(f'State {self.__class__.__name__}: Unexpected line: "{line}"')


class WaitForHeaderState(State):
    """
    skips blank lines, transitions to HeaderState once it encounters a dashed line (introduction of header) 
    """

    def __init__(self, previous_state=None, **kwargs):
        if previous_state is None:
            self.test_case_queue = kwargs['test_case_queue']
        else:
            self.test_case_queue = previous_state.test_case_queue
        self.transition_map = {
            self.BLANK_LINE_RE: self.__class__,
            self.DASHED_LINE_RE: HeaderState,
        }

class HeaderState(State):
    """
    skips header, moves to WaitForTestCaseState once a dashed line is encountered.
    Header usually looks like this:
    
    --------------------------------------------------
    
    +++Microsoft (R) Installable File System Test for Windows XP/2003/Vista+++:: Probe-Header: :  
    
    +++Test SW Build 0014 Init Thursday March 30, 2017 00:39:25+++
    
    --------------------------------------------------
    
    """

    HEADER_RE = re.compile(r"^.*$")

    def __init__(self, previous_state, **kwargs):
        super().__init__(previous_state, **kwargs)
        self.transition_map = OrderedDict({ # DASHED_LINE_RE needs to have priority
            self.DASHED_LINE_RE: WaitForTestCaseState,
            self.HEADER_RE: self.__class__,
        })

class WaitForTestCaseState(State):
    """
    skips empty lines and transitions to ProcessTestCaseState in case it enounters a line like this:
    Test         :OpenCreateGeneral
    
    In case of EOF, we consider our work finished
    """

    # \d? at the beginning is to work around some leftover debug-print that appears before the first Test
    FIRST_LINE_OF_TEST_CASE_RE = re.compile(r"^\d?(?P<key>Test) +:(?P<value>.*)$")
    def __init__(self, previous_state, **kwargs):
        super().__init__(previous_state, **kwargs)
        self.transition_map = {
            self.FIRST_LINE_OF_TEST_CASE_RE: ProcessTestCaseState,
            self.BLANK_LINE_RE: self.__class__,
            None: FinalState,
        }

class ProcessTestCaseState(State):
    """
    Processes one test case block, moves to WaitForTestCaseState once a blank line is encountered:
    Example input:
    Group        :OpenCreateParameters
    File         :g:\ifstest\code\opcreatp\crfile.c
    Line         :150
    Status       :24 (IFSTEST_TEST_NTAPI_FAILURE_CODE)
    LastNtStatus     :C0000022 STATUS_ACCESS_DENIED
    ExpectedNtStatus :00000000 STATUS_SUCCESS
    Description  :
    A failure was encountered when trying to create the file (\elifrc.dat)
    in the directory (\??\W:\opcreatp).  Check the last
    NT status returned.  
    """
    TEST_CASE_KV_LINE_RE = re.compile(r"^(?P<key>\w+) +:(?P<value>.*)$")
    TEST_CASE_KV_LINE_CONTINUATION = re.compile(r"^ *(?P<value_continuation>.+)$")

    def __init__(self, previous_state, **kwargs):
        super().__init__(previous_state, **kwargs)
        # data from either WaitForTestCaseState or this state
        current_key = kwargs['key']
        current_value = kwargs['value']
        if hasattr(previous_state, 'test_case_data'):
            self.test_case_data = previous_state.test_case_data
        else:
            self.test_case_data = OrderedDict()
            self.test_case_data['StartTime'] = datetime.utcnow()

        def save_old_kv_and_proceed(_, **new_kwargs):
            # save old key
            self.test_case_data[current_key] = current_value
            # pass new kv-pair read via regex to new state
            return ProcessTestCaseState(self, **new_kwargs)

        def save_old_kv_and_tc_data_move_to_wait_for_test_case_state(_, **new_kwargs):
            self.test_case_data['EndTime'] = datetime.utcnow()
            self.test_case_data[current_key] = current_value
            if self.test_case_data['Status'] != '40000006 (IFSTEST_INFO_END_OF_GROUP)':
                self.test_case_queue.append(self.test_case_data)
            #pprint(self.test_case_data)
            #print()
            return WaitForTestCaseState(self, **new_kwargs)

        def continue_line(previous_state, **new_kwargs):
            nonlocal current_value
            if current_value:
                current_value += " " + new_kwargs['value_continuation']
            else:
                current_value = new_kwargs['value_continuation']
            return ProcessTestCaseState(self, key=current_key, value=current_value)

        self.transition_map = OrderedDict({
            self.TEST_CASE_KV_LINE_RE: save_old_kv_and_proceed,
            self.TEST_CASE_KV_LINE_CONTINUATION: continue_line,
            self.BLANK_LINE_RE: save_old_kv_and_tc_data_move_to_wait_for_test_case_state,
        })

class FinalState(State):
    def __init__(self, previous_state, **kwargs):
        super().__init__(previous_state, **kwargs)
        self.is_final = True


def parse(file, test_case_queue):
    state = WaitForHeaderState(test_case_queue=test_case_queue)
    for line in file:
        print(line, end='')
        state = state.transition(line.rstrip('\n'))
        if state.is_final:
            print("Reached final state")
            return

    state = state.transition(None) # EOF
    # TODO: check if this check can be removed
    if not state.is_final:
        raise ParseError(f"{state.__class__.__name__}: Reached EOF without being in final state.")
    test_case_queue.append({'IsFinished': True})
