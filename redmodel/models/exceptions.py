import redmodel.containers

class Error(Exception):
    pass

class NotFoundError(Error):
    pass

class BadArgsError(Error):
    pass

UniqueError = redmodel.containers.UniqueError
