#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import time
import datetime
import cgi
import os
# test base64
import base64
import urllib
import re
import random
import hashlib
import hmac
import logging
import json
from json import JSONEncoder
from string import letters
import urllib2
import webapp2
import jinja2
import zipfile
import facebook
from google.appengine.api import urlfetch
urlfetch.set_default_fetch_deadline(45)
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from webapp2_extras import sessions
from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import mail
from xml.dom.minidom import parse, parseString
from HTMLParser import HTMLParser
from BeautifulSoup import BeautifulSoup
#from Graph import *

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),autoescape = False)

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__))
)

secret = "you-will-never-guess"

## config ##

config = {}
config['webapp2_extras.sessions'] = dict(secret_key='slhflsnhflsgkfgvsdbfksdhfksdhfkjs')
#slhflsnhflsgkfgvsdbfksdhfksdhfkjs

#######################################################################################################
#######################################################################################################
#######################################################################################################
###############  						Helper Function Section								###########
#######################################################################################################
#######################################################################################################
#######################################################################################################
class DateEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)

def split_by_colon(str):
	result = []
	result = str.split(';')
	return result
	
def create_params():
	length = 10
	return ''.join(random.choice(letters) for x in xrange(length))
		
##html input escape
def escape_html(s):
	return cgi.escape(s, quote = True)

## user stuff goes here ##
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val
def make_salt(length = 5):
	return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
	salt = h.split(',')[0]
	return h == make_pw_hash(name, password, salt)


USER_RE = re.compile(r"^[\S\s]{3,25}$")
def valid_displayname(display_name):
    return display_name and USER_RE.match(display_name)

def valid_username(username):
    return username and USER_RE.match(username)

LOGIN_RE = re.compile(r"^[a-zA-Z0-9_-]{6,25}$")
def valid_loginname(login_name):
    return login_name and LOGIN_RE.match(login_name)

PASS_RE = re.compile(r"^.{6,25}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

def string_normalize(s):
	s = re.sub('[^0-9a-zA-Z]+', '', s)
	s = s.lower()
	return s

#######################################################################################################
#######################################################################################################
#######################################################################################################
###############  						Handler Section								###################
#######################################################################################################
#######################################################################################################
#######################################################################################################
	
class FacebookHandler(webapp2.RequestHandler):   
	@property
	def fb_user(self):
		length = 5
		if self.session.get("user"):
		#if self.user:
		# User is logged in

			return self.session.get("user")
			#return self.user
		else:
		# Either used just logged in or just saw the first page
		# We'll see here
			cookie = facebook.get_user_from_cookie(self.request.cookies,
                                                   FACEBOOK_APP_ID,
                                                   FACEBOOK_APP_SECRET)
			if cookie:
			# Okay so user logged in.
			# Now, check to see if existing user
				user = FacebookUser.get_by_id(cookie["uid"])
				if not user:
				# Not an existing user so get user info
					graph = facebook.GraphAPI(cookie["access_token"])
					profile = graph.get_object('me')
					access_params = ''.join(random.choice(letters) for x in xrange(length))
							
					user = FacebookUser(
									id=str(profile["id"]),
									user_id=str(profile["id"]),
									displayname=profile["name"],									
									profile_url=profile["link"],
									access_token=cookie["access_token"],
									access_params=access_params,
									email=profile["email"]
								)
					user.put()
				elif user.access_token != cookie["access_token"]:
					user.access_token = cookie["access_token"]
					user.put()
			# User is now logged in

				self.session["user"] = dict(
								displayname=user.displayname,
								email=user.email,
								profile_url=user.profile_url,
								user_id=user.user_id,
								access_token=user.access_token,
								access_params=user.access_params,
								## fetch user key for further usage.
								user_key=user.key.id()
							)

				return self.session.get("user")
				#return user
		return None

	def dispatch(self):

		self.session_store = sessions.get_store(request=self.request)
		try:
			webapp2.RequestHandler.dispatch(self)
		finally:
			self.session_store.save_sessions(self.response)

	@webapp2.cached_property
	def session(self):
		return self.session_store.get_session()

		
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
		
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
		
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
		
    def render_json(self, d):
        json_txt = json.dumps(d.to_dict())
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.write(json_txt)
		
	def render_image(self, image):
		self.response.headers['Content-Type'] = 'image/jpeg'
		self.write(image)	
		
    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; expires=Sun, 5-May-2016 23:59:59 GMT; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key.id()))

    def logout(self):
		self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')
	
    def initialize(self, *a, **kw):     
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('user_id')
		self.user = uid and User.by_id(int(uid))
			
		
