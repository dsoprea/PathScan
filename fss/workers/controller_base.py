import multiprocessing


class ControllerBase(object):
    def __init__(self, pipeline_state, input_q, log_q, quit_ev=None):
        self.__pipeline_state = pipeline_state
        self.__log_q = log_q
        self.__input_q = input_q
        self.__output_q = multiprocessing.Queue(maxsize=self.output_queue_size)
        self.__quit_ev = quit_ev if quit_ev is not None else multiprocessing.Event()

    @property
    def pipeline_state(self):
        return self.__pipeline_state

    @property
    def log_q(self):
        return self.__log_q

    @property
    def input_q(self):
        return self.__input_q

    @property
    def output_q(self):
        return self.__output_q

    @property
    def quit_ev(self):
        return self.__quit_ev

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    @property
    def output_queue_size(self):
        raise NotImplementedError()
