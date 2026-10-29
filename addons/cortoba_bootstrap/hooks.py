import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Apply the Egyptian setup and create the bridge service user.

    Runs once when the module is first installed. Both steps are idempotent, so
    a re-install or a second call is harmless.
    """
    env["res.company"].cortoba_bootstrap()
    env["res.users"].cortoba_ensure_bridge_user()
    _logger.info("cortoba: bootstrap finished")