def init_data(self):
	data = {}
	if self.user:
		data = { 'user':self.user }
	if self.fb_user:
		data = { 'fb_user':self.fb_user }
		fb_user = self.fb_user
		user = FacebookUser.get_by_id(fb_user["user_key"])
		topology = Topology.query().filter(Topology.owner == user.key ).get()
		status = Status.query().filter(Status.owner == user.key ).get()
		data['status'] = status
	data['facebook_app_id'] = FACEBOOK_APP_ID	
	return data	


class LogOutHandler(Handler):
	def get(self):
		self.logout()
		self.redirect('/')	
															
class PleaseLoginHandler(Handler,FacebookHandler):
	def get(self):
		if data['user'] or data['fb_user']:
			self.redirect('/')

class FacebookLoginHandler(FacebookHandler):
	def get(self):
		template = jinja_env.get_template('example.html')
		self.response.out.write(template.render(dict(
			facebook_app_id=FACEBOOK_APP_ID,
            fb_user=self.fb_user
        )))		
		
class FacebookLogoutHandler(Handler,FacebookHandler):
    def get(self):
        if self.fb_user is not None:
            self.session['user'] = None
        self.redirect('/')
			
class HubHandler(Handler,FacebookHandler):
	def get(self):
		self.render('home.html')
				
class MapHandler(Handler,FacebookHandler):
	def get(self):
		self.render('map.html')

class DashboardHandler(Handler,FacebookHandler):
	def get(self):
		data = {}
		maps = Map.query()
		data['maps'] = maps
		self.render('dashboard.html',**data)

class CreateMapHandler(Handler,FacebookHandler):
	def post(self):
		name = escape_html(self.request.get('map'))
		desc = escape_html(self.request.get('desc'))
		access_params = create_params()
		map = Map(	name = name,
					desc = desc,
					access_params = access_params )
		map.put()
		time.sleep(2)
		self.redirect('/dashboard')

class AttackerHandler(Handler,FacebookHandler,blobstore_handlers.BlobstoreUploadHandler):
	def get(self):
		data = {}
		upload_url = blobstore.create_upload_url('/add-new-attacker')
		attackers = Attacker.query()
		vuls = ["Authentication","Buffer Overflow","Configuration Problem","Cryptographic error","Cross-Site Request Forgery","Insecure default configuration","Cross-site scripting",
		"Unknown vulnerability","SQL injection","Spoofing attacks","General race condition","Denial of Service"]
		data['upload_url'] = upload_url
		data['vuls'] = vuls
		data['attackers'] = attackers
		self.render('attacker.html',**data)

class DisplayImageHandler(blobstore_handlers.BlobstoreDownloadHandler):
	def get(self):
		upload_key_str = self.request.params.get('acc')
		upload = None
		if upload_key_str:
			upload = CharacterImage.query().filter(CharacterImage.access_params == upload_key_str ).get()		
		self.send_blob(upload.blob)
		
