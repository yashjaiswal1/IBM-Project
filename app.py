from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, send_file
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField,  RadioField, IntegerField, BooleanField
from wtforms.fields.html5 import DateField
import couchdb
import xlsxwriter
from ldap3 import *
from passlib.hash import sha256_crypt
from functools import wraps
from fpdf import FPDF
import csv
import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = 'secret123'
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

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session['logged_in'] == True:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


#test
@app.route('/test', methods=['GET', 'POST'])
def test():
    form = RegisterForm(request.form)
    return render_template('test.html', form=form)

# Index
@app.route('/')
@is_logged_in
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
@is_logged_in
def admin():
    form = EventForm(request.form)
    return render_template('admin.html')

#Add College
@app.route('/add_college', methods=['GET', 'POST'])
@is_logged_in
def addcollege():
    form = EventForm(request.form)
    if request.method == 'POST':
        college_name = form.college_name.data
        college_category = form.college_category.data
        ur_spoc = form.ur_spoc.data
        city = form.city.data
        region = form.region.data
        for i in db:
            if db[i]['type']=='admin_college_add':
                if db[i]['college_name'] == college_name and db[i]['college_category'] == college_category and db[i]['city'] == city:
                    flash('College Already Exists', 'danger')
                    return redirect(url_for('admin'))
        doc = {'college_name': college_name, 'college_category': college_category, 'ur_spoc': ur_spoc, 'city': city, 'region': region, 'type':'admin_college_add'}
        db.save(doc)

        flash('College added', 'success')
        return redirect(url_for('admin'))
    return render_template('add_college.html', form=form)


# Edit College
@app.route('/edit_college', methods=['GET', 'POST'])
@is_logged_in
def editcollege():
    college_list = []
    for i in db:
        if (db[i]['type'] == 'admin_college_add'):
            college_list.append(db[i])
    if request.method == 'GET':
        return render_template('edit_college.html', college_list=college_list)

# Delete College
@app.route('/delete_college/<string:id>', methods=['POST'])
@is_logged_in
def delete_college(id):
    doc = db[id]
    db.delete(doc)
    flash('College Deleted', 'success')
    return redirect(url_for('editcollege'))

