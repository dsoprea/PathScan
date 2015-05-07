import logging
import time
import multiprocessing
import queue
import threading

import fss.config.general
import fss.config.workers
import fss.workers.generator
import fss.workers.executor

_LOGGER = logging.getLogger(__name__)


class Orchestrator(object):
    def __init__(self, path, filter_rules, fq_handler_cls_name):
        self.__path = path
        self.__filter_rules = filter_rules
        self.__fq_handler_cls_name = fq_handler_cls_name

    def run(self):
        _LOGGER.info("Orchestrator running.")

        log_q = multiprocessing.Queue()

        # This is shared among all of the workers, in order to track their 
        # states.
        m = multiprocessing.Manager()
        pipeline_state = m.dict({
                                'running_' + fss.constants.PC_GENERATOR: fss.constants.PCS_INITIAL,
                                'running_' + fss.constants.PC_EXECUTOR: fss.constants.PCS_INITIAL,
                            })

        # Create the generator.

        generator_input_q = multiprocessing.Queue()
        generator_input_q.put(self.__path)

        g = fss.workers.generator.GeneratorController(
                self.__filter_rules,
                pipeline_state, 
                generator_input_q,
                log_q)

        # Create the executor.

        e = fss.workers.executor.ExecutorController(
                self.__fq_handler_cls_name,
                pipeline_state, 
                g.output_q, 
                log_q)

        # Start the pipeline.

        g.start()
        e.start()

        # Start foreground loop.

        # Loop while any of the components is still running (but only check 
        # when all components have been started).
        while True:
            states = [v for (k, v) in pipeline_state.items() if k.startswith('running_')]
            if min(states) >= fss.constants.PCS_STOPPED:
                break

# TODO(dustin): Check for any of the components not being alive.

            # Forward log messages to local log-handler.

            try:
                (cls_name, level, message) = log_q.get(timeout=fss.config.general.LOG_READ_BLOCK_TIMEOUT_S)
            except queue.Empty:
                #_LOGGER.debug("No log messages.")
                pass
            else:
                _LOGGER.log(level, cls_name + ": " + message)

        _LOGGER.info("Terminating workers.")

        e.stop()
        g.stop()