class AddNewAttackerHandler(Handler,FacebookHandler,blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		alias = escape_html(self.request.get('alias'))
		desc = escape_html(self.request.get('desc'))
		cve = escape_html(self.request.get('cve'))
		flawtype = escape_html(self.request.get('flawtype'))
		access_params = create_params()
		
		attacker = Attacker(	alias = alias,
								desc = desc,
								cve = cve,
								flawtype = flawtype,
								access_params = access_params	)
		attacker.put()
		time.sleep(2)
		
		for blob_info in self.get_uploads('upload'):
			upload = CharacterImage(
					blob = blob_info.key(),
					owner = alias,
					access_params = access_params	)
			upload.put()
		time.sleep(2)
		self.redirect('/attacker')

def translateCWE_ID(cwe_id):
	return { 	"20" 	: 	"Input Validation",
				"22"	:	"Path Transversal",
				"59"	:	"Link Following",
				"78"	:	"OS Command Injection",
				"89"	:	"SQL Injection",
				"287"	: 	"Authentication Issues",
				"255"	:	"Credentials Management",
				"264"	: 	"Permission Priviledge & Access Point",
				"119"	:	"Buffer Error",
				"352"	:	"Cross-site request forgery",
				"310"	:	"Cryptography Issues",
				"94"	:	"Code Injection",
				"134"	:	"Format String Vulnerability",
				"16"	:	"Configuration",
				"189"	:	"Numeric Errors",
				"362"	:	"Race Condition",
				"399"	:	"Resource Management Error"	
			}.get(cwe_id,"Others")
			
def setOption(option):
	if option:
		option = 1
	else:
		option = 0
	return option

def setOrderOption(option):
	return {	"publishDate"		:	1,
				"lastUpdateDate"	:	2,
				"CVE_id"			:	3}.get(option,1)

#NVD calculator
#http://nvd.nist.gov/cvss.cfm?version=2&name=CVE-2014-5318&vector=(AV:A/AC:M/Au:N/C:P/I:P/A:P)
				
class CVEProfileFetchHandler(Handler,FacebookHandler):
	def get(self):
		data = {}
		scores = [ 0,1,2,3,4,5,6,7,8,9,10 ]
		rows = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]
		orders = [ "Publish Date", "Last Update Date", "CVE ID"]
		options = { 'hashexp' 	: 	'Vulnerability with Expliots', 
					'opcsrf' 	: 	'Cross Site Request Forgery',
					'opsqli'	:	'SQL Injection',
					'opmemc'	:	'Memory Corruption',
					'opginf'	:	'Gain Information',
					'opec'		:	'Code Execution',
					'opfileinc'	:	'File inclusion',
					'opxss'		:	'Cross Site Scripting',
					'ophttprs'	:	'HTTP Response Spliting',
					'opdos'		: 	'Denial of Service',
					'opgpriv'	:	'Gain Priviledges',
					'opov'		:	'Overflow',
					'opdirt'	: 	'Directory Transverse',
					'opbyp'		:	'Bypass Something' 				}
		profiles = CVEProfile.query()
		data['scores'] = scores
		data['rows'] = rows
		data['orders'] = orders
		data['options'] = options
		data['profiles'] = profiles
		self.render('fetch-profile.html',**data)
		
	def post(self):
		#init_default
		URL = "http://www.cvedetails.com/json-feed.php?"
		numrows = 10					#		MAX = 30
		vendor_id = 0					#		default = 0
		product_id = 0					#		default = 0
		version_id = 0					#		default = 0
		#option
		hashexp = 0 					#		vulnerability with exploits
		opcsrf = 0 						#		cross site request forgery
		opsqli = 0 						#		SQL injection
		opmemc = 0 						#		Memory corruption
		opginf = 0 						#		Gain information
		opec = 0 						#		Code Execution
		opfileinc = 0 					#		File inclusion
		opxss = 0 						#		Cross site scripting
		ophttprs = 0 					#		HTTP Response Spliting
		opdos = 0 						#		Denial of Service
		opgpriv = 0 					#		Gain Priviledge
		opov = 0 						#		Overflow
		opdirt = 0						#		Directory Transverse
		opbyp = 0						#		Bypass Something
		#order
		orderby = 0						#		Publish Date = 1 ,Last Update date = 2 , CVE ID = 3
		cvssscoremin = 0				# 		1-10

		#get check
		hashexp = setOption(bool(self.request.get('hashexp')))
		opcsrf = setOption(bool(self.request.get('opcsrf')))
		opsqli = setOption(bool(self.request.get('opsqli')))
		opmemc = setOption(bool(self.request.get('opmemc')))
		opginf = setOption(bool(self.request.get('opginf')))
		opec = setOption(bool(self.request.get('opec')))
		opfileinc = setOption(bool(self.request.get('opfileinc')))
		opxss = setOption(bool(self.request.get('opxss')))
		ophttprs = setOption(bool(self.request.get('ophttprs')))
		opdos = setOption(bool(self.request.get('opdos')))
		opgpriv = setOption(bool(self.request.get('opgpriv')))
		opov = setOption(bool(self.request.get('opov')))
		opdirt = setOption(bool(self.request.get('opdirt')))
		opbyp = setOption(bool(self.request.get('opbyp')))
		#get degree
		numrows = int(self.request.get('numrows'))
		cvssscoremin = int(self.request.get('cvssscoremin'))
		orderby = setOrderOption(self.request.get('orderby'))
		
		values = {	'numrows'		: 	numrows,
					'vendor_id'		:	vendor_id,
					'product_id'	:	product_id,
					'version_id'	:	version_id,
					'hashexp'		:	hashexp,
					'opcsrf'		:	opcsrf,
					'opsqli'		:	opsqli,
					'opmemc'		:	opmemc,
					'opginf'		:	opginf,
					'opec'			:	opec,
					'opfileinc'		:	opfileinc,
					'opxss'			:	opxss,
					'ophttprs'		:	ophttprs,
					'opdos'			:	opdos,
					'opgpriv'		:	opgpriv,
					'opov'			:	opov,
					'opdirt'		:	opdirt,
					'opbyp'			:	opbyp,
					'cvssscoremin'	:	cvssscoremin,
					'orderby'		:	orderby			}
		# 	GET
		data = urllib.urlencode(values)
		json_url = URL+data
		#	POST	req = urllib2.Request(URL,data)
		# 	FETCH
		json_objects = json.loads(urllib2.urlopen(json_url).read())
		# 	STORE TO NDB
		for object in json_objects:
			cve_id = object['cve_id']
			cwe_id = object['cwe_id']
			cwe_name = translateCWE_ID(cwe_id)
			summary = object['summary']
			cvss_score = float(object['cvss_score'])
			exploit_count = int(object['exploit_count'])
			publish_date = object['publish_date']
			update_date = object['update_date']
			cve_url = object['url']
			#fetch CVSS Score
			#cvss metrix
			confidentiality_impact = 1  	# None = 1 , Partial = 2, Complete =3 
			integrity_impact = 1			# None = 1 , Partial = 2, Complete =3 
			availability_impact = 1			# None = 1 , Partial = 2, Complete =3 
			access_complexity = 1			# Low = 1 , Medium = 2, High = 3 
			gained_access = 1				# None = 1 , User = 2 , Admin = 3 
			authentication  = 1				# Not Required = 1 , Single System = 2, Multiple systems = 3  
			CVSS_URL = cve_url
			soup = BeautifulSoup(urllib2.urlopen(CVSS_URL))
			#confidentiality_impact
			c_impact = soup.find(text='Confidentiality Impact')
			c_impact = c_impact.findNext('span')
			if c_impact.find(text='Partial'):
				confidentiality_impact = 2
			if c_impact.find(text='Complete'):
				confidentiality_impact = 3
			#integrity_impact
			i_impact = soup.find(text='Integrity Impact')
			i_impact = i_impact.findNext('span')
			if i_impact.find(text='Partial'):
				integrity_impact = 2
			if i_impact.find(text='Complete'):
				integrity_impact = 3
			#availability_impact
			a_impact = soup.find(text='Availability Impact')
			a_impact = a_impact.findNext('span')
			if a_impact.find(text='Partial'):
				availability_impact = 2
			if a_impact.find(text='Complete'):
				availability_impact = 3
			#access_complexity
			a_complex = soup.find(text='Access Complexity')
			a_complex = a_complex.findNext('span')
			if a_impact.find(text='Medium'):
				access_complexity = 2
			if a_impact.find(text='High'):
				access_complexity = 3
			#authentication
			authen = soup.find(text='Authentication')
			authen = authen.findNext('span')
			if authen.find(text='Single system'):
				authentication = 2
			if authen.find(text='Multiple systems'):
				authentication = 3
			#gained access
			g_access = soup.find(text='Gained Access')
			g_access = g_access.findNext('span')
			if g_access.find(text='User'):
				gained_access = 2
			if g_access.find(text='Admin'):
				gained_access = 3				
			put_object = CVEProfile.createProfile(cve_id, cwe_id, cwe_name, summary, cvss_score, exploit_count, publish_date, update_date, cve_url, confidentiality_impact, integrity_impact, availability_impact, access_complexity, gained_access, authentication )
			put_object.put()
		time.sleep(2)
		self.redirect('/fetch-profile')
			
	
