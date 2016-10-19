__author__ = 'shahab'

import itertools
import threading
import sys
from time import sleep


def start_thread_pool(nodes, target_function, join=True, sleep_time=0.000001):
    threads = []
    results = {}

    for node in nodes:
        t = threading.Thread(target=target_function, args=[node, results])
        if not join:
            t.daemon = True
        t.start()
        threads.append(t)
        sleep(sleep_time)

    ret_val = True
    for t, n in zip(threads, nodes):
        if join:
            t.join()
            try:
                if not results[n]:
                    ret_val = False
            except KeyError:
                ret_val = False

    return ret_val


def on_success(result):  # default implementation
    """Called on the result of the function"""
    return result


def on_failure(exc_info):  # default implementation
    """Called if the function fails"""
    pass


def on_closing():  # default implementation
    """Called at the end, both in case of success and failure"""
    pass


class Async(object):
    """
    A decorator converting blocking functions into asynchronous
    functions, by using threads or processes. Examples:

    async_with_threads =  Async(threading.Thread)
    async_with_processes =  Async(multiprocessing.Process)
    """

    def __init__(self, threadfactory=threading.Thread, on_success=on_success, on_failure=on_failure,
                 on_closing=on_closing):

        self.threadfactory = threadfactory
        self.on_success = on_success
        self.on_failure = on_failure
        self.on_closing = on_closing

    def __call__(self, func, *args, **kw):
        try:
            counter = func.counter
        except AttributeError:  # instantiate the counter at the first call
            counter = func.counter = itertools.count(1)
        name = '%s-%s' % (func.__name__, next(counter))

        def func_wrapper():
            try:
                result = func(*args, **kw)
            except:
                self.on_failure(sys.exc_info())
            else:
                return self.on_success(result)
            finally:
                self.on_closing()

        thread = self.threadfactory(None, func_wrapper, name)
        thread.start()
        return thread
