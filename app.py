from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, send_file
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField,  RadioField, IntegerField, BooleanField
from wtforms.fields.html5 import DateField
import couchdb
from ldap3 import *
from passlib.hash import sha256_crypt
from functools import wraps
from fpdf import FPDF
import csv
import datetime
import pandas as pd

app = Flask(__name__)
#couch = couchdb.Server()
# Using Database
#db = couch['events']

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=5)


def authorizeCouch():
    couchserver = couchdb.Server("http://localhost:5984/")
    user = "admin"
    password = "admin"
    return couchdb.Server("http://%s:%s@localhost:5984/" % (user, password))

def dbCreate(dbname,couchserver):
    if dbname in couchserver:
        db = couchserver[dbname]
    else:
        db = couchserver.create(dbname)
    return db

couchserver = authorizeCouch()
db = dbCreate("events",couchserver)

def college_call():
    college_list = []
    for i in db:
        if (db[i]['type'] == 'admin_college_add'):
            college_list.append(db[i]['college_name'])
            college_list.append(db[i]['college_name'])
    college_list = iter(college_list)
    college_list = [(x, next(college_list)) for x in college_list]
    return college_list

def events_call():
    events_list = []
    for i in db:
        if (db[i]['type'] == 'event'):
            events_list.append(db[i]['event_name'])
            events_list.append(db[i]['event_name'])
    events_list = iter(events_list)
    events_list = [(x, next(events_list)) for x in events_list]
    return events_list

#test
@app.route('/test', methods=['GET', 'POST'])
def test():
    form = RegisterForm(request.form)
    return render_template('test.html', form=form)

# Index
@app.route('/')
def index():
    if 'logged_in' in session and session['logged_in'] == True:
        return render_template('home.html')
    return redirect(url_for('login'))


# About
@app.route('/about')
def about():
    return render_template('about.html')


# Events
@app.route('/events')
def events():
    det = []
    events = []
    for a in db:
        det.append(db[a])
    for a in range(len(det)):
        if det[a]['type'] == 'event':
            events.append(det[a])
    if len(events) > 0:
        return render_template('events.html', events=events)
    msg = 'No Events Found'
    return render_template('events.html', msg=msg)


# Single Event
@app.route('/event/<string:id>/')
def event(id):
    det = []
    event = []
    for a in db:
        det.append(db[a])
    for a in range(len(det)):
        if det[a]['type'] == 'event' and det[a]['_id'] == id:
            event.append(det[a])
    return render_template('event.html', event=event)


# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')



#Admin Page
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    form = EventForm(request.form)
    return render_template('admin.html')

#Add College
@app.route('/add_college', methods=['GET', 'POST'])
def addcollege():
    form = EventForm(request.form)
    if request.method == 'POST':
        college_name = form.college_name.data
        city = form.city.data
        for i in db:
            if db[i]['type']=='admin_college_add':
                if db[i]['college_name'] == college_name and db[i]['city'] == city:
                    flash('College Already Exists', 'danger')
                    return redirect(url_for('admin'))
        doc = {'college_name': college_name, 'city': city, 'type':'admin_college_add'}
        db.save(doc)

        flash('College added', 'success')
        return redirect(url_for('admin'))
    return render_template('add_college.html', form=form)


# Edit College
@app.route('/edit_college', methods=['GET', 'POST'])
def editcollege():
    college_list = []
    for i in db:
        if (db[i]['type'] == 'admin_college_add'):
            college_list.append(db[i])
    if request.method == 'GET':
        return render_template('edit_college.html', college_list=college_list)

# Delete College
@app.route('/delete_college/<string:id>', methods=['POST'])
def delete_college(id):
    doc = db[id]
    db.delete(doc)
    flash('College Deleted', 'success')
    return redirect(url_for('editcollege'))

