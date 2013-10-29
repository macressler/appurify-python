'''
Created on Oct 15, 2013

@author: twang
'''
import signal

class SigintException(Exception):
    pass

class AbortException(SigintException):
    message = "Test run aborted at user request"
    pass

class ContinueException(SigintException):
    message = "Continuing test execution"
    pass

class QuitException(SigintException):
    message = "Script quit at user request without aborting test run"
    pass

def signal_handler(signal, frame):
    response = None
    while not response or response not in ['a', 'A', 'q', 'Q', 'c', 'C']:
        response = read_input("Interrupted: (a)bort test run, (q)uit script without aborting or (c)ontinue script? [a/q/c]")
    if response in ['a', 'A']:
        raise AbortException
    elif response in ['c', 'C']:
        raise ContinueException
    else:
        raise QuitException

def read_input(prompt):
    try:
        response = raw_input(prompt)
    except:
        response = input(prompt)
    return response

signal.signal(signal.SIGINT, signal_handler)

