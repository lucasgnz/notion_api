import requests
import furl
import time
from notion.block import TextBlock, PageBlock, QuoteBlock, CalloutBlock
from notion_api.config import *

def error(token, client, title, content):
    print("ERROR: {} / {}".format(title, content))
    id = create_new_page(token, client, title, error_db_id)
    page = client.get_block(id)
    page.children.add_new(TextBlock, title=content)


def get_db_properties(token, client, id):
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    response = requests.get('https://api.notion.com/v1/databases/' + id, headers=headers)
    try:
        return response.json()['properties']
    except Exception as e:
        error(token, client, "Error get_db_properties", id + ": " + str(e) + " / "+ str(response.json()))




def get_db_content(token, client, id, last_run_page_id=None, updated_main_db_pages=[]):
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '""+token+""'',
        'Notion-Version': '2021-05-13'
    }
    filters, sorts = [], []
    if last_run_page_id != None:
        last_run_timestamp = get_db_last_run_timestamp(token, last_run_page_id)
        filters.append('{' \
                            '"property": "last_edited_timestamp",' \
                             '"number": {' \
                                '"greater_than": '+str(last_run_timestamp-120000)+'' \
                            '}' \
                       '}')
        sorts = ['{' \
                 '"property": "Last edited",' \
                 '"direction": "ascending"' \
                 '}']
    filters += ['{' \
                            '"property": "Digital library ref",' \
                            '"text": {' \
                            '"equals": "' + updated_main_db_page + '"' \
                                       '}' \
                            '}' for updated_main_db_page in updated_main_db_pages]



    # filters / sorts
    data = '{' \
                '"filter":' \
                    '{' \
                    '"or":[' \
                      +','.join(filters)+'' \
                    '] }' \
                ',' \
                '"sorts": [' \
           + ','.join(sorts) + '' \
                ']' \
           '}'
    response = requests.post('https://api.notion.com/v1/databases/'+id+'/query', headers=headers, data=data.encode('utf-8'))
    try:
        return [r for r in response.json()['results'] if r['id'] != last_run_page_id]
    except Exception as e:
        error(token, client, "Error get_db_content", id+": "+str(e)+" / "+str(response.json()))

def update_db_last_run_timestamp(token, id):
    now = round(time.time()*1000)
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }

    data = '{' \
               '"properties": {' \
                   '"last_run_timestamp": {' \
                        '"number": '+str(now)+'' \
                    '}' \
                '}' \
            '}'
    requests.patch('https://api.notion.com/v1/pages/' + id, headers=headers, data=data.encode('utf-8'))

def get_page(token, id):
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    return requests.get('https://api.notion.com/v1/pages/' + id, headers=headers).json()

