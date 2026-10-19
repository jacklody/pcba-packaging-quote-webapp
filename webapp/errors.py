import logging

from werkzeug.exceptions import BadRequest, HTTPException, InternalServerError, NotFound, MethodNotAllowed

from webapp.responses import fail

logger = logging.getLogger(__name__)


class ApiValidationError(ValueError):
    pass


def register_error_handlers(app):
    @app.errorhandler(ApiValidationError)
    @app.errorhandler(BadRequest)
    def handle_bad_request(exc):
        return fail(400, str(exc) or "bad request", 400)

    @app.errorhandler(NotFound)
    def handle_not_found(exc):
        return fail(404, exc.description or "not found", 404)

    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(_exc):
        return fail(405, "method not allowed", 405)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        return fail(exc.code or 500, exc.description or "request failed", exc.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        logger.exception("Unhandled API error")
        return fail(500, "internal server error", 500)
