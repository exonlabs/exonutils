# -*- coding: utf-8 -*-
import sys
import logging
from time import sleep
from argparse import ArgumentParser
from traceback import format_exc

from exonutils.process import BaseProcess

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout,
    format='%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s')
logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.CRITICAL, "FATAL")


class SampleProcess(BaseProcess):

    def initialize(self):
        self.log.info("Initializing")
        self.counter = 0

    def execute(self):
        self.log.debug("Running: %s ..." % self.counter)
        self.counter += 1
        sleep(2)

    def terminate(self):
        self.log.info("Shutting down")

    def handle_sigusr1(self):
        rootlogger = logging.getLogger()
        if rootlogger.level != logging.DEBUG:
            rootlogger.setLevel(logging.DEBUG)
            self.log.info("debugging ON")
        else:
            rootlogger.setLevel(logging.INFO)
            self.log.info("debugging OFF")

    def handle_sigusr2(self):
        self.counter = 0
        self.log.info("Counter reset")


if __name__ == '__main__':
    log = logging.getLogger()
    log.name = 'main'
    try:
        pr = ArgumentParser(prog=None)
        pr.add_argument(
            '-x', dest='debug', action='count', default=0,
            help='set debug modes')
        args = pr.parse_args()

        if args.debug > 0:
            log.setLevel(logging.DEBUG)

        p = SampleProcess('SampleProcess', logger=log, debug=args.debug)
        p.start()

    except Exception:
        log.fatal(format_exc())
        sys.exit(1)
