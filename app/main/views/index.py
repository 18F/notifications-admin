from flask import render_template
from app.main import main


@main.route('/')
def index():
    return render_template('views/signedout.html')


@main.route("/govuk")
def govuk():
    return render_template('views/govuk_template.html')


@main.route("/register-from-invite")
def registerfrominvite():
    return render_template('views/register-from-invite.html')


@main.route("/verify-mobile")
def verifymobile():
    return render_template('views/verify-mobile.html')


@main.route("/send-email")
def sendemail():
    return render_template('views/send-email.html')


@main.route("/check-email")
def checkemail():
    return render_template('views/check-email.html')


@main.route("/user-profile")
def userprofile():
    return render_template('views/user-profile.html')


@main.route("/manage-users")
def manageusers():
    return render_template('views/manage-users.html')


@main.route("/api-keys")
def apikeys():
    return render_template('views/api-keys.html')


@main.route("/manage-templates")
def managetemplates():
    return render_template('views/manage-templates.html')


@main.route("/edit-template")
def edittemplate():
    return render_template('views/edit-template.html')