class CVSScoreHandler(Handler,FacebookHandler):
	def get(self):
		data = {}
		#init metrix
		confidentiality_impact = 1  	# None = 1 , Partial = 2, Complete =3 
		integrity_impact = 1			# None = 1 , Partial = 2, Complete =3 
		availability_impact = 1			# None = 1 , Partial = 2, Complete =3 
		access_complexity = 1			# Low = 1 , Medium = 2, High = 3 
		gained_access = 1				# None = 1 , User = 2 , Admin = 3 
		authentication  = 1				# Not Required = 1 , Single System = 2, Multiple systems = 3  
		CVSS_URL = "http://www.cvedetails.com/cve/CVE-2014-6043/"
		#page = urllib2.urlopen(CVSS_URL)
		soup = BeautifulSoup(urllib2.urlopen(CVSS_URL))
		#confidentiality_impact
		c_impact = soup.find(text='Confidentiality Impact')
		c_impact = c_impact.findNext('span')
		if c_impact.find(text='Partial'):
			confidentiality_impact = 2
		if c_impact.find(text='Complete'):
			confidentiality_impact = 3
		#integrity_impact
		i_impact = soup.find(text='Integrity Impact')
		i_impact = i_impact.findNext('span')
		if i_impact.find(text='Partial'):
			integrity_impact = 2
		if i_impact.find(text='Complete'):
			integrity_impact = 3
		#availability_impact
		a_impact = soup.find(text='Availability Impact')
		a_impact = a_impact.findNext('span')
		if a_impact.find(text='Partial'):
			availability_impact = 2
		if a_impact.find(text='Complete'):
			availability_impact = 3
		#access_complexity
		a_complex = soup.find(text='Access Complexity')
		a_complex = a_complex.findNext('span')
		if a_impact.find(text='Medium'):
			access_complexity = 2
		if a_impact.find(text='High'):
			access_complexity = 3
		#authentication
		authen = soup.find(text='Authentication')
		authen = authen.findNext('span')
		if authen.find(text='Single system'):
			authentication = 2
		if authen.find(text='Multiple systems'):
			authentication = 3
		#gained access
		g_access = soup.find(text='Gained Access')
		g_access = g_access.findNext('span')
		if g_access.find(text='User'):
			gained_access = 2
		if g_access.find(text='Admin'):
			gained_access = 3		
		
		data['confidentiality_impact'] = confidentiality_impact
		data['integrity_impact'] = integrity_impact
		data['availability_impact'] = availability_impact
		data['access_complexity'] =  access_complexity
		data['gained_access'] = gained_access
		data['authentication'] = authentication
		self.render('test.html',**data)

