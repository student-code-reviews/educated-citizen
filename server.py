from flask import Flask, render_template, request, flash, redirect

import xml.etree.ElementTree as ET
from pprint import pformat
import os
import requests

from model import Legislator, connect_to_db, db

app = Flask(__name__)
app.secret_key = 'SECRETSECRETSECRET'

API_KEY = os.environ['CIVIC_API_KEY']
VOTESMART_API_KEY = os.environ['VOTESMART_API_KEY']
OPEN_SECRETS_API_KEY = os.environ['OPEN_SECRETS_API_KEY']

@app.route('/')
def homepage():
    """ Homepage with user form"""

    return render_template('homepage.html')

@app.route('/officials')
def find_elected_officials():
    """Finding all elected officials using Vote Smart API"""

    # find zip code from user's form
    user_zipcode = request.args.get('zipcode', '')
    votesmart_zipcode_url = 'http://api.votesmart.org/Officials.getByZip'
    votesmart_zipcode_payload = {'key' : VOTESMART_API_KEY,
                                 'zip5' : user_zipcode}
    votesmart_zipcode_response = requests.get(votesmart_zipcode_url, 
                                              params=votesmart_zipcode_payload)
    # response in xml
    root = ET.fromstring(votesmart_zipcode_response.content)

    #build empty list of dictionaries with candidate data
    list_candidates = []
    list_candidate_id = []

    for candidate in root.iter('candidate'):
        candidate_id = candidate.find('candidateId').text
        list_candidate_id.append(candidate_id)
        dict_of_officials = {
            "cfirst_name": candidate.find('firstName').text,
            "clast_name": candidate.find('lastName').text,
            "ctitle": candidate.find('title').text,
            "coffice_parties": candidate.find('officeParties').text
        }
        list_candidates.append(dict_of_officials)

    bill_category = request.args.get('category', '')
    bill_category_url = 'http://api.votesmart.org/Votes.getBillsByCategoryYearState'
    bill_category_payload = {'key' : VOTESMART_API_KEY,
                             'categoryId' : bill_category, 'year': '2020'}
    bill_category_response = requests.get(bill_category_url, 
                                          params=bill_category_payload)
    # response in xml
    bill_root = ET.fromstring(bill_category_response.content)

    list_bills = []

    for bill in bill_root.iter('bill'):
        dict_of_bills = {
        "bill_number": bill.find('billNumber').text,
        "bill_title": bill.find('title').text,
        "bill_type": bill.find('type').text
        }
        list_bills.append(dict_of_bills)
        
    return render_template('smartvote.html', candidates=list_candidates,
                           bills=list_bills)


@app.route('/search')
def search_contributions_by_member():
    """ Search form; asks for candidate's last name """

    return render_template('candidate.html')


@app.route('/search-results')
def member_results():
    """ Provides contribution info on candidate selected from search form 
        Am using OpenSecrets API """

    # finding candidate's open secret id from db
    # using who user selected on candidate search form
    official_last_name = request.args.get('last-name').upper()
    state = request.args.get('state')

    # one legislator in db has a null opensecrets value, accounting for this below
    db_last_name = Legislator.query.filter(Legislator.last_name==official_last_name,
                                           Legislator.opensecrets_id!=None,
                                           Legislator.state==state).first()
    if not db_last_name:
        flash('The last name entered and state selected did not match an existing legislator. Please search again.')
        return redirect('/search')
    opensecrets = db_last_name.opensecrets_id
    full_name = db_last_name.full_name


    top_industries_url = 'https://www.opensecrets.org/api/?method=candIndustry'
    top_industries_payload = {'cid' : opensecrets, 'cycle' : 2020,
                              'apikey' : OPEN_SECRETS_API_KEY}
    top_industries_response = requests.get(top_industries_url,
                                           top_industries_payload)
    top_industry_root = ET.fromstring(top_industries_response.content)

    list_industry = []

    for industry in top_industry_root.iter('industry'):
        dict_industries = {
        "Industry Name" : industry.attrib['industry_name'],
        "Individual Contributors": industry.attrib['indivs'],
        "PACs" : industry.attrib['pacs'],
        "Total" : industry.attrib['total']
        }
        list_industry.append(dict_industries)

    return render_template('candidate_results.html',
                       candidate_contributions=list_industry,
                       full_name=full_name)

@app.route('/votes-by-topic')
def search_votes_by_member():
    """ Search form; user selects a candidate and category to get candidate's votes """
    
    return render_template('voting.html')

# @app.route('/using-ajax')
# def ajax_pls_work():

