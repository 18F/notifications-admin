from flask import (
    render_template,
    url_for
)

from flask_login import login_required
from werkzeug.utils import redirect
from app.main import main
from app.main.forms import ProviderForm
from app.utils import user_has_permissions
from app import provider_client


@main.route("/providers")
@login_required
@user_has_permissions(admin_override=True)
def view_providers():
    providers = provider_client.get_all_providers()['provider_details']
    email_providers = [email for email in providers if email['notification_type'] == 'email']
    sms_providers = [sms for sms in providers if sms['notification_type'] == 'sms']
    return render_template(
        'views/providers/providers.html',
        email_providers=email_providers,
        sms_providers=sms_providers
    )


@main.route("/provider/<provider_id>/edit", methods=['GET', 'POST'])
@login_required
@user_has_permissions(admin_override=True)
def edit_provider(provider_id):
    provider = provider_client.get_provider_by_id(provider_id)['provider_details']
    form = ProviderForm(active=provider['active'], priority=provider['priority'])

    if form.validate_on_submit():
        provider_client.update_provider(provider_id, form.priority.data)
        return redirect(url_for('.view_providers'))

    return render_template('views/providers/edit-provider.html', form=form, provider=provider)


@main.route("/provider/<provider_id>")
@login_required
@user_has_permissions(admin_override=True)
def view_provider(provider_id):
    versions = provider_client.get_provider_versions(provider_id)
    return render_template('views/providers/provider.html', provider_versions=versions['data'])