#Edit College
@app.route('/edit_college/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_college1(id):
    form = EventForm(request.form)
    form.college_name.data = db[id]['college_name']
    form.college_category.data = db[id]['college_category']
    form.ur_spoc.data = db[id]['ur_spoc']
    form.city.data = db[id]['city']
    form.region.data = db[id]['region']
    if request.method == 'POST':
        college_name = request.form['college_name']
        college_category = request.form['college_category']
        ur_spoc = request.form['ur_spoc']
        city = request.form['city']
        region = request.form['region']
        doc = db[id]
        doc['college_name'] = college_name
        doc['college_category'] = college_category
        doc['ur_spoc'] = ur_spoc
        doc['city'] = city
        doc['region'] = region
        for i in db:
            if db[i]['type']=='admin_college_add':
                if db[i]['college_name'] == college_name and db[i]['college_category'] == college_category and db[i]['city'] == city and db[i]['ur_spoc'] == ur_spoc and db[i]['region'] == region:
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
                if db[i]['username'] == POST_USERNAME and db[i]['password'] == POST_PASSWORD:
                    session['logged_in'] = True
                    session['username'] = POST_USERNAME

                    # flash('You are now logged in', 'success')
                    return redirect(url_for('index'))
                else:
                    error = 'Invalid login'
                    session['logged_in'] = False
                    return render_template('login.html', error=error)


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
        if (fromdate > todate):
            flash('From Date cannot be greater than To Date', 'danger')
            return redirect(url_for('dashboard'))
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
    tech_session_name = StringField('Tech Session / Workshop Name', [validators.Length(min=1, max=200), validators.DataRequired()])
    ibm_sme_name = StringField('IBM SME Name',[validators.Length(min=1, max=200), validators.DataRequired()])
    bu = SelectField(
        'BU',
        choices=[('ISL', 'ISL'), ('IRL', 'IRL'), ('GBS', 'GBS'),('GTS', 'GTS')])
    box_location_atten = StringField('Box location for Attendee list', [validators.Length(min=1, max=500), validators.DataRequired()])
    box_location_feed = StringField('Box location for Feedback',[validators.Length(min=1, max=500), validators.DataRequired()])
    box_location_winning_profile = StringField('Box location for Winning team profiles',[validators.Length(min=1, max=500), validators.DataRequired()])
    sponsorship_amount = StringField('Sponsorship Amount', [validators.Length(min=5, max=500), validators.DataRequired()], render_kw={"placeholder": "INR"})

    hackathon_name = StringField('Hackathon Name', [validators.Length(min=1, max=200), validators.DataRequired()])
    
    #----------tech workshop---------
    institution = StringField('Institution',[validators.Length(min=1),validators.DataRequired()])
    tech_area = StringField('Technology', [validators.Length(min=1), validators.DataRequired()])
    no_of_sessions = StringField('Number of sessions', [validators.Length(min=1), validators.DataRequired()])
    # no_of_attendees = IntegerField('Number of attendees', [validators.Length(min=1), validators.DataRequired()])
    event_posted = RadioField('Event posted on portal', [validators.DataRequired()], choices= [('Yes', 'Yes'), ('No', 'No')])
    event_socialising = RadioField('Post event socialising?', [validators.DataRequired()], choices= [('Yes', 'Yes'), ('No', 'No')])
    comments = TextAreaField('Comments',default='None')
    #-----------END of TECH FEST------------------------

    #----------Hackathon---------
    # First Prize Winners
    team_name1 = StringField('Team Name', [validators.Length(min=1), validators.DataRequired()])
    team_member_name1 = StringField('Member Name', [validators.Length(min=1), validators.DataRequired()])
    team_member_college1 = StringField('College', [validators.Length(min=1), validators.DataRequired()])

    # Second Prize Winners
    team_name2 = StringField('Team Name', [validators.Length(min=1)])
    team_member_name2 = StringField('Member Name', [validators.Length(min=1)])
    team_member_college2 = StringField('College', [validators.Length(min=1)])

    # Third Prize Winners
    team_name3 = StringField('Team Name', [validators.Length(min=1)])
    team_member_name3 = StringField('Member Name', [validators.Length(min=1)])
    team_member_college3 = StringField('College', [validators.Length(min=1)])
    #----------END---------

    college = SelectField('College',[validators.DataRequired()], choices=[])
    college_name = StringField('College Name', [validators.Length(min=3), validators.DataRequired()])
    college_category = SelectField('College Category', [validators.DataRequired()], choices=[("Platinum","Platinum"), ("Gold","Gold"),  ("Silver", "Silver")])
    ur_spoc = StringField('UR SPOC', [validators.Length(min=1, max=200), validators.DataRequired()])
    city = SelectField('City',[validators.DataRequired()], choices=[("Bangalore","Bangalore"), ("C2","C2"),("Chennai","Chennai")])
    region = StringField('Region', [validators.Length(min=1, max=200), validators.DataRequired()])
    no_of_participants = IntegerField('No of participants', [validators.NumberRange(min=1)])
    no_of_registrations = IntegerField('No of registrations', [validators.NumberRange(min=1)])
    no_of_abstracts = IntegerField('No of abstracts shortlisted',[validators.NumberRange(min=1)])
    no_of_finalist = IntegerField('No of Finalist Teams',
                                   [validators.NumberRange(min=1)])
    finaledate = DateField('Finale Date', [validators.DataRequired()], default=datetime.date.today, format='%Y-%m-%d')
    speaker_name = StringField('Speakers', [validators.Length(min=1, max=200), validators.DataRequired()])
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
    status = RadioField('Status', [validators.DataRequired()], choices= [('Planned', 'Planned'), ('In Progress', 'In Progress'),('Completed','Completed'), ('Cancelled','Cancelled')],default='Planned')
    portal_status = RadioField('Event Posted on Portal?', [validators.DataRequired()], choices= [('Yes', 'Yes'), ('No', 'No')],default='Yes')
    post_event_social = RadioField('Post Event Socialising?', [validators.DataRequired()], choices= [('Yes', 'Yes'), ('No', 'No')],default='Yes')
    list_of_events  = SelectField('List of Events', choices=[])
    theme  = SelectField('Theme',[validators.DataRequired()], choices=[('Agile / DevOps', 'Agile / DevOps'),('AI / ML', 'AI / ML'), ('Analytics', 'Analytics'), ('Blockchain', 'Blockchain'), ('Cloud', 'Cloud'), ('Databases', 'Databases'), ('Design Thinking', 'Design Thinking'), ('Green Data Center', 'Green Data Center'), ('IoT', 'IoT'), ('Leadership Talk', 'Leadership Talk'), ('Mainframe','Mainframe'), ('Networking', 'Networking'), ('Patents & IP', 'Patents & IP'), ('Programming Languages', 'Programming Languages'), ('Project Management', 'Project Management'), ('Quantum Computing', 'Quantum Computing'), ('Security', 'Security'), ('Soft Skills', 'Soft Skills'), ('Smarter Cities', 'Smarter Cities'), ('SW Engg.', 'SW Engg.'), ('Watson', 'Watson'), ('Others', 'Others')])
    topic = StringField('Topic', [validators.Length(min=3), validators.DataRequired()])
    name_of_participants = StringField('Name of Participants. Separate using ;', [validators.Length(min=3), validators.DataRequired()])
    
    # ---------SUR---------
    sur_topic_name = StringField('SUR Topic Name', [validators.Length(min=3), validators.DataRequired()])
    prof_name = StringField('Professor Name', [validators.Length(min=3), validators.DataRequired()], render_kw={"placeholder": "Name"})
    prof_college_name = StringField('College', [validators.Length(min=3), validators.DataRequired()], render_kw={"placeholder": "College"})
    technology = StringField('Technology', [validators.Length(min=3), validators.DataRequired()])
    sur_grant_req = StringField('SUR Grant Request', [validators.Length(min=3), validators.DataRequired()],render_kw={"placeholder": "INR"})
    proposal_receipt_date = DateField('Proposal Receipt date',default = datetime.date.today, format='%Y-%m-%d')
    proposal_submission_date = DateField('Proposal Submission date',default = datetime.date.today, format='%Y-%m-%d')
    proposal_status = RadioField('Proposal Status', [validators.DataRequired()], choices=[('Approved', 'Approved'), ('Rejected', 'Rejected')],
                        default='Approved')
    invoice_receipt_date = DateField('Invoice receipt date',default = datetime.date.today, format='%Y-%m-%d')
    invoice_payout_date = DateField('Invoice payout date', default = datetime.date.today, format='%Y-%m-%d')
    paper_publications = StringField('Paper publications', [validators.Length(min=3)])
    type_of_event = StringField('Event type')
    conference_showcase = RadioField('Conference Showcase', [validators.DataRequired()], choices=[("Yes","Yes"), ("No","No")], default="Yes")
    conference_url = StringField('', [validators.Length(min=3)], render_kw={"placeholder": "Conference URL"})
    sur_proposal_location = StringField('SUR City ', [validators.Length(min=3), validators.DataRequired()])
    project_url = StringField('Project URL', [validators.Length(min=3), validators.DataRequired()])
   #-------SUR END------     
    
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
    feedback1 = TextAreaField('Feedback #1', [validators.Length(min=3)])
    feedback2 = TextAreaField('Feedback #2', [validators.Length(min=3)])
    feedback3 = TextAreaField('Feedback #3', [validators.Length(min=3)])
    url_list = StringField('', [validators.Length(min=3)])

    def validate_on_submit(self):
        if self.startdate.data > self.enddate.data:
            return False
        else:
            return True

    def validate_on_submit_sur(self):
        if self.proposal_receipt_date.data > self.proposal_submission_date.data and self.invoice_receipt_date.data > self.invoice_payout_date.data:
            return False
        if self.project_startdate.data > self.project_enddate.data:
            error = "Project Start Date is greater than Project End Date"
            return render_template('add_event.html', form=EventForm(request.form), error=error)
        else:
            return True
    
    def validate_on_submit_hackathon(self):
        if (self.startdate.data > self.enddate.data):
            return False
        if (self.finaledate.data < self.startdate.data):
            error = "Start date is greater than Finale date"
            return render_template('add_event.html', form=EventForm(request.form), error=error)
        if (int(self.no_of_finalist.data) > int(self.no_of_registrations.data)):
            error = "Number of Finalists cannot be greater than number of Registrations"
            return render_template('add_event.html', form=EventForm(request.form), error=error)
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
    form.institution.choices=college_call()
    form.list_of_events.choices = events_call()
    error = None
    if request.method == 'POST':
        event_name = form.event_name.data
        college = form.college.data
        # no_of_participants = form.no_of_participants.data
        # startdate = str(form.startdate.data)
        # enddate = str(form.enddate.data)
        theme = form.theme.data 
        # event_posted = form.event_posted.data
        # event_posted=request.form['event_portal']
        # comments = form.comments.data
        portal_status = form.portal_status.data
        post_event_social = form.post_event_social.data
        if (post_event_social == 'Yes'):
            url_list = request.form.getlist('url_list')
        else:
            url_list = 'None'
        feedback1 = form.feedback1.data
        feedback2 = form.feedback2.data
        feedback3 = form.feedback3.data
        # event_socialising = request.form['post_event']
        if form.validate_on_submit()==True:
            no_of_participants = str(form.no_of_participants.data)
            status = form.status.data
            startdate = str(form.startdate.data)
            enddate = str(form.enddate.data)

            sponsorship_amount = form.sponsorship_amount.data
            topic = form.topic.data
            # doc = {'username': session['username'],       commented out temporarily
            # compute total number of participants and add them here
            doc = {'event_name': event_name, 'college': college,'theme' : theme ,
                   'no_of_participants': no_of_participants, 'enddate': enddate, 'startdate': startdate,
                   'status': status, 'sponsorsship_amount': sponsorship_amount,'status': status,
                   'portal_status' : portal_status ,'post_event_social' : post_event_social,'topic':topic, 'type': 'event',
                   'feedback1': feedback1, 'feedback2': feedback2, 'feedback3': feedback3}
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
        prof_college_name = request.form.getlist('prof_college_name')
        list_prof = [x for x in zip(prof_name,prof_college_name)]
        print(prof_name)
        print(prof_college_name)
        technology = form.technology.data
        sur_grant_req=form.sur_grant_req.data
        print(sur_grant_req)
        if form.validate_on_submit_sur()==True:
            proposal_receipt_date = str(form.proposal_receipt_date.data)
            proposal_submission_date = str(form.proposal_submission_date.data)
            project_startdate = str(form.project_startdate.data)
            project_enddate = str(form.project_enddate.data)
            proposal_status = request.form['proposal_status']
            print(proposal_status)
            if proposal_status == 'Approved':
                invoice_receipt_date = str(form.invoice_receipt_date.data)
                invoice_payout_date = str(form.invoice_payout_date.data)
                paper_publications = form.paper_publications.data
                conference_show = form.conference_showcase.data
                if(conference_show == 'Yes'):
                    conference_url = form.conference_url.data
                else:
                    conference_url = ''
            else:
                invoice_receipt_date = ''
                invoice_payout_date = ''
                paper_publications = ''
                conference_show = ''
            sur_proposal_location = form.sur_proposal_location.data
            project_url = form.project_url.data
            portal_status = form.portal_status.data
            post_event_social = form.post_event_social.data
            if (post_event_social == 'Yes'):
                url_list = request.form.getlist('url_list')
            else:
                url_list = 'None'
            feedback1 = form.feedback1.data
            feedback2 = form.feedback2.data
            feedback3 = form.feedback3.data
            doc = { 'sur_topic_name': sur_topic_name, 'list_prof': list_prof,
                   'Technology': technology,'Grant_request':sur_grant_req, 'proposal_receipt_date': proposal_receipt_date, 'proposal_submission_date': proposal_submission_date,
                   'project_startdate':project_startdate,'project_enddate' : project_enddate,
                   'proposal_status': proposal_status, 'url_list': url_list,'portal_status':portal_status,'invoice_receipt_date': invoice_receipt_date, 'invoice_payout_date':invoice_payout_date, 'paper_publications': paper_publications,
                   'conference_show': conference_show, 'conference_url': conference_url , 'sur_proposal_location':sur_proposal_location,
                   'feedback1': feedback1, 'feedback2': feedback2, 'feedback3': feedback3,
                   'project_url': project_url, 'type': 'SUR'}
            db.save(doc)
            flash('SUR Created', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = "Reciept date is greater than Payout / Submission date"
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
        theme = form.theme.data
        topic = form.topic.data
        speaker_name = request.form.getlist('speaker_name')
        no_of_participants = str(form.no_of_participants.data)
        if form.validate_on_submit() == True:
            startdate = str(form.startdate.data)
            enddate = str(form.enddate.data)
            status = form.status.data
            portal_status = form.portal_status.data
            post_event_social = form.post_event_social.data
            if (post_event_social == 'Yes'):
                url_list = request.form.getlist('url_list')
            else:
                url_list = 'None'
            # technology = form.technology.data
            bu = form.bu.data
            ibm_sme_name = form.ibm_sme_name.data
            box_location_atten = form.box_location_atten.data
            box_location_feed = form.box_location_feed.data
            feedback1 = form.feedback1.data
            feedback2 = form.feedback2.data
            feedback3 = form.feedback3.data
            # box_location_winning_profile = form.box_location_winning_profile.data
            doc = {'event_name': event_name,'main_event':list_of_events, 'college': college, 'theme': theme, 'topic': topic,
                'speaker_name': speaker_name,'no_of_participants': no_of_participants,'startdate': startdate,'enddate': enddate,'portal_status':portal_status,
                'status':status, 'url_list': url_list, 'bu' : bu, 'post_event_social':post_event_social, 'ibm_sme_name' : ibm_sme_name, 'box_location_atten' : box_location_atten,
                'box_location_feed' : box_location_feed, 'feedback1': feedback1, 'feedback2': feedback2, 'feedback3': feedback3,
                'type': 'tech Session'}
            db.save(doc)
            flash('Event Created', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = "Start date is greater than End date"
        return render_template('add_event.html', form=form, error=error)

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
        if form.validate_on_submit_hackathon() == True:
            startdate = str(form.startdate.data)
            enddate = str(form.enddate.data)
            theme = form.theme.data
            no_of_registrations = form.no_of_registrations.data
            no_of_abstracts = form.no_of_abstracts.data
            no_of_finalist = form.no_of_finalist.data
            finaledate = str(form.finaledate.data)
            if ((finaledate > enddate) or (finaledate < startdate)):
                flash('Hackathon Finale Date should lie within the Start Date and End Date', 'danger')
                return redirect(url_for('hackathon'))
            jury = request.form.getlist('jury_name')
            bu = request.form.getlist('bu')
            list_ibm_jury = [x for x in zip(jury,bu)]
            team_name1 = form.team_name1.data
            team_member_name1 = request.form.getlist('team_member_name1')
            team_member_college1 = request.form.getlist('team_member_college1')
            list_team1 = [x for x in zip(team_member_name1,team_member_college1)]
            team_name2 = form.team_name2.data
            team_member_name2 = request.form.getlist('team_member_name2')
            team_member_college2 = request.form.getlist('team_member_college2')
            list_team2 = [x for x in zip(team_member_name2,team_member_college2)]
            team_name3 = form.team_name3.data
            team_member_name3 = request.form.getlist('team_member_name3')
            team_member_college3 = request.form.getlist('team_member_college3')
            list_team3 = [x for x in zip(team_member_name3,team_member_college3)]
            winning_team_profiles = form.box_location_winning_profile.data
            status = form.status.data
            portal_status = form.portal_status.data
            post_event_social = form.post_event_social.data
            if (post_event_social == 'Yes'):
                url_list = request.form.getlist('url_list')
            else:
                url_list = 'None'
            feedback1 = form.feedback1.data
            feedback2 = form.feedback2.data
            feedback3 = form.feedback3.data
            # additional_jury = form.additional_jury_name.data
            # winning_team_details = form.winning_team_details.data
            # runnerup_team_details = form.runnerup_team_details.data
            doc = {'Hackathon_name': hackathon_name,'main_event':list_of_events, 'college': college,
                   'no_of_participants': no_of_participants,'no_of_registrations': no_of_registrations,'status':status, 'url_list': url_list,'portal_status':portal_status,
                   'no_of_abstracts': no_of_abstracts, 'no_of_finalist': no_of_finalist,
                   'startdate': startdate,'enddate': enddate,'finaledate': finaledate,'theme':theme,
                   'jury' : list_ibm_jury, 'team_name1': team_name1, 'list_team1': list_team1, 'team_name2': team_name2, 'list_team2': list_team2, 'team_name3': team_name3, 'list_team3': list_team3,
                   'feedback1': feedback1, 'feedback2': feedback2, 'feedback3': feedback3,
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
        form.technology.data =  db[id]['Technology']
        form.sur_grant_req.data=db[id]['Grant_request']
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
        form.conference_url.data = db[id]['conference_url']
        form.sur_proposal_location.data = db[id]['sur_proposal_location']
        form.project_url.data = db[id]['project_url']
        form.type_of_event.data = 'SUR'
        form.feedback1.data = db[id]['feedback1']
        form.feedback2.data = db[id]['feedback2']
        form.feedback3.data = db[id]['feedback3']
        if request.method == 'POST':
            doc = db[id]
            doc['sur_topic_name'] = request.form['sur_topic_name']
            doc['professor_Name'] = request.form['prof_name']
            doc['professor_college_Name'] = request.form['prof_college_name']
            doc['Technology'] = request.form['technology']
            doc['Grant_request']=request.form['sur_grant_req']
            doc['feedback1'] = request.form['feedback1']
            doc['feedback2'] = request.form['feedback2']
            doc['feedback3'] = request.form['feedback3']
            if form.validate_on_submit_sur() == True:
                print("I am in")
                proposal_status = request.form['proposal_status']
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
                doc['proposal_status'] = request.form['proposal_status']
                doc['conference_url'] = request.form['conference_url']
                doc['sur_proposal_location'] = request.form['sur_proposal_location']
                doc['project_url'] = request.form['project_url']
                prof_name = request.form.getlist('prof_name')
                prof_college_name = request.form.getlist('prof_college_name')
                doc['list_prof'] = [x for x in zip(prof_name,prof_college_name)]
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
        form.theme.data = db[id]['theme']
        # form.jury_name.data = db[id]['jury']
        # form.additional_jury_name.data = db[id]['additional_jury']
        list_ibm_jury = db[id]['jury'] 
        
        # Fetch name and BU of jury
        # list_ibm_jury stores jury-information in the format: [(name, BU), (name, BU) ...]
        
        form.team_name1.data = db[id]['team_name1']
        # list_team1 = db[id]['list_team1']
        form.team_name2.data = db[id]['team_name2']
        # list_team2 = db[id]['list_team2']
        form.team_name3.data = db[id]['team_name3']
        # list_team3 = db[id]['list_team3']

        form.status.data = db[id]['status']
        form.portal_status.data = db[id]['portal_status']
        # form.url_list.data = db[id]['url_list']
        # form.winning_team_details.data = db[id]['winning_team_details']
        # form.runnerup_team_details.data = db[id]['runnerup_team_details']
        form.box_location_winning_profile.data = db[id]['winning_team_profiles']
        form.feedback1.data = db[id]['feedback1']
        form.feedback2.data = db[id]['feedback2']
        form.feedback3.data = db[id]['feedback3']
        form.type_of_event.data = 'Hackathon'
        if request.method == 'POST':
            doc = db[id]
            doc['Hackathon_name'] = request.form['hackathon_name']
            doc['college'] = request.form['college']
            doc['main_event'] = request.form['list_of_events']
            if form.validate_on_submit_hackathon() == True:
                print("I am in")
                doc['no_of_participants'] = request.form['no_of_participants']
                doc['no_of_registrations'] = request.form['no_of_registrations']
                doc['no_of_abstracts'] = request.form['no_of_abstracts']
                doc['no_of_finalist'] = request.form['no_of_finalist']
                doc['startdate'] = request.form['startdate']
                doc['enddate'] = request.form['enddate']
                doc['finaledate'] = request.form['finaledate']
                doc['status'] = request.form['status']
                doc['feedback1'] = request.form['feedback1']
                doc['feedback2'] = request.form['feedback2']
                doc['feedback3'] = request.form['feedback3']
                post_event_social = form.post_event_social.data
                if (post_event_social == 'Yes'):
                    doc['url_list'] = request.form.getlist('url_list')
                else:
                    doc['url_list'] = 'None'
                
                doc['theme'] = request.form['theme']
                # doc['jury'] = request.form['jury_name']
                # doc['additional_jury'] = request.form['additional_jury_name']
                # doc['winning_team_details'] = request.form['winning_team_details']
                # doc['runnerup_team_details'] = request.form['runnerup_team_details']
                doc['team_name1'] = form.team_name1.data
                team_member_name1 = request.form.getlist('team_member_name1')
                team_member_college1 = request.form.getlist('team_member_college1')
                doc['list_team1'] = [x for x in zip(team_member_name1,team_member_college1)]
                doc['team_name2'] = form.team_name2.data
                team_member_name2 = request.form.getlist('team_member_name2')
                team_member_college2 = request.form.getlist('team_member_college2')
                doc['list_team2'] = [x for x in zip(team_member_name2,team_member_college2)]
                doc['team_name3'] = form.team_name3.data
                team_member_name3 = request.form.getlist('team_member_name3')
                team_member_college3 = request.form.getlist('team_member_college3')
                doc['list_team3'] = [x for x in zip(team_member_name3,team_member_college3)]
                jury = request.form.getlist('jury_name')
                bu = request.form.getlist('bu')
                doc['jury'] = [x for x in zip(jury,bu)]
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
        # form.technology.data = db[id]['technology']
        form.theme.data = db[id]['theme']
        form.topic.data = db[id]['topic']
        # form.speaker_name.data = db[id]['speaker_name']
        speaker_list = db[id]['speaker_name']
        form.status.data = db[id]['status']
        form.portal_status.data = db[id]['portal_status']
        form.url_list.data = db[id]['url_list']
        form.bu.data = db[id]['bu']
        form.ibm_sme_name.data = db[id]['ibm_sme_name']
        form.box_location_atten.data = db[id]['box_location_atten']
        form.box_location_feed.data = db[id]['box_location_feed']
        form.type_of_event.data = 'tech_session'
        form.feedback1.data = db[id]['feedback1']
        form.feedback2.data = db[id]['feedback2']
        form.feedback3.data = db[id]['feedback3']

        if request.method == 'POST':
            doc = db[id]
            doc['event_name'] = request.form['tech_session_name']
            doc['college'] = request.form['college']
            doc['main_event'] = request.form['list_of_events']
            doc['no_of_participants'] = request.form['no_of_participants']
            if form.validate_on_submit() == True:
                doc['startdate'] = request.form['startdate']
                doc['enddate'] = request.form['enddate']
                doc['theme'] = request.form['theme']
                doc['topic'] = request.form['topic']
                doc['speaker_name'] = request.form.getlist('speaker_name')
                doc['status'] = request.form['status']
                doc['portal_status'] = request.form['portal_status']
                post_event_social = form.post_event_social.data
                if (post_event_social == 'Yes'):
                    doc['url_list'] = request.form.getlist('url_list')
                else:
                    doc['url_list'] = 'None'
                doc['ibm_sme_name'] = request.form['ibm_sme_name']
                # doc['technology'] = request.form['technology']
                doc['bu'] = request.form['bu']
                doc['box_location_atten'] = request.form['box_location_atten']
                doc['box_location_feed'] = request.form['box_location_feed']
                doc['feedback1'] = request.form['feedback1']
                doc['feedback2'] = request.form['feedback2']
                doc['feedback3'] = request.form['feedback3']
                db.save(doc)
                print(doc)
                flash('Event Updated', 'info')

                return redirect(url_for('dashboard'))
            else:
                error = "Start date is greater than End date"
            return render_template('add_event.html', form=form, error=error)
    
    # compute total number of participants and add them here
    # resolve url_list error
    else:
        result = db[id]
        form = EventForm(request.form)
        form.event_name.data = db[id]['event_name']
        form.sponsorship_amount.data = db[id]['sponsorship_amount']
        form.college.data = db[id]['college'] 
        form.college.choices = college_call()
        form.no_of_participants.data = db[id]['no_of_participants']
        form.theme.data = db[id]['theme']
        t = db[id]['startdate']
        t = t.replace('-', '')
        s = datetime.datetime.strptime(t, "%Y%m%d")
        form.startdate.data = s
        t = db[id]['enddate']
        t = t.replace('-', '')
        s = datetime.datetime.strptime(t, "%Y%m%d")
        form.enddate.data = s
        form.status.data = db[id]['status']
        form.portal_status.data = db[id]['portal_status']
        # form.url_list.data = db[id]['url_list']
        form.type_of_event.data = 'event'
        if request.method == 'POST':
            event_name = request.form['event_name']
            sponsorship_amount = request.form['sponsorship_amount']
            college = request.form['college'] 
            # no_of_participants = request.form['no_of_participants']
            startdate = request.form['startdate']
            enddate = request.form['enddate']
            status = request.form['status']
            portal_status = request.form['portal_status']
            # url_list = request.form['url_list']
            theme = request.form['theme']

            doc = db[id]
            doc['event_name'] = event_name
            doc['sponsorship_amount'] =sponsorship_amount
            doc['college'] = college 
            doc['theme'] = theme
            # doc['no_of_participants'] = no_of_participants
            doc['startdate'] = startdate
            doc['enddate'] = enddate
            doc['status'] = status
            doc['portal_status'] = portal_status
            # doc['url_list'] = url_list
            post_event_social = form.post_event_social.data
            if (post_event_social == 'Yes'):
                doc['url_list'] = request.form.getlist('url_list')
            else:
                doc['url_list'] = 'None'
            

            db.save(doc)
            flash('Event Updated', 'info')

            return redirect(url_for('dashboard'))

    if (db[id]['type'] == 'Hackathon'):
        return render_template('edit_event.html', form=form, social_url_list=db[id]['url_list'], list_team1=db[id]['list_team1'], list_team2=db[id]['list_team2'], list_team3=db[id]['list_team3'], jury=db[id]['jury'], speaker_list=[None], list_prof=[[None]])
    if (db[id]['type'] == 'tech Session'):
        return render_template('edit_event.html', form=form, social_url_list=db[id]['url_list'], list_team1=[[None]], list_team2=[[None]], list_team3=[[None]], jury=[[None]], speaker_list=db[id]['speaker_name'], list_prof=[[None]])
    if db[id]['type'] == 'SUR':
        return render_template('edit_event.html', form=form, social_url_list=db[id]['url_list'], list_team1=[[None]], list_team2=[[None]], list_team3=[[None]], jury=[[None]], speaker_list=[None], list_prof=db[id]['list_prof'])
    else:
        return render_template('edit_event.html', form=form, social_url_list=db[id]['url_list'], list_team1=[[None]], list_team2=[[None]], list_team3=[[None]], jury=[[None]], speaker_list=[None], list_prof=[[None]])
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
@is_logged_in
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
@is_logged_in
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
    header_techSession = ['main_event','event_name','college','no_of_participants','status','startdate','enddate','theme','bu','ibm_sme_name','box_location_atten','box_location_feed']
    header_hackathon = ['main_event','Hackathon_name','college','no_of_participants','no_of_registrations','no_of_abstracts','no_of_finalist'
                        ,'startdate','enddate', 'finaledate', 'theme','jury','status','team_name1', 'team_name2','winning_team_profiles']
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
    app.run(host='0.0.0.0',port=2222,debug=True)
