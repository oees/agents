"""The one base class for problems a user can fix."""


class OeesAgentsError(ValueError):
    """The CLI shows this as `error: <message>`, without a traceback, and exits 1."""
