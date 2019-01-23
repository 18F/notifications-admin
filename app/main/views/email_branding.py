from flask import current_app, redirect, render_template, session, url_for
from flask_login import login_required

from app import email_branding_client
from app.main import main
from app.main.forms import SearchTemplatesForm, ServiceUpdateEmailBranding
from app.main.s3_client import (
    TEMP_TAG,
    delete_temp_file,
    delete_temp_files_created_by,
    persist_logo,
    upload_logo,
)
from app.utils import AgreementInfo, get_logo_cdn_domain, user_is_platform_admin


@main.route("/email-branding", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def email_branding():
    brandings = email_branding_client.get_all_email_branding(sort_key='name')

    return render_template(
        'views/email-branding/select-branding.html',
        email_brandings=brandings,
        search_form=SearchTemplatesForm(),
        show_search_box=len(brandings) > 9,
        agreement_info=AgreementInfo,
    )


@main.route("/email-branding/<branding_id>/edit", methods=['GET', 'POST'])
@main.route("/email-branding/<branding_id>/edit/<logo>", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def update_email_branding(branding_id, logo=None):
    email_branding = email_branding_client.get_email_branding(branding_id)['email_branding']

    form = ServiceUpdateEmailBranding(
        name=email_branding['name'],
        text=email_branding['text'],
        colour=email_branding['colour'],
        domain=email_branding['domain'],
        brand_type=email_branding['brand_type']
    )

    logo = logo if logo else email_branding.get('logo') if email_branding else None

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_logo(
                form.file.data.filename,
                form.file.data,
                current_app.config['AWS_REGION'],
                user_id=session["user_id"]
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=session['user_id'])):
                delete_temp_file(logo)

            return redirect(url_for('.update_email_branding', branding_id=branding_id, logo=upload_filename))

        if logo:
            logo = persist_logo(logo, session["user_id"])

        delete_temp_files_created_by(session["user_id"])

        email_branding_client.update_email_branding(
            branding_id=branding_id,
            logo=logo,
            name=form.name.data,
            text=form.text.data,
            colour=form.colour.data,
            domain=form.domain.data,
            brand_type=form.brand_type.data,
        )

        return redirect(url_for('.email_branding', branding_id=branding_id))

    return render_template(
        'views/email-branding/manage-branding.html',
        form=form,
        email_branding=email_branding,
        cdn_url=get_logo_cdn_domain(),
        logo=logo
    )


@main.route("/email-branding/create", methods=['GET', 'POST'])
@main.route("/email-branding/create/<logo>", methods=['GET', 'POST'])
@login_required
@user_is_platform_admin
def create_email_branding(logo=None):
    form = ServiceUpdateEmailBranding(brand_type='org')

    if form.validate_on_submit():
        if form.file.data:
            upload_filename = upload_logo(
                form.file.data.filename,
                form.file.data,
                current_app.config['AWS_REGION'],
                user_id=session["user_id"]
            )

            if logo and logo.startswith(TEMP_TAG.format(user_id=session['user_id'])):
                delete_temp_file(logo)

            return redirect(url_for('.create_email_branding', logo=upload_filename))

        if logo:
            logo = persist_logo(logo, session["user_id"])

        delete_temp_files_created_by(session["user_id"])

        email_branding_client.create_email_branding(
            logo=logo,
            name=form.name.data,
            text=form.text.data,
            colour=form.colour.data,
            domain=form.domain.data,
            brand_type=form.brand_type.data,
        )

        return redirect(url_for('.email_branding'))

    return render_template(
        'views/email-branding/manage-branding.html',
        form=form,
        cdn_url=get_logo_cdn_domain(),
        logo=logo
    )