class GetGraphHandler(Handler,FacebookHandler):	
	def get(self):
		id = int(escape_html(self.request.get('id')))
		u = Graph.query().filter(Graph.graphID == id).get()		
		self.render_json(u)
		
class CreateGraphHandler(Handler,FacebookHandler):	
	def get(self):
		data = {}
		graphs = Graph.query().order(Graph.graphID)
		data['graphs'] = graphs
		self.render('create-graph.html',**data)
		
	def post(self):
		name = escape_html(self.request.get('graph-name'))
		graphs = Graph.query().order(-Graph.graphID).get()
		if graphs:
			graphID = graphs.graphID + 1
		else:
			graphID = 1
		u = Graph(	graphID		= 	graphID,
					name		=	name)
		u.put()
		self.redirect('/create-graph')
	
class EditGraphHandler(Handler,FacebookHandler):
	def get(self):
		data = {}
		id = int(escape_html(self.request.get('id')))
		service_status = [ "found" ,"attacking" ]
		machine_status = [ "hidden", "found" , "ready" ,"attacking" ]
		path_status = [ "","unused", "used" ]
		graph = Graph.query().filter(Graph.graphID == id).get()
		profiles = CVEProfile.query()
		data['graph'] = graph
		data['service_status'] = service_status
		data['machine_status'] = machine_status
		data['path_status'] = path_status
		data['profiles'] = profiles
		self.render('edit-graph.html',**data)
		
