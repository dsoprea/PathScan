import multiprocessing
import time
import logging
import queue
import os.path
import fnmatch

import fss.constants
import fss.config.workers
import fss.workers.controller_base
import fss.workers.worker_base

_LOGGER = logging.getLogger(__name__)


class GeneratorWorker(fss.workers.worker_base.WorkerBase):
    """This class knows how to recursively traverse a path to produce a list of 
    file-paths.
    """

    def __init__(self, filter_rules_raw, *args):
        super(GeneratorWorker, self).__init__(*args)

        _LOGGER.info("Creating generator.")

        # Set after we've popped the first item off the queue.
        self.__processed_first = False

        self.__filter_rules = None
        self.__load_filter_rules(filter_rules_raw)

    def __load_filter_rules(self, filter_rules_raw):
        _LOGGER.debug("Loading filter-rules.")

        # We expect this to be a listof 3-tuples: 
        #
        #     (entry-type, filter-type, pattern)
        
        self.__filter_rules = {
            fss.constants.FT_DIR: {
                fss.constants.FILTER_INCLUDE: [],
                fss.constants.FILTER_EXCLUDE: [],
            },
            fss.constants.FT_FILE: {
                fss.constants.FILTER_INCLUDE: [],
                fss.constants.FILTER_EXCLUDE: [],
            },
        }

        for (entry_type, filter_type, pattern) in filter_rules_raw:
            self.__filter_rules[entry_type][filter_type].append(pattern)

        # If an include filter was given for DIRECTORIES, but no exclude 
        # filter, exclude everything but what hits on the include.

        rules = self.__filter_rules[fss.constants.FT_DIR]
        if rules[fss.constants.FILTER_INCLUDE] and \
           not rules[fss.constants.FILTER_EXCLUDE]:
            rules[fss.constants.FILTER_EXCLUDE].append('*')

        # If an include filter was given for FILES, but no exclude filter, 
        # exclude everything but what hits on the include.

        rules = self.__filter_rules[fss.constants.FT_FILE]
        if rules[fss.constants.FILTER_INCLUDE] and \
           not rules[fss.constants.FILTER_EXCLUDE]:
            rules[fss.constants.FILTER_EXCLUDE].append('*')

    def __check_to_permit(self, entry_type, entry_filename):
        """Applying the filter rules."""

        rules = self.__filter_rules[entry_type]

        # Should explicitly include?
        for pattern in rules[fss.constants.FILTER_INCLUDE]:
            if fnmatch.fnmatch(entry_filename, pattern):
                _LOGGER.debug("Entry explicitly INCLUDED: [%s] [%s] [%s]", 
                              entry_type, pattern, entry_filename)

                return True

        # Should explicitly exclude?
        for pattern in rules[fss.constants.FILTER_EXCLUDE]:
            if fnmatch.fnmatch(entry_filename, pattern):
                _LOGGER.debug("Entry explicitly EXCLUDED: [%s] [%s] [%s]", 
                              entry_type, pattern, entry_filename)

                return False

        # Implicitly include.

        _LOGGER.debug("Entry IMPLICITLY included: [%s] [%s]", 
                      entry_type, entry_filename)

        return True

    def process_item(self, entry_path):
        _LOGGER.debug("Processing: [%s]", entry_path)

        entry_filename = os.path.basename(entry_path)

        # The first item in the queue is the root-directory to be scanned. It's 
        # not subject to the filter-rules.
        if self.__processed_first is True:
            if self.__check_to_permit(
                fss.constants.FT_DIR, 
                entry_filename) is False:

                # Skip.
                return True
        else:
            self.__processed_first = True

        for filename in os.listdir(entry_path):
            if self.check_quit() is True:
                _LOGGER.warning("Generator has been told to quit before "
                                "finishing. WITHIN=[%s]", entry_path)

                return False

            filepath = os.path.join(entry_path, filename)
            is_dir = os.path.isdir(filepath)

            file_type = fss.constants.FT_DIR \
                            if is_dir is True \
                            else fss.constants.FT_FILE

            if self.__check_to_permit(file_type, filename) is False:
                continue

            if self.tick_count % \
                    fss.config.workers.PROGRESS_LOG_TICK_INTERVAL == 0:
                self.log(
                    logging.DEBUG, 
                    "Generator progress: (%d)", 
                    self.tick_count)

            # We'll populate our own input-queue with downstream paths.
            if is_dir:
                self.push_to_output((fss.constants.FT_DIR, filepath))
                
                _LOGGER.debug("Pushing directory to input-queue: [%s]", 
                              filepath)

                self.input_q.put(filepath)
            else:
                self.push_to_output((fss.constants.FT_FILE, filepath))

            self.increment_tick()

    def get_component_name(self):
        return fss.constants.PC_GENERATOR


class GeneratorController(fss.workers.controller_base.ControllerBase):
    def __init__(self, filter_rules_raw, *args, **kwargs):
        super(GeneratorController, self).__init__(*args, **kwargs)

        args = (
            filter_rules_raw,
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

def _boot(filter_rules_raw, pipeline_state, input_q, output_q, log_q, quit_ev):
    _LOGGER.info("Booting generator worker.")

    g = GeneratorWorker(
            filter_rules_raw,
            pipeline_state, 
            input_q, 
            output_q, 
            log_q, 
            quit_ev)

    g.run()
