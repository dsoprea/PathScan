import multiprocessing
import time
import logging
import queue
import os.path

import fss.constants
import fss.config.workers
import fss.workers.controller_base
import fss.workers.worker_base

_LOGGER = logging.getLogger(__name__)


class GeneratorWorker(fss.workers.worker_base.WorkerBase):
    """This class knows how to recursively traverse a path to produce a list of 
    file-paths.
    """

    def __init__(self, *args):
        super(GeneratorWorker, self).__init__(*args)

        _LOGGER.info("Creating generator.")

    def process_item(self, path):
        for filename in os.listdir(path):
            if self.check_quit() is True:
                return False

            if self.tick_count % \
                    fss.config.workers.PROGRESS_LOG_TICK_INTERVAL == 0:
                self.log(
                    logging.DEBUG, 
                    "Generator progress: (%d)", 
                    self.tick_count)

            filepath = os.path.join(path, filename)

            # We'll populate our own input-queue with downstream paths.
            if os.path.isdir(filepath):
                self.push_to_output((fss.constants.FT_DIR, filepath))
                self.input_q.put(filepath)
            else:
                self.push_to_output((fss.constants.FT_FILE, filepath))

            self.increment_tick()

    def get_component_name(self):
        return fss.constants.PC_GENERATOR


class GeneratorController(fss.workers.controller_base.ControllerBase):
    def __init__(self, *args, **kwargs):
        super(GeneratorController, self).__init__(*args, **kwargs)

        args = (
            self.pipeline_state, 
            self.input_q,
            self.output_q, 
            self.log_q, 
            self.quit_ev
        )

        self.__p = multiprocessing.Process(target=_boot, args=args)

    def start(self):
        _LOGGER.info("Starting generator.")
        self.__p.start()

    def stop(self):
        _LOGGER.info("Stopping generator.")
        self.quit_ev.set()
# TODO(dustin): Audit for a period of time, and then stop it.
        self.__p.join()

    @property
    def output_queue_size(self):
        return fss.config.workers.GENERATOR_MAX_OUTPUT_QUEUE_SIZE

def _boot(pipeline_state, input_q, output_q, log_q, quit_ev):
    _LOGGER.info("Booting generator worker.")

    g = GeneratorWorker(
            pipeline_state, 
            input_q, 
            output_q, 
            log_q, 
            quit_ev)

    g.run()