class DeleteGraphHandler(Handler,FacebookHandler):
	def post(self):
		id = int(escape_html(self.request.get('id')))
		u = Graph.query().filter(Graph.graphID == id).get().key 
		u.delete()
		time.sleep(2)
		self.redirect('/create-graph')
		
class AddNewMachineHandler(Handler,FacebookHandler):
	def post(self):
		id = int(self.request.get('GraphID'))
		u = Graph.query().filter(Graph.graphID == id).get()
		machineID = int(escape_html(self.request.get('machineID')))
		name = escape_html(self.request.get('machineName'))
		status = escape_html(self.request.get('machineStatus'))
		impact = int(escape_html(self.request.get('machineImpact')))
		v = Machine.add_new_machine(machineID,name,status,impact)
		#v.put()
		if u.machines:
			u.machines.append(v)
		else:
			u.machines = [ v ]
		u.put()
		#self.write("success!")
		
class AddNewServiceHandler(Handler,FacebookHandler):
	def post(self):
		id = int(self.request.get('GraphID'))
		u = Graph.query().filter(Graph.graphID == id).get()
		serviceID = int(escape_html(self.request.get('serviceID')))
		name = escape_html(self.request.get('serviceName'))
		status = escape_html(self.request.get('serviceStatus'))
		impact = int(escape_html(self.request.get('serviceImpact')))
		machineID = int(escape_html(self.request.get('serviceMachineID')))
		v = Service.add_new_service(serviceID,name,status,impact,machineID)
		if u.services:
			u.services.append(v)
		else:
			u.services = [ v ]
		u.put()
		
class AddNewPathHandler(Handler,FacebookHandler):
	def post(self):
		id = int(self.request.get('GraphID'))
		u = Graph.query().filter(Graph.graphID == id).get()
		pathID = int(escape_html(self.request.get('pathID')))
		#GET CVSS FROM PROFILE
		name = escape_html(self.request.get('pathName'))
		cve_id = name
		v = CVEProfile.query().filter(CVEProfile.cve_id == cve_id).get()
		cvss = v.access_params
		#STATUS???
		status = escape_html(self.request.get('pathStatus'))
		#SERVICE STATUS
		src = int(escape_html(self.request.get('pathSrc')))
		dest = int(escape_html(self.request.get('pathDest')))
		w = Path.add_new_path(pathID,name,status,src,dest,cvss)
		if u.paths:
			u.paths.append(w)
		else:
			u.paths = [ w ]
		u.put()
		
		
