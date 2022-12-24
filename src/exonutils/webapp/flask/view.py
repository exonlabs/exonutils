# -*- coding: utf-8 -*-
from flask import request

__all__ = []


class BaseWebView(object):
    # list of tuples: [(url, endpoint), ...]
    routes = []
    # allowed methods for view
    methods = ['GET', 'POST']

    def __init__(self, name=None, logger=None, debug=0):
        # view name
        self.name = name if name else self.__class__.__name__
        # view parent handler
        self.parent = None
        # view logger
        self.log = logger
        # debug mode
        self.debug = debug

    def initialize(self):
        pass

    # check xhr/ajax request type
    @classmethod
    def is_xhrequest(cls):
        return bool(
            request.headers.get('X-Requested-With') == 'XMLHttpRequest')

    # check json or xhr/ajax request type
    @classmethod
    def is_jsrequest(cls):
        return bool(
            'json' in str(request.headers.get('Content-Type')) or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest')

    def dispatch_request(self, **kwargs):
        # exec before request handlers
        if hasattr(self, 'before_request'):
            response = self.before_request(**kwargs)
            if response is not None:
                return response

        # dispatch request
        response = self.handle_request(**kwargs)

        # exec after request handlers
        if hasattr(self, 'after_request'):
            return self.after_request(response, **kwargs)

        return response

    def handle_request(self, **kwargs):
        method = request.method.lower()
        if not hasattr(self, method):
            # use GET method instead of HEAD if not implemented
            if method == 'head' and hasattr(self, 'get'):
                method = 'get'
            else:
                return "Method Not Allowed", 405

        return getattr(self, method)(**kwargs)

    # def before_request(self, **kwargs):
    #     return None

    # def after_request(self, response, **kwargs):
    #     return response

    # def head(self, **kwargs):
    #     raise NotImplementedError()

    # def get(self, **kwargs):
    #     raise NotImplementedError()

    # def post(self, **kwargs):
    #     raise NotImplementedError()
