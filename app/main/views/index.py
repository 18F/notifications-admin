from flask import render_template
from flask_login import login_required

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


@main.route("/text-not-received-2")
def textnotreceived2():
    return render_template('views/text-not-received-2.html')


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template('views/dashboard.html')


@main.route("/send-email")
def sendemail():
    return render_template('views/send-email.html')


@main.route("/check-email")
def checkemail():
    return render_template('views/check-email.html')


@main.route("/jobs")
def showjobs():
    return render_template('views/jobs.html')


@main.route("/jobs/job")
def showjob():
    return render_template('views/job.html')


@main.route("/jobs/job/notification")
def shownotification():
    return render_template('views/notification.html')


@main.route("/forgot-password")
def forgotpassword():
    return render_template('views/forgot-password.html')


@main.route("/new-password")
def newpassword():
    return render_template('views/new-password.html')


@main.route("/user-profile")
def userprofile():
    return render_template('views/user-profile.html')


@main.route("/manage-users")
def manageusers():
    return render_template('views/manage-users.html')


@main.route("/service-settings")
def servicesettings():
    return render_template('views/service-settings.html')


@main.route("/api-keys")
def apikeys():
    return render_template('views/api-keys.html')


@main.route("/verification-not-received")
def verificationnotreceived():
    return render_template('views/verification-not-received.html')


@main.route("/manage-templates")
def managetemplates():
    return render_template('views/manage-templates.html')


@main.route("/edit-template")
def edittemplate():
    return render_template('views/edit-template.html')
