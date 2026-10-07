import logging
import sys

import gevent
from locust import events
from locust.env import Environment
from locust.stats import stats_history, stats_printer

from integration_tests import settings
from integration_tests.users import CatalogusUser
from integration_tests.utils import get_token

logger = logging.getLogger(__name__)


@events.test_start.add_listener
def _(environment, **kwargs):
    environment.employee_token = get_token(settings.TOKEN) if settings.TOKEN else None
    environment.team_token = get_token(settings.TEAM_TOKEN) if settings.TEAM_TOKEN else None
    environment.admin_token = get_token(settings.ADMIN_TOKEN) if settings.ADMIN_TOKEN else None


@events.test_stop.add_listener
def analyze_results(environment, **kwargs):
    """Analyze results when test completes."""

    # Access overall statistics
    total_stats = environment.stats.total

    if total_stats.num_failures > settings.ALLOWED_FAILURES:
        logger.error("Catalogus Integration Tests Failed")
        sys.exit(1)
    else:
        logger.info("Catalogus API Integration Tests Passed")


def run_tests(endpoints, **kwargs):
    # setup Environment and Runner
    env = Environment(user_classes=[CatalogusUser], events=events, tags=endpoints)
    # env.employee_token = get_token(settings.TOKEN) if settings.TOKEN else None
    # env.team_token = get_token(settings.TEAM_TOKEN) if settings.TEAM_TOKEN else None
    # env.admin_token = get_token(settings.ADMIN_TOKEN) if settings.ADMIN_TOKEN else None
    runner = env.create_local_runner()

    # start a greenlet that periodically outputs the current stats
    gevent.spawn(stats_printer(env.stats))

    # start a greenlet that save current stats to history
    gevent.spawn(stats_history, env.runner)

    # start the test
    runner.start(user_count=2, spawn_rate=1)

    # in 30 seconds stop the runner
    gevent.spawn_later(30, runner.quit)

    # wait for the greenlets
    runner.greenlet.join()
