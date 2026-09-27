"""A request keeps the account it started with, including thread-pool work."""
from contextvars import ContextVar

UNSET = object()
request_account = ContextVar("codememory_request_account", default=UNSET)