#######################################################################################################
#######################################################################################################
#######################################################################################################
###############  						Handler	Mapper Section							###############
#######################################################################################################
#######################################################################################################
#######################################################################################################
	
app = webapp2.WSGIApplication([
    ('/', HubHandler),
	('/logout',LogOutHandler),
	('/pleaselogin',PleaseLoginHandler),
	('/connectWithFacebook',FacebookLoginHandler),
	('/logout_with_facebook',FacebookLogoutHandler),
	('/map',MapHandler),
	('/dashboard',DashboardHandler),
	('/create-map',CreateMapHandler),
	('/attacker',AttackerHandler),
	('/add-new-attacker',AddNewAttackerHandler),
	('/displayImage',DisplayImageHandler),
	('/fetch-profile',CVEProfileFetchHandler),
	('/fetch-score',CVSScoreHandler),
	#('/addfakedata', AddFakeData),
	#('/loader', LoadGraphHandler),
	('/edit-graph',EditGraphHandler),
	('/create-graph',CreateGraphHandler),
	('/get-graph',GetGraphHandler),
	('/delete-graph',DeleteGraphHandler),
	('/add-new-machine',AddNewMachineHandler),
	('/add-new-service',AddNewServiceHandler),
	('/add-new-path',AddNewPathHandler)

	
], debug=True,config=config)

#######################################################################################################
#######################################################################################################
#######################################################################################################
###############  						Data Structure Section						###################
#######################################################################################################
#######################################################################################################
#######################################################################################################	
class CVEProfile(ndb.Model):
	profile_name = ndb.StringProperty(default="N/A")
	cve_id = ndb.StringProperty(required=True)
	cwe_id = ndb.StringProperty(required=True)
	cwe_name = ndb.StringProperty(required=True)
	summary = ndb.TextProperty()
	cvss_score = ndb.FloatProperty()
	exploit_count = ndb.IntegerProperty()
	publish_date = ndb.StringProperty()
	update_date = ndb.StringProperty()	
	cve_url = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	access_params = ndb.StringProperty()
	confidentiality_impact = ndb.IntegerProperty()
	integrity_impact = ndb.IntegerProperty()
	availability_impact = ndb.IntegerProperty()
	access_complexity = ndb.IntegerProperty()
	gained_access = ndb.IntegerProperty()
	authentication = ndb.IntegerProperty()
	
	@classmethod
	def createProfile(cls, cve_id , cwe_id , cwe_name, summary, cvss_score, exploit_count, publish_date, update_date, cve_url, confidentiality_impact, integrity_impact, availability_impact, access_complexity, gained_access, authentication):
		access_params = create_params()
		return CVEProfile(	cve_id = cve_id,
							cwe_id = cwe_id,
							cwe_name = cwe_name,
							summary = summary,
							cvss_score = cvss_score,
							exploit_count = exploit_count,
							publish_date = publish_date,
							update_date = update_date,
							cve_url = cve_url,
							confidentiality_impact = confidentiality_impact,
							integrity_impact = integrity_impact,
							availability_impact = availability_impact,
							access_complexity = access_complexity,
							gained_access = gained_access,
							authentication = authentication,
							access_params = access_params					)

class Service(ndb.Model):
	serviceID=ndb.IntegerProperty(required=True)
	name=ndb.StringProperty()
	status=ndb.StringProperty()
	impact=ndb.IntegerProperty()
	machineID=ndb.IntegerProperty()
	
	@classmethod
	def add_new_service(cls,serviceID,name,status,impact,machineID):
		return Service(		serviceID 	= 	serviceID,
							name 		= 	name,
							status 		=	status,
							impact 		= 	impact,
							machineID	=	machineID)

