[![Build Status](https://api.travis-ci.org/alphagov/notifications-admin.svg?branch=master)](https://api.travis-ci.org/alphagov/notifications-admin.svg?branch=master)


# notifications-admin
Application to handle the admin functions of the notifications application.

### Features of this application:
<ul>
 <li>Register users
 <li>Register services
 <li>Download CSV for an email or sms batch
 <li>Show history of notifications
 <li>Reports
</ul>

### Create a virtual environment for this project
    mkvirtualenv -p /usr/local/bin/python3 notifications-admin 
 

### GOV.UK frontend toolkit
 The GOV.UK frontend toolkit is a submodule of this project.
 To get the content of the toolkit run the following two commands
 
    git submodule init
    git submodule update

### Running the application:
    pip install -r requirements.txt
    ./scripts/bootstrap.sh  
    ./scripts/run_app.sh

Note: the ./scripts/bootstrap.sh script only needs to be run the first time to create the database.

 url to test app: 
 
    localhost:6012/helloworld


### Domain model

All the domain models are defined in the [models.py](https://github.com/alphagov/notifications-admin/blob/master/app/models.py) file.




