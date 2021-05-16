import requests
import furl
import time
from datetime import date
from notion.client import NotionClient
from notion.block import TextBlock, PageBlock, QuoteBlock, CalloutBlock
import re
import os


###CONFIG###
library_db_id = '4b7625673a034a789bf055aabd180a0c'
notes_db_id = '51695ec05e114ca581982a29abb46574'
highlights_db_id = '5fa75c76-8fee-4663-a2d7-fc0d4aebc46e'
notes_last_run_page_id = 'a1556700-7882-4a98-a823-e663065b8f75'
highlights_last_run_page_id = None
error_db_id = '53a7033e508b414eaa090a1235347316'
############

def error(token, client, title, content):
    print("ERROR: {} / {}".format(title, content))
    id = create_new_page(token, client, title, '', error_db_id)
    page = client.get_block(id)
    page.children.add_new(TextBlock, title=content)

def get_db_content(token, id, last_run_page_id, updated_main_db_pages):
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
    return [r for r in response.json()['results'] if r['id'] != last_run_page_id]

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

def create_new_page(token, client, title, url, db_id):
    headers = {
        'Content-type': 'application/json; charset=utf-8',
        'Authorization': 'Bearer '"" + token + ""'',
        'Notion-Version': '2021-05-13'
    }
    data = \
    '{ ' \
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
	'   },' \
    '   "Link": { ' \
    '       "url": '+('null' if url=='' else '"'+url+'"')+'' \
    '    },' \
                                                          '"Status": {"select": {"name": "In progress"}}' \
    '}' \
    '}'

    response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=data.encode('utf-8'))
    try:
        print(response.json())
        return response.json()['id']
    except Exception as e:
        error(token, client, 'Create new page error', 'Title:{} \n \n Url: {} \n \n Database ID: {} \n \n Error: {}'.format(title, url, db_id, e))


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


def change_status(token, page_id, status):
    headers = {
        'Authorization': 'Bearer '"" + token + ""'',
        'Content-type': 'application/json',
        'Notion-Version': '2021-05-13'
    }

    data = '{"properties":{"Status": {"select": {"name": "'+status+'"}}}}'
    URL = 'https://api.notion.com/v1/pages/' + page_id
    response = requests.patch(URL, data=data, headers=headers)
    return response.json()['id']


def update_main_page(token, client, main_page_id, title, highlights):
    print("Adding {} highlights to {}".format(len(highlights), title))

    change_status(token, main_page_id, "In progress")

    main_page = client.get_block(main_page_id)
    for e in main_page.children:
        if e.type == "quote" or e.type == "callout":
            e.remove(permanently=True)

    notes_db = get_db_content(token, notes_db_id, notes_last_run_page_id,
                              [main_page_id])  #### Add notes corresponding to updated main db pages

    foot_notes = []
    for highlight in highlights:
        main_page.children.add_new(QuoteBlock, title=highlight)
        for n in notes_db:
            blocks = client.get_block(n['id']).children
            note = blocks[1].title
            if blocks[0].type != "quote":
                highlight_text = ''
                foot_notes.append(note)
            else:
                highlight_text = blocks[0].title
            if highlight_text == highlight:
                main_page.children.add_new(CalloutBlock, title=note)
    for note in foot_notes:
        main_page.children.add_new(CalloutBlock, title=note)

def cron(token, token_v2):
    client = NotionClient(token_v2)

    #### COMMAND ####
    highlights_db = get_db_content(token, highlights_db_id, highlights_last_run_page_id, [])

    updated_main_db_pages = []

    main_db_pages_to_update = []

    notes_db = get_db_content(token, notes_db_id, notes_last_run_page_id, [])
    for n in notes_db:
        title = n['properties']['Name']['title'][0]['text']['content']
        url = n['properties']['Link']['url']
        url = clean_url(url)

        main_page_id = get_id_by_url(token, url, library_db_id)

        if main_page_id == -1:
            main_page_id = create_new_page(token, client, title, url, library_db_id)

        main_db_pages_to_update.append(main_page_id)

        if len(n['properties']['Digital library ref']['rich_text']) == 0:
            add_main_db_link(token, n['id'], main_page_id)

    print(main_db_pages_to_update)

    # Add highlights to main DB
    print("Adding highlights to main DB...")
    for h in highlights_db:
        title = h['properties']['Title']['title'][0]['text']['content']
        print(title)
        url = h['properties']['Link']['url']
        url = clean_url(url)
        try:
            # OFFICIAL API (Blocks of type "quote" are still unsupported...)
            # blocks = get_page_children(token, n['id'])
            ######

            # UNOFFICIAL API
            main_page_id = get_id_by_url(token, url, library_db_id)
            if main_page_id == -1:
                main_page_id = create_new_page(token, client, title, url, library_db_id)

            #add_main_db_link(token, h['id'], main_page_id)
            update_main_page(token, client, main_page_id, title, [e.title for e in client.get_block(h['id']).children if e.type == "quote"])
            updated_main_db_pages.append(main_page_id)
            ######

            #Delete highlight from highlight DB

            # OFFICIAL API (removing pages is still not supported)

            ######
            # UNOFFICIAL API
            print("Delete {}".format(h['id']))
            h_ = client.get_block(h['id'])
            h_.remove()
        except Exception as e:
            print(e)
            error(token, client, "Adding new highlights", "From database (ID: {}) to main database (ID: {})".format(highlights_db_id, library_db_id)+ "\n \n Title: {} \n \n URL: {} \n \n Error: {}".format(title, url, e))

    main_db_pages_to_update = list(set(main_db_pages_to_update) - set(updated_main_db_pages))
    for page in main_db_pages_to_update:
        try:
            update_main_page(token, client, page, "["+page+"]",
                         [e.title for e in client.get_block(page).children if e.type == "quote"])
        except Exception as e:
            error(token, client, "Adding new notes",
                  "From database (ID: {}) to main database (ID: {})".format(highlights_db_id, library_db_id)
                  + "\n \n Page ID: {} \n \n Error: {}".format(page, e))
    return