class Machine(ndb.Model):
	machineID=ndb.IntegerProperty(required=True)
	name=ndb.StringProperty()
	status=ndb.StringProperty()
	impact=ndb.IntegerProperty()
	
	@classmethod
	def add_new_machine(cls,machineID,name,status,impact):
		return Machine(		machineID 	= 	machineID,
							name 		= 	name,
							status 		=	status,
							impact 		= 	impact)

class Path(ndb.Model):
	pathID=ndb.IntegerProperty(required=True)
	name=ndb.StringProperty()
	status=ndb.StringProperty()
	src=ndb.IntegerProperty()
	dest=ndb.IntegerProperty()
	cvss=ndb.StringProperty()
	
	@classmethod
	def add_new_path(cls,pathID,name,status,src,dest,cvss):
		return Path(		pathID 		= 	pathID,
							name 		= 	name,
							status 		=	status,
							src 		= 	src,
							dest		=	dest,
							cvss		=	cvss)	

class Graph(ndb.Model):
	name=ndb.StringProperty(required=True)
	graphID=ndb.IntegerProperty(required=True)
	machines=ndb.StructuredProperty(Machine, repeated=True)
	services=ndb.StructuredProperty(Service, repeated=True)
	paths=ndb.StructuredProperty(Path, repeated=True)							
														
class Attacker(ndb.Model):
	alias = ndb.StringProperty(required=True)
	desc = ndb.StringProperty()
	cve = ndb.StringProperty(required=True)
	flawtype = ndb.StringProperty(required=True)
	access_params = ndb.StringProperty(required=True)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)

class CharacterImage(ndb.Model):
	blob = ndb.BlobKeyProperty()
	owner = ndb.StringProperty()
	access_params = ndb.StringProperty()	

class Map(ndb.Model):
	name = ndb.StringProperty(required=True)
	desc = ndb.StringProperty(required=True)
	created = ndb.DateTimeProperty(auto_now_add=True)
	number_of_node = ndb.IntegerProperty(default=0)
	updated = ndb.DateTimeProperty(auto_now=True)
	access_params = ndb.StringProperty(required=True)


	
class FacebookUser(ndb.Model):
	displayname = ndb.StringProperty(required=True)
	user_id = ndb.StringProperty()
	profile_url = ndb.StringProperty(required=True)
	access_token = ndb.StringProperty(required=True)
	access_params = ndb.StringProperty()
	email = ndb.StringProperty()
	joined_date = ndb.DateTimeProperty(auto_now_add=True)
	last_visited = ndb.DateTimeProperty(auto_now=True)
	avatar = ndb.StringProperty()
	have_api = ndb.BooleanProperty(default=False)
	
	
class User(ndb.Model):
	email = ndb.StringProperty(required=True)
	displayname = ndb.StringProperty(required=True)
	username = ndb.StringProperty(required=True)
	access_params = ndb.StringProperty()
	pw_hash = ndb.StringProperty()
	last_visited = ndb.DateTimeProperty(auto_now=True)
	joined_date = ndb.DateTimeProperty(auto_now_add=True)
	
	@classmethod
	def by_id(cls, uid):
		return User.get_by_id(uid)
	
	@classmethod
	def by_displayname(cls, displayname):
		u = User.query(User.displayname == displayname).get()
		return u
		
	@classmethod
	def by_username(cls, username):
		u = User.query(User.username == username).get()
		return u
		
	@classmethod
	def by_email(cls, email):
		u = User.query(User.email == email).get()
		return u

	@classmethod
	def register(cls, email, displayname , username , password, access_params):
		pw_hash = make_pw_hash(username, password)
		return User(
                    displayname = displayname,
					username = username,
					email = email,
                    pw_hash = pw_hash,
					access_params = access_params
					)		
					
	@classmethod
	def login(cls, username, password):
		u = cls.by_username(username)
		if u and valid_pw(username, password, u.pw_hash):
			return u
	
