# TODO: core/exceptions.py
class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UnsupportedFileTypeError(AppError):
    status_code = 415


class FileTooLargeError(AppError):
    status_code = 413


class EmptyDocumentError(AppError):
    status_code = 422

class CorruptFileError(AppError):
    status_code = 422

class LLMError(AppError):
    status_code = 502

class SessionNotFoundError(AppError):
    status_code = 404

class ResumeNotGeneratedError(AppError):
    status_code = 404