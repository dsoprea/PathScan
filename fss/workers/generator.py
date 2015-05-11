import multiprocessing
import time
import logging
import queue
import os
import fnmatch
import pprint

import fss.constants
import fss.config
import fss.config.workers
import fss.workers.controller_base
import fss.workers.worker_base

_LOGGER = logging.getLogger(__name__)

_LOGGER_FILTER = logging.getLogger(__name__ + '.-filter–')

_IS_FILTER_DEBUG = bool(int(os.environ.get('FSS_FILTER_DEBUG', '0')))

if _IS_FILTER_DEBUG is True:
    _LOGGER_FILTER.setLevel(logging.DEBUG)
else:
    _LOGGER_FILTER.setLevel(logging.WARNING)


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
        self.__local_input_q = queue.Queue()

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

        # If an include filter was given for DIRECTORIES, add an exclude filter 
        # for "*". Since we check the include rules, first, we'll simply not be 
        # implicitly including anything else.

        rules = self.__filter_rules[fss.constants.FT_DIR]
        if rules[fss.constants.FILTER_INCLUDE]:
            rules[fss.constants.FILTER_EXCLUDE].append('*')

        # If an include filter was given for FILES, add an exclude filter for
        # "*". Since we check the include rules, first, we'll simply not be 
        # implicitly including anything else.

        rules = self.__filter_rules[fss.constants.FT_FILE]
        if rules[fss.constants.FILTER_INCLUDE]:
            rules[fss.constants.FILTER_EXCLUDE].append('*')

        if fss.config.IS_DEBUG is True:
            _LOGGER.debug("Final rules:\n%s", 
                          pprint.pformat(self.__filter_rules))

    def __check_to_permit(self, entry_type, entry_filename):
        """Applying the filter rules."""

        rules = self.__filter_rules[entry_type]

        # Should explicitly include?
        for pattern in rules[fss.constants.FILTER_INCLUDE]:
            if fnmatch.fnmatch(entry_filename, pattern):
                _LOGGER_FILTER.debug("Entry explicitly INCLUDED: [%s] [%s] "
                                     "[%s]", 
                                     entry_type, pattern, entry_filename)

                return True

        # Should explicitly exclude?
        for pattern in rules[fss.constants.FILTER_EXCLUDE]:
            if fnmatch.fnmatch(entry_filename, pattern):
                _LOGGER_FILTER.debug("Entry explicitly EXCLUDED: [%s] [%s] "
                                     "[%s]", 
                                     entry_type, pattern, entry_filename)

                return False

        # Implicitly include.

        _LOGGER_FILTER.debug("Entry IMPLICITLY included: [%s] [%s]", 
                             entry_type, entry_filename)

        return True

    def get_next_item(self):
        """Override the default functionality to not only try to pull things 
        off the external input-queue, but to first try to pull things from a 
        local input-queue that we'll primarily depend on. We'll only use the 
        external input-queue to get the initial root-path (we could reuse it to 
        do the recursion, but it's more costly and prone to delay).
        """

        # Try to pop something off the local input-queue.

        try:
            return self.__local_input_q.get(block=False)
        except queue.Empty:
            pass

        # Try to pop something off the external input-queue.

        return self.input_q.get(block=False)

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

        try:
            entries = os.listdir(entry_path)
        except:
            _LOGGER.exception("Skipping unreadable directory: [%s]", 
                              entry_path)
        else:
            for filename in entries:
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
                    
                    _LOGGER.debug("Pushing directory to local input-queue: "
                                  "[%s]", filepath)

                    self.__local_input_q.put(filepath)
                else:
                    self.push_to_output((fss.constants.FT_FILE, filepath))

                self.increment_tick()

    def get_component_name(self):
        return fss.constants.PC_GENERATOR

    @property
    def terminate_on_idle(self):
        return True


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