#Edit College
@app.route('/edit_college/<string:id>', methods=['GET', 'POST'])
def edit_college1(id):
    form = EventForm(request.form)
    form.college_name.data = db[id]['college_name']
    form.city.data = db[id]['city']
    if request.method == 'POST':
        college_name = request.form['college_name']
        city = request.form['city']
        doc = db[id]
        doc['college_name'] = college_name
        doc['city'] = city
        for i in db:
            if db[i]['type']=='admin_college_add':
                if db[i]['college_name'] == college_name and db[i]['city'] == city:
                    flash('College Already Exists', 'danger')
                    return redirect(url_for('editcollege'))
        db.save(doc)
        flash('College Updated', 'info')
        return redirect(url_for('editcollege'))
    return render_template('update_college.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        POST_USERNAME = str(request.form['username'])
        POST_PASSWORD = str(request.form['password'])

        for i in db:
            if db[i]['type'] == 'user':
                if db[i]['username'] == POST_USERNAME:
                    session['logged_in'] = True
                    session['username'] = POST_USERNAME

                    # flash('You are now logged in', 'success')
                    return redirect(url_for('index'))


        server = Server('ldap://bluepages.ibm.com', get_info=ALL)
        c = Connection(server, user="", password="", raise_exceptions=False)
        noUseBool = c.bind()

        checkUserIBM = c.search(search_base='ou=bluepages,o=ibm.com',
                                search_filter='(mail=%s)' % (POST_USERNAME),
                                search_scope=SUBTREE,
                                attributes=['dn', 'givenName'])

        if (checkUserIBM == False):
            session['authorized'] = 0
            error = 'Invalid login'
            return render_template('login.html', error=error)

        # get the username of the emailID and authenticate password
        userName = c.entries[0].givenName[0]
        uniqueID = c.response[0]['dn']
        c2 = Connection(server, uniqueID, POST_PASSWORD)
        isPassword = c2.bind()

        if (isPassword == False):
            session['authorized'] = 0
            error = 'Invalid login'
            return render_template('login.html', error=error)

        # now search group
        checkIfAdminGroup = c.search(search_base='cn=RSC_B2B,ou=memberlist,ou=ibmgroups,o=ibm.com',
                                     search_filter='(uniquemember=%s)' % (str(uniqueID)),
                                     search_scope=SUBTREE,
                                     attributes=['dn'])

        if (checkIfAdminGroup == False):
            session['authorized'] = 0
            error = 'Invalid login'
            return render_template('login.html', error=error)

        # control reaches here if user password and group authentication is successful

        session['logged_in'] = True
        session['username'] = userName

        #flash('You are now logged in', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    session['logged_in'] = False
    flash('You have logged out', 'success')
    return redirect(url_for('login'))


# DateSubmit`
@app.route('/datesubmit')
@is_logged_in
def datesubmit():
    form = EventForm(request.form)


# Dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
@is_logged_in
def dashboard():
    event_type_list = ['event', 'tech Session', 'Hackathon']
    form = EventForm(request.form)
    if request.method == 'POST':
        fromdate = str(form.fromdate.data)
        todate = str(form.todate.data)
        event_type = form.event_types.data
        print(event_type)
        print(fromdate)
        print(todate)
        if(fromdate==None):
            det = []
            events = []
            for a in db:
                det.append(db[a])
            for a in range(len(det)):
                if det[a]['type'] in event_type_list:
                    events.append(det[a])
            if len(events) > 0:
                return render_template('dashboard.html', events=events, form=form)
            else:
                msg = 'No Events Found'
                return render_template('dashboard.html', msg=msg, form=form)
        det = []
        events = []
        for a in db:
            det.append(db[a])
        for a in range(len(det)):
            if det[a]['type'] == 'SUR' and fromdate <= det[a]['proposal_submission_date'] <= todate:
                events.append(det[a])
            if det[a]['type'] in event_type_list and fromdate <= det[a]['startdate'] <= todate:
                events.append(det[a])
        if len(events)>0:
            return render_template('dashboard.html', events=events, form = form)
        else:
            msg = 'No Events Found'
            return render_template('dashboard.html', msg=msg, form=form)
    det = []
    events = []
    event_type_list.append('SUR')
    for a in db:
        det.append(db[a])
    for a in range(len(det)):
        if det[a]['type'] in event_type_list:
        # if det[a]['type'] == 'event' and det[a]['username'] == session['username']:
            events.append(det[a])
    if len(events) > 0:
        return render_template('dashboard.html', events=events, form=form)
    else:
        msg = 'No Events Found'
        return render_template('dashboard.html', msg=msg, form=form)


# Event Form Class
class EventForm(Form):
    events = SelectField('Events', choices=[("Technical Fest","Technical Fest"), ("Conference","Conference"),  ("Tech Session", "Tech Session"), ("Tech Workshop", "Tech Workshop"), ("Hackathon", "Hackathon"), ("SUR", "SUR")])
    event_name = StringField('Event Name', [validators.Length(min=1, max=200), validators.DataRequired()])
    tech_session_name = StringField('Tech Session / Workshop name', [validators.Length(min=1, max=200), validators.DataRequired()])
    ibm_sme_name = StringField('IBM SME Name',[validators.Length(min=1, max=200), validators.DataRequired()])
    bu = SelectField(
        'BU',
        choices=[('ISL', 'ISL'), ('IRL', 'IRL'), ('GBS', 'GBS'),('GTS', 'GTS')])
    box_location_atten = StringField('Box location for Attendee list', [validators.Length(min=1, max=500), validators.DataRequired()])
    box_location_feed = StringField('Box location for Feedback',[validators.Length(min=1, max=500), validators.DataRequired()])
    box_location_winning_profile = StringField('Box location for Winning team profiles',[validators.Length(min=1, max=500), validators.DataRequired()])
    sponsorship_amount = StringField('Sponsorship Amount', [validators.Length(min=5, max=500), validators.DataRequired()],default='INR  ')

    hackathon_name = StringField('Hackathon Name', [validators.Length(min=1, max=200), validators.DataRequired()])
    college = SelectField('College',[validators.DataRequired()], choices=[])
    college_name = StringField('College Name', [validators.Length(min=3), validators.DataRequired()])
    city = SelectField('city', choices=[("Bangalore","Bangalore"), ("C2","C2"),("Chennai","Chennai")])
    no_of_participants = IntegerField('No of participants', [validators.NumberRange(min=1), validators.DataRequired()])
    no_of_registrations = IntegerField('No of registrations', [validators.NumberRange(min=1), validators.DataRequired()])
    no_of_abstracts = IntegerField('No of abstracts shortlisted',[validators.NumberRange(min=1), validators.DataRequired()])
    no_of_finalist = IntegerField('No of Finalist',
                                   [validators.NumberRange(min=1), validators.DataRequired()])
    finaledate = DateField('Finale Date', [validators.DataRequired()], default=datetime.date.today, format='%Y-%m-%d')
    jury_name = StringField('Jury', [validators.Length(min=1, max=200), validators.DataRequired()])
    additional_jury_name = StringField('Additional Jury', [validators.Length(min=1, max=200)])
    winning_team_details = StringField('Winning Team Details', [validators.Length(min=1, max=200), validators.DataRequired()])
    runnerup_team_details = StringField('Runner-Up Team Details',
                                       [validators.Length(min=1, max=200), validators.DataRequired()])
    startdate = DateField('Start Date', [validators.DataRequired()], default = datetime.date.today, format='%Y-%m-%d')
    enddate = DateField('End Date', [validators.DataRequired()], default = datetime.date.today, format='%Y-%m-%d')
    project_startdate = DateField('Project Start Date', [validators.DataRequired()], default=datetime.date.today, format='%Y-%m-%d')
    project_enddate = DateField('Project End Date', [validators.DataRequired()], default=datetime.date.today, format='%Y-%m-%d')
    fromdate = DateField('From Date',default = datetime.date.today, format='%Y-%m-%d')
    todate = DateField('To Date', default = datetime.date.today, format='%Y-%m-%d')
    status = RadioField('Status', [validators.DataRequired()], choices= [('Planned', 'Planned'), ('In Progress', 'In Progress'),('Completed','Completed')],default='Planned')
    list_of_events  = SelectField('List of Events', choices=[])
    theme  = SelectField('Theme',[validators.DataRequired()], choices=[('AI', 'AI'), ('Blockchain', 'Blockchain'), ('Cloud', 'Cloud'), ('Security', 'Security'), ('Project Management', 'Project Management'), ('Others', 'Others')])
    topic = StringField('Topic', [validators.Length(min=3), validators.DataRequired()])
    name_of_participants = StringField('Name of Participants. Separate using ;', [validators.Length(min=3), validators.DataRequired()])
    sur_topic_name = StringField('SUR Topic Name', [validators.Length(min=3), validators.DataRequired()])
    prof_name = StringField('Professor Name', [validators.Length(min=3), validators.DataRequired()])
    technology = StringField('Technology', [validators.Length(min=3), validators.DataRequired()])
    proposal_receipt_date = DateField('Proposal Receipt date',default = datetime.date.today, format='%Y-%m-%d')
    proposal_submission_date = DateField('Proposal Submission date',default = datetime.date.today, format='%Y-%m-%d')
    proposal_status = RadioField('Proposal Status', [validators.DataRequired()], choices=[('Approved', 'Approved'), ('Rejected', 'Rejected')],
                        default='Rejected')
    invoice_receipt_date = DateField('Invoice receipt date',default = datetime.date.today, format='%Y-%m-%d')
    invoice_payout_date = DateField('Invoice payout date', default = datetime.date.today, format='%Y-%m-%d')
    paper_publications = StringField('Paper publications', [validators.Length(min=3)])
    type_of_event = StringField('Event type')
    conference_showcase = StringField('Conference showcase', [validators.Length(min=3)])
    sur_proposal_location = StringField('SUR Proposal Location ', [validators.Length(min=3), validators.DataRequired()])
    project_url = StringField('Project URL', [validators.Length(min=3), validators.DataRequired()])
    event_types = SelectField(
        'Event Type',
        choices=[('event', 'Technical Fest'), ('tech Session', 'Tech Session'), ('Hackathon', 'Hackathon'),('SUR', 'SUR')])


    requestor = StringField('Requestor Name', [validators.Length(min=3), validators.DataRequired()])
    destination = StringField('Destination/s', [validators.Length(min=3), validators.DataRequired()])
    amount_k = StringField('Amount (US $ K)',
                                     [validators.Length(min=5, max=500), validators.DataRequired()], default='$  ')
    travel_date = DateField('Travel date', default=datetime.date.today, format='%Y-%m-%d')
    amount_m = StringField('Amount (US $ M)',
                           [validators.Length(min=5, max=500), validators.DataRequired()], default='$  ')
    po_date = DateField('PO date', default=datetime.date.today, format='%Y-%m-%d')
    submited_finance_date = DateField('Date Submitted to Finance', default=datetime.date.today, format='%Y-%m-%d')
    finance_status = RadioField('Finance Status', [validators.DataRequired()],
                                 choices=[('Approved', 'Approved'), ('Rejected', 'Rejected')],
                                 default='Rejected')
    travel_request = BooleanField('Travel Request')
    po_request = BooleanField('PO Request')


    def validate_on_submit(self):
        if self.startdate.data > self.enddate.data:
            return False
        else:
            return True

    def validate_on_submit_sur(self):
        if self.proposal_receipt_date.data > self.proposal_submission_date.data and self.invoice_receipt_date.data > self.invoice_payout_date.data:
            return False
        else:
            return True
    ##{{% %}}##



# city = SelectField('city', choices=[])
# college = SelectField('College', choices=[("Col1","Col1"), ("Col2","Col2"),  ("Col3", "Col3"), ("Col4", "Col4"), ("Col5", "Col5"), ("Col6", "Col6")])
# ("Technical Fest","Technical Fest"), ("Conference","Conference"),  ("Tech Session","Tech Session"), ("Tech Workshop", "Tech Workshop"), ("Hackathon", "Hackathon"),("SUR","SUR")

# Add Event
@app.route('/add_event', methods=['GET', 'POST'])
@is_logged_in
def add_event():
    form = EventForm(request.form)
    form.college.choices = college_call()
    form.list_of_events.choices = events_call()
    error = None
    if request.method == 'POST':
        event_name = form.event_name.data
        college = form.college.data
        # no_of_participants = form.no_of_participants.data
        # startdate = str(form.startdate.data)
        # enddate = str(form.enddate.data)
        if form.validate_on_submit()==True:
            no_of_participants = str(form.no_of_participants.data)
            status = form.status.data
            startdate = str(form.startdate.data)
            enddate = str(form.enddate.data)
            sponsorship_amount = form.sponsorship_amount.data
            topic = form.topic.data
            doc = {'username': session['username'], 'event_name': event_name, 'college': college,
                   'no_of_participants': no_of_participants, 'enddate': enddate, 'startdate': startdate,
                   'status': status, 'sponsorship_amount': sponsorship_amount, 'topic':topic, 'type': 'event'}
            db.save(doc)
            flash('Event Created', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = "Start date is greater than End date"
        return render_template('add_event.html', form=form, error=error)


    return render_template('add_event.html', form=form)


@app.route('/sme_details', methods=['GET', 'POST'])
@is_logged_in
def sme_details():
    form = EventForm(request.form)
    form.college.choices = college_call()
    error = None
    if request.method == 'POST':
        event_name = form.event_name.data
        college = form.college.data
        # no_of_participants = form.no_of_participants.data
        # startdate = str(form.startdate.data)
        # enddate = str(form.enddate.data)
        if form.validate_on_submit()==True:
            no_of_participants = str(form.no_of_participants.data)
            status = form.status.data
            startdate = str(form.startdate.data)
            enddate = str(form.enddate.data)
            sponsorship_amount = form.sponsorship_amount.data
            topic = form.topic.data
            doc = {'username': session['username'], 'event_name': event_name, 'college': college,
                   'no_of_participants': no_of_participants, 'enddate': enddate, 'startdate': startdate,
                   'status': status, 'sponsorship_amount': sponsorship_amount, 'topic':topic, 'type': 'event'}
            db.save(doc)
            flash('Event Created', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = "Start date is greater than End date"
        return render_template('sme_details.html', form=form, error=error)


    return render_template('sme_details.html', form=form)


@app.route('/sur_event', methods=['GET', 'POST'])
@is_logged_in
def sur_event():
    form = EventForm(request.form)
    if request.method == 'POST':
        sur_topic_name = form.sur_topic_name.data
        prof_name = request.form.getlist('prof_name')
        print(prof_name)
        technology = form.technology.data
        print(technology)
        if form.validate_on_submit_sur()==True:
            proposal_receipt_date = str(form.proposal_receipt_date.data)
            proposal_submission_date = str(form.proposal_submission_date.data)
            project_startdate = str(form.project_startdate.data)
            project_enddate = str(form.project_enddate.data)
            proposal_status = request.form['status']
            print(proposal_status)
            if proposal_status == 'Approved':
                invoice_receipt_date = str(form.invoice_receipt_date.data)
                invoice_payout_date = str(form.invoice_payout_date.data)
                paper_publications = form.paper_publications.data
                conference_show = form.conference_showcase.data
            else:
                invoice_receipt_date = ''
                invoice_payout_date = ''
                paper_publications = ''
                conference_show = ''
            sur_proposal_location = form.sur_proposal_location.data
            project_url = form.project_url.data
            doc = {'username': session['username'], 'sur_topic_name': sur_topic_name, 'professor_Name': prof_name,
                   'Technology': technology, 'proposal_receipt_date': proposal_receipt_date, 'proposal_submission_date': proposal_submission_date,
                   'project_startdate':project_startdate,'project_enddate' : project_enddate,
                   'proposal_status': proposal_status, 'invoice_receipt_date': invoice_receipt_date, 'invoice_payout_date':invoice_payout_date, 'paper_publications': paper_publications,
                   'conference_show': conference_show,'sur_proposal_location':sur_proposal_location,
                   'project_url': project_url, 'type': 'SUR'}
            db.save(doc)
            flash('SUR Created', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = "Start date is greater than End date"
        return render_template('add_event.html', form=form, error=error)


    return render_template('add_event.html', form=form)


@app.route('/tech_session', methods=['GET', 'POST'])
@is_logged_in
def tech_session():
    form = EventForm(request.form)
    form.college.choices = college_call()
    form.list_of_events.choices = events_call()
    error = None
    if request.method == 'POST':
        event_name = form.tech_session_name.data
        college = form.college.data
        list_of_events = form.list_of_events.data
        no_of_participants = str(form.no_of_participants.data)
        startdate = str(form.startdate.data)
        status = form.status.data
        enddate = str(form.enddate.data)
        technology = form.technology.data
        bu = form.bu.data
        ibm_sme_name = form.ibm_sme_name.data
        box_location_atten = form.box_location_atten.data
        box_location_feed = form.box_location_feed.data
        box_location_winning_profile = form.box_location_winning_profile.data
        doc = {'username': session['username'], 'event_name': event_name,'main_event':list_of_events, 'college': college,
               'no_of_participants': no_of_participants,'startdate': startdate,'enddate': enddate,'technology':technology,
               'bu' : bu, 'status':status, 'ibm_sme_name' : ibm_sme_name, 'box_location_atten' : box_location_atten,'box_location_winning_profile':box_location_winning_profile,
               'box_location_feed' : box_location_feed,
               'type': 'tech Session'}
        db.save(doc)
        flash('Event Created', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_event.html', form=form)

@app.route('/hackathon', methods=['GET', 'POST'])
@is_logged_in
def hackathon():
    form = EventForm(request.form)
    form.college.choices = college_call()
    form.list_of_events.choices = events_call()
    error = None
    if request.method == 'POST':
        hackathon_name = form.hackathon_name.data
        college = form.college.data
        list_of_events = form.list_of_events.data
        no_of_participants = str(form.no_of_participants.data)
        if form.validate_on_submit() == True:
            startdate = str(form.startdate.data)
            enddate = str(form.enddate.data)
            technology = form.technology.data
            no_of_registrations = form.no_of_registrations.data
            no_of_abstracts = form.no_of_abstracts.data
            no_of_finalist = form.no_of_finalist.data
            finaledate = str(form.finaledate.data)
            jury = request.form.getlist('jury_name')
            bu = request.form.getlist('bu')
            list_ibm_jury = [x for x in zip(jury,bu)]
            status = form.status.data
            additional_jury = form.additional_jury_name.data
            winning_team_details = form.winning_team_details.data
            runnerup_team_details = form.runnerup_team_details.data
            winning_team_profiles = form.box_location_winning_profile.data
            doc = {'username': session['username'], 'Hackathon_name': hackathon_name,'main_event':list_of_events, 'college': college,
                   'no_of_participants': no_of_participants,'no_of_registrations': no_of_registrations,'status':status, 'additional_jury':additional_jury,
                   'no_of_abstracts': no_of_abstracts, 'no_of_finalist': no_of_finalist,
                   'startdate': startdate,'enddate': enddate,'finaledate': finaledate,'technology':technology,
                   'jury' : list_ibm_jury, 'winning_team_details' : winning_team_details, 'runnerup_team_details' : runnerup_team_details,
                   'winning_team_profiles':winning_team_profiles,'type': 'Hackathon'}
            db.save(doc)
            flash('Event Created', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = "Start date is greater than End date"
        return render_template('add_event.html', form=form, error=error)

    return render_template('add_event.html', form=form)

# Edit Event
@app.route('/edit_event/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_event(id):
    form = EventForm(request.form)
    print(db[id]['type'])
    if db[id]['type'] == 'SUR':
        form.sur_topic_name.data = db[id]['sur_topic_name']
        form.prof_name.data = db[id]['professor_Name']
        form.technology.data =  db[id]['Technology']
        form.proposal_receipt_date.data = datetime.datetime.strptime(db[id]['proposal_receipt_date'].replace('-', ''), "%Y%m%d")
        print(form.proposal_receipt_date.data)
        form.proposal_submission_date.data = datetime.datetime.strptime(db[id]['proposal_submission_date'].replace('-', ''),
                                                                     "%Y%m%d")
        form.project_startdate.data = datetime.datetime.strptime(db[id]['project_startdate'].replace('-', ''),
                                                                     "%Y%m%d")
        form.project_enddate.data = datetime.datetime.strptime(db[id]['project_enddate'].replace('-', ''),"%Y%m%d")

        if db[id]['invoice_receipt_date'] != '':
            form.invoice_receipt_date.data = datetime.datetime.strptime(db[id]['invoice_receipt_date'].replace('-', ''), "%Y%m%d")
            form.invoice_payout_date.data = datetime.datetime.strptime(db[id]['invoice_payout_date'].replace('-', ''), "%Y%m%d")
        form.paper_publications.data = db[id]['paper_publications']
        form.conference_showcase.data = db[id]['conference_show']
        form.sur_proposal_location.data = db[id]['sur_proposal_location']
        form.project_url.data = db[id]['project_url']
        form.type_of_event.data = 'SUR'
        if request.method == 'POST':
            doc = db[id]
            doc['sur_topic_name'] = request.form['sur_topic_name']
            doc['professor_Name'] = request.form['prof_name']
            doc['technology'] = request.form['technology']
            if form.validate_on_submit() == True:
                print("I am in")
                proposal_status = request.form['status']
                print(proposal_status)
                if proposal_status == 'Approved':
                    doc['invoice_receipt_date'] = request.form['invoice_receipt_date']
                    doc['invoice_payout_date'] = request.form['invoice_payout_date']
                    doc['paper_publications'] = request.form['paper_publications']
                    doc['conference_show'] = request.form['conference_showcase']
                else:
                    doc['invoice_receipt_date'] = ''
                    doc['invoice_payout_date'] = ''
                    doc['paper_publications'] = ''
                    doc['conference_show'] = ''
                doc['proposal_receipt_date'] = request.form['proposal_receipt_date']
                doc['proposal_submission_date'] = request.form['proposal_submission_date']
                doc['project_startdate'] = request.form['project_startdate']
                doc['project_enddate'] = request.form['project_enddate']
                doc['proposal_status'] = request.form['status']

                doc['sur_proposal_location'] = request.form['sur_proposal_location']
                doc['project_url'] = request.form['project_url']
                db.save(doc)
                print(doc)
                flash('Event Updated', 'info')

                return redirect(url_for('dashboard'))


    elif db[id]['type'] == 'Hackathon':
        form.hackathon_name.data = db[id]['Hackathon_name']
        form.college.data = db[id]['college']
        form.college.choices = college_call()
        form.list_of_events.data = db[id]['main_event']
        form.list_of_events.choices = events_call()
        form.no_of_participants.data = db[id]['no_of_participants']
        form.no_of_registrations.data = db[id]['no_of_registrations']
        form.no_of_abstracts.data = db[id]['no_of_abstracts']
        form.no_of_finalist.data = db[id]['no_of_finalist']
        form.startdate.data = datetime.datetime.strptime(db[id]['startdate'].replace('-', ''),"%Y%m%d")
        form.enddate.data = datetime.datetime.strptime(db[id]['enddate'].replace('-', ''),"%Y%m%d")
        form.finaledate.data = datetime.datetime.strptime(db[id]['finaledate'].replace('-', ''),"%Y%m%d")
        form.technology.data = db[id]['technology']
        form.jury_name.data = db[id]['jury']
        form.additional_jury_name.data = db[id]['additional_jury']
        form.status.data = db[id]['status']
        form.winning_team_details.data = db[id]['winning_team_details']
        form.runnerup_team_details.data = db[id]['runnerup_team_details']
        form.box_location_winning_profile.data = db[id]['winning_team_profiles']
        form.type_of_event.data = 'Hackathon'
        if request.method == 'POST':
            doc = db[id]
            doc['Hackathon_name'] = request.form['hackathon_name']
            doc['college'] = request.form['college']
            doc['main_event'] = request.form['list_of_events']
            doc['no_of_participants'] = request.form['no_of_participants']
            if form.validate_on_submit() == True:
                print("I am in")
                doc['no_of_registrations'] = request.form['no_of_registrations']
                doc['no_of_abstracts'] = request.form['no_of_abstracts']
                doc['no_of_finalist'] = request.form['no_of_finalist']
                doc['startdate'] = request.form['startdate']
                doc['enddate'] = request.form['enddate']
                doc['finaledate'] = request.form['finaledate']
                doc['status'] = request.form['status']
                doc['technology'] = request.form['technology']
                doc['jury'] = request.form['jury_name']
                doc['additional_jury'] = request.form['additional_jury_name']
                doc['winning_team_details'] = request.form['winning_team_details']
                doc['runnerup_team_details'] = request.form['runnerup_team_details']
                doc['winning_team_profiles'] = request.form['box_location_winning_profile']
                db.save(doc)
                print(doc)
                flash('Event Updated', 'info')

                return redirect(url_for('dashboard'))


    elif db[id]['type'] == 'tech Session':
        form.tech_session_name.data = db[id]['event_name']
        form.college.data = db[id]['college']
        form.college.choices = college_call()
        form.list_of_events.data = db[id]['main_event']
        form.list_of_events.choices = events_call()
        form.no_of_participants.data = db[id]['no_of_participants']
        form.startdate.data = datetime.datetime.strptime(db[id]['startdate'].replace('-', ''),
                                                                    "%Y%m%d")
        form.enddate.data = datetime.datetime.strptime(db[id]['enddate'].replace('-', ''),
                                                         "%Y%m%d")
        form.technology.data = db[id]['technology']
        form.bu.data = db[id]['bu']
        form.status.data = db[id]['status']
        form.ibm_sme_name.data = db[id]['ibm_sme_name']
        form.box_location_atten.data = db[id]['box_location_atten']
        form.box_location_feed.data = db[id]['box_location_feed']
        form.type_of_event.data = 'tech_session'
        if request.method == 'POST':
            doc = db[id]
            doc['event_name'] = request.form['tech_session_name']
            doc['college'] = request.form['college']
            doc['main_event'] = request.form['list_of_events']
            doc['no_of_participants'] = request.form['no_of_participants']
            if form.validate_on_submit() == True:
                doc['startdate'] = request.form['startdate']
                doc['enddate'] = request.form['enddate']
                doc['status'] = request.form['status']
                doc['ibm_sme_name'] = request.form['ibm_sme_name']
                doc['technology'] = request.form['technology']
                doc['bu'] = request.form['bu']
                doc['box_location_atten'] = request.form['box_location_atten']
                doc['box_location_feed'] = request.form['box_location_feed']
                db.save(doc)
                print(doc)
                flash('Event Updated', 'info')

                return redirect(url_for('dashboard'))
            else:
                error = "Start date is greater than End date"
            return render_template('add_event.html', form=form, error=error)
    else:
        result = db[id]
        form = EventForm(request.form)
        form.event_name.data = db[id]['event_name']
        form.sponsorship_amount.data = db[id]['sponsorship_amount']
        form.college.data = db[id]['college']
        form.college.choices = college_call()
        form.no_of_participants.data = db[id]['no_of_participants']
        t = db[id]['startdate']
        t = t.replace('-', '')
        s = datetime.datetime.strptime(t, "%Y%m%d")
        form.startdate.data = s
        t = db[id]['enddate']
        t = t.replace('-', '')
        s = datetime.datetime.strptime(t, "%Y%m%d")
        form.enddate.data = s
        form.status.data = db[id]['status']
        form.type_of_event.data = 'event'
        if request.method == 'POST':
            event_name = request.form['event_name']
            sponsorship_amount = request.form['sponsorship_amount']
            college = request.form['college']
            no_of_participants = request.form['no_of_participants']
            startdate = request.form['startdate']
            enddate = request.form['enddate']
            status = request.form['status']

            doc = db[id]
            doc['event_name'] = event_name
            doc['sponsorship_amount'] =sponsorship_amount
            doc['college'] = college
            doc['no_of_participants'] = no_of_participants
            doc['startdate'] = startdate
            doc['enddate'] = enddate
            doc['status'] = status
            db.save(doc)
            flash('Event Updated', 'info')

            return redirect(url_for('dashboard'))


    return render_template('edit_event.html', form=form)
# first get doc by id, save to formal parameter, delete doc with id,, store new doc in db
# import couchdb
# couch = couchdb.Server()
# # Using Database
# db = couch['events']
# doc = db["fc32db1cf373a40ce6fc2cca8a007d71"]
# doc['username']='tt'
# db.save(doc)


# Delete Event
@app.route('/delete_event/<string:id>', methods=['POST'])
@is_logged_in
def delete_event(id):
    doc = db[id]
    db.delete(doc)
    flash('Event Deleted', 'success')
    return redirect(url_for('dashboard'))


# Download Event
@app.route('/downloadpdf', methods=['GET'])
def download():
    pdf = FPDF()
    c = {}
    a = []
    pdf.add_page()
    pdf.set_font("Arial", size=5)
    i = int(1)
    for i in db:
        c = {}
        if db[i]['type'] == 'event':
            for j in db[i]:
                # print(j,db[i][j])
                c[j] = db[i][j]
            del c['_id']
            del c['_rev']
            del c['topic']
            # pdf.cell(200, 10, txt=str(c), ln=1, align="L")
            a.append(c)
    m = []
    data = [['event_name', 'college', 'no_of_participants', 'enddate', 'startdate', 'status', 'theme', 'topic']]
    for i in a:
        for j in i:
            m.append(i[j])
        data.append(m)
        m = []

    col_width = pdf.w / 10.5
    row_height = pdf.font_size
    spacing = 1
    for row in data:
        for item in row:
            pdf.cell(col_width, row_height * spacing,
                     txt=item, border=1)
        pdf.ln(row_height * spacing)
        #     print(item, end = " ")
        # print()

    pdf.output('Events.pdf')
    path = "Events.pdf"
    return send_file(path, as_attachment=True)


@app.route('/downloadexcel', methods=['GET'])
def downloadexcel():
    events = []
    sur = []
    tech_session = []
    hackathon = []
    for i in db:
        c = {}
        if db[i]['type'] == 'event':
            for j in db[i]:
                c[j] = db[i][j]
            del c['_id']
            del c['_rev']
            del c['topic']
            events.append(c)
        elif db[i]['type'] == 'SUR':
            for j in db[i]:
                c[j] = db[i][j]
            del c['_id']
            del c['_rev']
            sur.append(c)
        elif db[i]['type'] == 'tech Session':
            for j in db[i]:
                c[j] = db[i][j]
            del c['_id']
            del c['_rev']
            tech_session.append(c)
        elif db[i]['type'] == 'Hackathon':
            for j in db[i]:
                c[j] = db[i][j]
            del c['_id']
            del c['_rev']
            hackathon.append(c)


    m_event = {}
    m_sur = {}
    m_techSession = {}
    m_hackathon = {}
    header_event = ['event_name', 'college', 'no_of_participants', 'enddate', 'startdate', 'status', 'sponsorship_amount']
    header_techSession = ['main_event','event_name','college','no_of_participants','status','startdate','enddate','technology','bu','ibm_sme_name','box_location_atten','box_location_feed']
    header_hackathon = ['main_event','Hackathon_name','college','no_of_participants','no_of_registrations','no_of_abstracts','no_of_finalist'
                        ,'startdate','enddate', 'finaledate', 'technology','jury','status','additional_jury','winning_team_details', 'runnerup_team_details','winning_team_profiles']
    header_sur = ['sur_topic_name', 'professor_Name','Technology', 'proposal_receipt_date','proposal_submission_date','project_startdate','project_enddate',
     'proposal_status', 'invoice_receipt_date','invoice_payout_date', 'paper_publications','conference_show', 'sur_proposal_location','project_url']


    for i in header_event:
        m_event[i] = [events[j][i] for j in range(len(events))]
    for i in header_techSession:
        m_techSession[i] = [tech_session[j][i] for j in range(len(tech_session))]
    for i in header_hackathon:
        m_hackathon[i] = [hackathon[j][i] for j in range(len(hackathon))]
    for i in header_sur:
        m_sur[i] = [sur[j][i] for j in range(len(sur))]

    print(m_event)
    df_event = pd.DataFrame(m_event)
    df_techSession = pd.DataFrame(m_techSession)
    df_hacathon = pd.DataFrame(m_hackathon)
    df_sur = pd.DataFrame(m_sur)


    writer = pd.ExcelWriter('Event.xlsx', engine='xlsxwriter')

    df_event.to_excel(writer, sheet_name='Main event')
    df_hacathon.to_excel(writer,sheet_name='Hackathon')
    df_techSession.to_excel(writer, sheet_name='Tech Session')
    df_sur.to_excel(writer, sheet_name='SUR')

    writer.save()
    path = "Event.xlsx"
    return send_file(path, as_attachment=True)


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(host='0.0.0.0',port=2222,debug=True)
