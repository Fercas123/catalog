from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from setup_catalog_db import Base, Category, Project, User

#imports for google login/token
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

#declaring the client id
Client_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "DIY Application"

# Connect to Database and create database session
engine = create_engine('sqlite:///projectscategories.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange (32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    #validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('invalid state'),401)
        response.headers['Content-Type'] = 'application/json'
        return response
    #obtain authorization code
    code = request.data
    try:
        #upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code'), 401)
        response.headers['Content-Type']= 'application/json'
        return response

    #check if there is an access token and its valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is valid for this app.
    if result['issued_to'] != Client_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    # check to see if the user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = json.loads(answer.text)

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    #see if the user exists, if not make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output
#DISCONNECT-  Revoke a current users token and reset their login_session.
@app.route("/gdisconnect")
def gdisconnect():
    #only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
      response = make_response(json.dumps('Current user not connected'), 401)
      response.headers['Content-Type'] = 'application/json'
      return response
    #execute http get request to revoke current token.
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % credentials
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
      #resete the users session.
      del login_session['credentials']
      del login_session['gplus_id']
      del login_session['username']
      del login_session['email']
      del login_session['picture']

      response = make_response(json.dumps('Successfully disconnected'),200)
      response.headers['Content-Type'] = 'application/json'
      return response
    else:
      #for whatever reason, the given token was invalid.
      response = make_response(json.dumps('failed to revoke token for given user'), 400)
      response.headers['Content-Type'] = 'application/json'
      return response

###
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        flash("you have been successfully logged out")
        return redirect(url_for('ShowCategories'))
    else:
        flash("you were not logged in to begin with!")
    return redirect(url_for('ShowCategories'))
#making an API Endpoint (GET request)
@app.route('/categories/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(Category=[i.serialize for i in categories])

@app.route('/category/<int:category_id>/JSON')
def projectsJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items= session.query(Project).filter_by(category_id=category_id).all()
    return jsonify(Category=[i.serialize for i in items])

@app.route('/category/<int:category_id>/<int:project_id>/JSON')
def projectJSON(category_id, project_id):
    project = session.query(Project).filter_by(id=project_id).one()
    return jsonify(Project=project.serialize)
###

@app.route('/')
@app.route('/categories')
def ShowCategories():
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return render_template('publiccategories.html', categories=categories)
    else:
        return render_template('categories.html', categories=categories)

@app.route('/category/new', methods=['GET','POST'])
def NewCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        NewCategory= Category(name = request.form['name'], user_id=login_session['user_id'])
        session.add(NewCategory)
        session.commit()
        flash("New Category Created")
        return redirect(url_for('ShowCategories'))
    else:
        return render_template('newcategory.html')

@app.route('/category/<int:category_id>/delete', methods=['GET','POST'])
def DeleteCategory(category_id):
    deletedCategory = session.query(Category).filter_by(id=category_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        session.delete(deletedCategory)
        session.commit()
        flash("the category has been successfully deleted")
        return redirect(url_for('ShowCategories'))
    else:
        return render_template('deletecategory.html', item=deletedCategory)

@app.route('/category/<int:category_id>/edit/', methods=['GET','POST'])
def EditCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    EditCategory = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        if request.form['name']:
            EditCategory.name = request.form['name']
        session.add(EditCategory)
        session.commit()
        flash("the Category has been successfully edited")
        return redirect(url_for('ShowCategories'))
    else:
        return render_template('editcategory.html', category_id=category_id, item=EditCategory)

@app.route('/category/<int:category_id>')
def ShowProjects(category_id):
    category = session.query(Category).filter_by(id = category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Project).filter_by(category_id = category.id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicproject.html', category=category, items=items, creator = creator)
    else:
        return render_template('project.html', category=category, items=items, creator=creator)

@app.route('/category/<int:category_id>/project/new', methods=['GET','POST'])
def NewProject(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem= Project(name = request.form['name'], complexity = request.form['complexity'], description = request.form['description'], user_id=login_session['user_id'], category_id= category_id)
        session.add(newItem)
        session.commit()
        flash("new project created")
        return redirect(url_for('ShowProjects', category_id=category_id))
    else:
        return render_template('createproject.html', category_id=category_id)

@app.route('/category/<int:category_id>/project/<int:project_id>/edit' , methods=['GET','POST'])
def EditProject(category_id, project_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedproject = session.query(Project).filter_by(id=project_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedproject.name = request.form['name']
        session.add(editedproject)
        session.commit()
        flash("Project Successfully Edited")
        return redirect(url_for('ShowProjects', category_id=category_id))
    else:
        return render_template('editproject.html', category_id=category_id, project_id=project_id, item=editedproject)


@app.route('/category/<int:category_id>/project/<int:project_id>/delete', methods=['GET','POST'])
def DeleteProject(category_id, project_id):
    if 'username' not in login_session:
        return redirect('/login')
    deletedItem = session.query(Project).filter_by(id=project_id).one()
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash("the project has been successfully deleted")
        return redirect(url_for('ShowProjects', category_id=category_id))
    else:
        return render_template('deleteproject.html', item=deletedItem)

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 8000)