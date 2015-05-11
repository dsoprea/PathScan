import logging
import time
import multiprocessing
import queue
import threading

import fss.config.general
import fss.config.workers
import fss.workers.generator
import fss.workers.worker_base

_LOGGER = logging.getLogger(__name__)


class Orchestrator(object):
    def __init__(self, path, filter_rules):
        self.__path = path
        self.__filter_rules = filter_rules

    def recurse(self):
        _LOGGER.info("Orchestrator running.")

        log_q = multiprocessing.Queue()

        # This is shared among all of the workers, in order to track their 
        # states.
        m = multiprocessing.Manager()
        pipeline_state = m.dict({
            ('running_' + fss.constants.PC_GENERATOR): 
                fss.constants.PCS_INITIAL,
        })

        # Create the generator.

        generator_input_q = multiprocessing.Queue()
        generator_input_q.put(self.__path)

        g = fss.workers.generator.GeneratorController(
                self.__filter_rules,
                pipeline_state, 
                generator_input_q,
                log_q)

        # Start the pipeline.

        g.start()

        # Start foreground loop.

        # Loop while any of the components is still running (but only check 
        # when all components have been started).
        keep_running = True
        while keep_running is True:
            # Yield any results.

            i = 0
            while i < fss.config.general.MAX_RESULT_BATCH_READ_COUNT:
                try:
                    entry = g.output_q.get(block=False)
                except queue.Empty:
                    break
                else:
                    if issubclass(
                            entry.__class__, 
                            fss.workers.worker_base.TerminationMessage) is True:

                        keep_running = False
                        break

                    (entry_type, entry_filepath) = entry
                    yield (entry_type, entry_filepath)

                i += 1

            # Forward log messages to local log-handler.

            j = 0
            while j < fss.config.general.MAX_LOG_BATCH_READ_COUNT:
                try:
                    (cls_name, level, message) = log_q.get(block=False)
                except queue.Empty:
                    break
                else:
                    _LOGGER.log(level, cls_name + ": " + message)

        _LOGGER.info("Terminating worker.")

        g.stop()