#     # db_last_name = Legislator.query.filter(Legislator.last_name==official_last_name,
#     #                                        Legislator.votesmart_id!=None,
#     #                                        Legislator.state==state).first()
#     phone = votes_by_official(db_last_name.phone)

#     return jsonify({'phone': phone})


@app.route('/official-votes')
def votes_by_official():
    """Allows user to see votes by candidate using VoteSmart API based on which
    topic user selected in form"""
 
    last_name = request.args.get('last-name')
    official_last_name = last_name.upper()
    state = request.args.get('state')
    # a couple legislators in db has a null value, accounting for that below
    db_last_name = Legislator.query.filter(Legislator.last_name==official_last_name,
                                           Legislator.votesmart_id!=None,
                                           Legislator.state==state).first()
    # error handling below:
    if not db_last_name:
        flash('The search did not return a valid result. Please try again.')
        return redirect('/votes-by-topic')
    votesmart = db_last_name.votesmart_id
    full_name = db_last_name.full_name

    # using this to test ajax
    last_name = db_last_name.last_name
    phone = db_last_name.phone
    website = db_last_name.website


    category = request.args.get('category')

    votes_official_url = 'http://api.votesmart.org/Votes.getByOfficial'
    votes_official_payload = {'key' : VOTESMART_API_KEY, 
                              'candidateId' : votesmart,
                              'categoryId': category}
    votes_official_response = requests.get(votes_official_url, 
                                           params=votes_official_payload)
    voting_record_root = ET.fromstring(votes_official_response.content)

    bill_list = []
    index = 1

    for bill in voting_record_root.iter('bill'):
        dict_of_votes = {
        "bill number": voting_record_root[index][1].text,
        "title" : voting_record_root[index][2].text,
        "passage": voting_record_root[index][8].text,
        "vote": voting_record_root[index][9].text,
        }
        index += 1
        bill_list.append(dict_of_votes)

    return render_template('voting_results.html', full_name=full_name,
                           bill_list=bill_list, last_name=last_name, phone=phone)

########### below is info for using Google's Civic Info API ##############   
# @app.route('/votes')
# def vote_by_official():
#     """ Finding votes official made on bills in category user selected. """

#     # vote_by_official_candidate_id = 
#     # how best to get candidate id?
#     # i can only grab one candidate at a time, maybe this should be an ajax
#     # if user clicks on a candidate in ('/officials'), then it goes to this
#     # route? i use that click as the candidate id?

#     vote_by_official_url = 'http://api.votesmart.org/Votes.getByOfficial'
#     vote_by_official_payload = {'key' : VOTESMART_API_KEY, 'candidateId': }

########## info below this is related to Google Civic Info API ########
# unsure if i will use this

# @app.route('/elections')
# def election_info():
#     """ election query info, unsure if i will use this """

# # below is for electionQuery
#     election_url = 'https://www.googleapis.com/civicinfo/v2/elections'
#     election_payload = {'key' : API_KEY}

#     election_response = requests.get(election_url, params=election_payload)

#     # response in json
#     election_data = election_response.json()
#     election_info_data = election_data['elections']

#     # converting dict into list, getting back election name & date
#     elections_list = list(election_info_data[0].values())
#     elections = elections_list[1:3]


#     return render_template('results.html', elections=elections)

# @app.route('/contests')
# def contest_info():
#     """User search for ballot with street address """

# # below is for voterInfoQuery
# # match address from homepage.html with address in payload
#     address = request.args.get('address', '')

# # use elections id from election query as a param in voter_payload
# # will the electionid be stored in a session key?

#     voter_url = 'https://www.googleapis.com/civicinfo/v2/voterinfo'
#     voter_payload = {'key' : API_KEY, 'address': address}
#     voter_response = requests.get(voter_url, params=voter_payload)
#     voter_info_json = voter_response.json()

#     # getting election data, converting to list
#     voter_election_data = voter_info_json['election']
#     voter_election_list = list(voter_election_data.values())
#     elections = voter_election_list[1:3] 

#     # unsure how to get values from contests without indexing
#     # contests[0] gives info about first office contest
#     first_contest_data = voter_info_json['contests'][0]
#     first_contest_list = [(key,value) for key, value in first_contest_data.items()]
#     spliced_data = first_contest_list[1:4:2]

#     candidate_info = first_contest_list[7][1:]


#     return render_template('ballot.html', elections=elections, 
#                            contests=spliced_data, candidates=candidate_info)


if __name__ == '__main__':
    app.debug = True
    connect_to_db(app)
    app.run(host='0.0.0.0')