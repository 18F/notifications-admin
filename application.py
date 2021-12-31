import os

import sentry_sdk
from flask import Flask
from sentry_sdk.integrations.flask import FlaskIntegration

from app import create_app

sentry_sdk.init(
    dsn=os.environ['SENTRY_DSN'],
    integrations=[FlaskIntegration()],
    environment=os.environ['NOTIFY_ENVIRONMENT'],
    attach_stacktrace=True,
    traces_sample_rate=0.00005  # avoid exceeding rate limits in Production
)
sentry_sdk.set_level('error')  # only record error logs or exceptions

application = Flask('app')

create_app(application)