def get_db_last_run_timestamp(token, id):
    headers = {
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    response = requests.get('https://api.notion.com/v1/pages/' + id, headers=headers)
    update_db_last_run_timestamp(token, id)
    return response.json()['properties']['last_run_timestamp']['number']

def get_page_children(token, id):
    headers = {
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    response = requests.get('https://api.notion.com/v1/blocks/' + id + '/children', headers=headers)
    return response.json()['results']

def clean_url(url):
    url = furl.furl(url, strict=True)
    site_name = url.host.replace("www.", "").split(".")[0]

    if site_name == 'youtube':
        v = url.args['v']
        url.remove(args=True, fragment=True)
        url.add(args={'v': v})
    else:
        url.remove(args=True, fragment=True)

    url = url.url

    if url[-1] == "/":
        url = url[:-1]

    url = url.replace("'","%27")
    return url

'''def rec_del_multiple_dashs(s):
    if s.replace("--","-") == s:
        return s
    else:
        return rec_del_multiple_dashs(s.replace("--","-"))

def url_encode(string):
    r = ''.join([c if re.match("[a-zA-Z0-9]", c) else '-' for c in string])
    r = rec_del_multiple_dashs(r)
    return r'''

def get_id_by_url(token, url, db_id):
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    data = '{' \
           '    "filter": {' \
           '        "property": "Link",' \
           '        "url": {' \
           '            "contains":"'+url+'"' \
           '        }' \
           '    }' \
           '}'
    response = requests.post('https://api.notion.com/v1/databases/' + db_id + '/query', headers=headers, data=data.encode('utf-8'))

    if len(response.json()['results']) < 1:
        return -1
    else:
        return response.json()['results'][0]['id']

def create_new_page(token, client, title, db_id, metadata=[]):
    headers = {
        'Content-type': 'application/json; charset=utf-8',
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    data = '{ ' \
	'"parent": { "database_id": "'+db_id+'" }, ' \
	'"properties": { ' \
	'	"Name": { ' \
	'		"title": [ ' \
	'  			{ ' \
	'			"text": { ' \
	'				"content": "'+title+'" ' \
    '				} ' \
	'		    } ' \
	'	    ] ' \
	'   }' \
    ''+(',' if len(metadata)>0 else '')+'' \
                                                          +','.join(metadata)+'' \
    '}' \
    '}'

    response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=data.encode('utf-8'))
    try:
        return response.json()['id']
    except Exception as e:
        error(token, client, 'Create new page error', 'Title:{} \n \n Database ID: {} \n \n Error: {} \n \n Metadata: {}'.format(title, db_id, response.json(), metadata))


def add_main_db_link(token, id, main_db_id):
    headers = {
        'Authorization': 'Bearer '"" + token + ""'',
        'Content-type': 'application/json',
        'Notion-Version': '2021-05-13'
    }
    # '"text": "' + str(main_db_id) + '"' \
    data = '{"properties":{"Dofb": {"rich_text": [{"type": "text","text": {"content": "'+main_db_id+'"}}]}}}'
    URL = 'https://api.notion.com/v1/pages/' + id
    response = requests.patch(URL, data=data, headers=headers)

    #os.system('curl https://api.notion.com/v1/pages/'+id+' -H \'Authorization: Bearer \'"'+token+'"\'\' -H "Content-Type: application/json" -H "Notion-Version 2021-05-13" -X PATCH --data \'{"properties":{"Dofb": {"text": [{"type": "text","text": {"content": "'+main_db_id+'"}}]}}}\'')


def update_metadata(token, client, page_id, metadata):
    headers = {
        'Authorization': 'Bearer '"" + token + ""'',
        'Content-type': 'application/json',
        'Notion-Version': '2021-05-13'
    }

    data = '{"properties": {'+', '.join(metadata)+'}}'
    URL = 'https://api.notion.com/v1/pages/' + page_id
    response = requests.patch(URL, data=data, headers=headers)
    try:
        return response.json()['id']
    except :
        error(token, client, 'Update metadata', page_id+" / Data : "+ data + ' / ' + str(response.json()))

def get_areas_projects_tags(token, client):
    # Get areas
    areas_ = [(a['id'], a['properties']['Name']['title'][0]['text']['content']) for a in
              get_db_content(token, client, areas_db_id)]

    # Get projects
    projects_ = [(a['id'], a['properties']['Name']['title'][0]['text']['content'],
                  [sn['text']['content'] for sn in a['properties']['Short name']['rich_text']]) for a in
                 get_db_content(token, client, projects_db_id)]

    # Get tags
    tags_ = [(a['id'], a['properties']['Name']['title'][0]['text']['content']) for a in
             get_db_content(token, client, tags_db_id)]

    return areas_, projects_, tags_

def get_statuses_types(token, client, db_id):
    # Get db_properties
    db_properties = get_db_properties(token, client, db_id)

    statuses_, types_ = [], []

    # Get statuses
    if 'Status' in db_properties.keys():
        statuses_ = [s['name'] for s in db_properties['Status']['select']['options']]

    # Get types of content
    if 'Type' in db_properties.keys():
        types_ = [s['name'] for s in db_properties['Type']['select']['options']]

    return statuses_, types_
