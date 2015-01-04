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


class ExecutorWorker(fss.workers.worker_base.WorkerBase):
    """This class knows how to recursively traverse a path to produce a list of 
    file-paths.
    """

    def __init__(self, fq_handler_cls_name, *args):
        super(ExecutorWorker, self).__init__(*args)

        self.log(logging.INFO, "Creating executor.")

        self.__fq_handler_cls_name = fq_handler_cls_name

    def process_item(self, item):
        (entry_type, entry_path) = item

# TODO(dustin): Finish this.
        # fss.constants.FT_DIR
        # fss.constants.FT_FILE

#        self.push_to_output((entry_type, entry_path))

    def post_loop_hook(self):
        #self.set_finished()
        pass

    def get_component_name(self):
        return fss.constants.PC_EXECUTOR

    def get_upstream_component_name(self):
        return fss.constants.PC_FILTER


class ExecutorController(fss.workers.controller_base.ControllerBase):
    def __init__(self, fq_handler_cls_name, *args, **kwargs):
        super(ExecutorController, self).__init__(*args, **kwargs)

        args = (
            fq_handler_cls_name,
            self.pipeline_state, 
            self.input_q, 
            self.output_q,
            self.log_q, 
            self.quit_ev 
        )

        self.__p = multiprocessing.Process(target=_boot, args=args)

    def start(self):
        _LOGGER.info("Starting executor.")
        self.__p.start()

    def stop(self):
        _LOGGER.info("Stopping executor.")

        self.quit_ev.set()
# TODO(dustin): Audit for a period of time, and then stop it.
        self.__p.join()

    @property
    def output_queue_size(self):
        return fss.config.workers.FILTER_MAX_OUTPUT_QUEUE_SIZE

def _boot(fq_handler_cls_name, pipeline_state, input_q, output_q, log_q, quit_ev):
    _LOGGER.info("Booting executor worker.")

    e = ExecutorWorker(
            fq_handler_cls_name, 
            pipeline_state, 
            input_q, 
            output_q, 
            log_q, 
            quit_ev)

    e.run()
