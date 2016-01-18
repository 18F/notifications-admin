from flask import request, render_template, jsonify, redirect, session, url_for, abort
from flask_login import login_required
from app.main import main
from app.main.dao import services_dao, users_dao
from app.main.forms import AddServiceForm


@main.route("/add-service", methods=['GET', 'POST'])
@main.route("/add-service/<string:first>", methods=['GET', 'POST'])
@login_required
def add_service(first=False):
    if first:
        if first == 'first':
            heading = 'Set up notifications for your service'
        else:
            abort(404)
    else:
        heading = 'Add a new service'

    form = AddServiceForm(services_dao.find_all_service_names())
    if form.validate_on_submit():
        user = users_dao.get_user_by_id(session['user_id'])
        services_dao.insert_new_service(form.service_name.data, user)
        return redirect(url_for('.dashboard', service_id=123))
    else:
        return render_template(
            'views/add-service.html',
            form=form,
            heading=heading
        )
