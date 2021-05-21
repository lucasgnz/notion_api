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

def error(token, title, content):
    print("ERROR: {} / {}".format(title, content))
    #create_new_page(token, title, '', error_db_id)

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
                 '"direction": "descending"' \
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

################################################################################################################################
def get_urls(db, property_name):
    r = {}
    for e in db:
        url = clean_url(url)
        r[e['id']] =  url
    return r

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

def merge_db_on_links(args_main_db, args_highlights_db):
    main_links = get_urls(*args_main_db)
    main_ids = {v:k for (k,v) in reversed(main_links.items())}
    highlights_links = get_urls(*args_highlights_db)

    # print(main_links)
    # print(highlights_links)

    to_update = set(main_links.values()).intersection(set(highlights_links.values()))

    to_add = set(highlights_links.values()).difference(set(main_links.values()))

    print("To update: {}".format(to_update))
    print("To add: {}".format(to_add))

    for id_page_highlights, url in highlights_links.items():
        if url in to_update:
            id_page_main_db = main_ids[url]
            print("Add highlights of {} in {}".format(id_page_highlights, id_page_main_db))
            add_highlights(id_page_highlights, id_page_main_db)

        if url in to_add:
            print("Create new page with highlights of {}".format(id_page_highlights))
################################################################################################################################

def rec_del_multiple_dashs(s):
    if s.replace("--","-") == s:
        return s
    else:
        return rec_del_multiple_dashs(s.replace("--","-"))
def url_encode(string):
    r = ''.join([c if re.match("[a-zA-Z0-9]", c) else '-' for c in string])
    r = rec_del_multiple_dashs(r)
    return r

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

def create_new_page(token, title, url, db_id):
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
    '       "url": "'+url+'"' \
    '    }' \
    '}' \
    '}'

    response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=data.encode('utf-8'))
    try:
        return response.json()['id']
    except:
        error(token, title, response.json())


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



def cron(token, token_v2):
    client = NotionClient(token_v2)

    #### COMMAND ####
    highlights_db = get_db_content(token, highlights_db_id, highlights_last_run_page_id, [])

    updated_main_db_pages = []
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
            highlights = [e.title for e in client.get_block(h['id']).children if e.type == "quote"]


            main_page_id = get_id_by_url(token, url, library_db_id)

            if main_page_id == -1:
                main_page_id = create_new_page(token, title, url, library_db_id)

            #add_main_db_link(token, h['id'], main_page_id)
            main_page = client.get_block(main_page_id)
            updated_main_db_pages.append(main_page_id)

            print("Adding {} highlights to {}".format(len(highlights), title))

            for e in main_page.children:
                if e.type == "quote" or e.type == "callout":
                    e.remove(permanently=True)

            for highlight in highlights:
                main_page.children.add_new(QuoteBlock, title=highlight)
            ######

            #Delete highlight from highlight DB

            # OFFICIAL API (removing pages is still not supported)

            ######

            # UNOFFICIAL API
            h_ = client.get_block(h['id'])
            h_.remove()
        except:
           error(token, "Adding highlights from {} to main DB ({})".format(highlights_db_id, library_db_id), "Title: {}, URL: {}".format(title, url))

    #Add notes to main DB
    print("Adding notes to main DB...")
    notes_db = get_db_content(token, notes_db_id, notes_last_run_page_id, updated_main_db_pages)#### Add notes corresponding to updated main db pages
    for n in notes_db:
        title = n['properties']['Name']['title'][0]['text']['content']
        url = n['properties']['Link']['url']
        url = clean_url(url)

        #try:
        #OFFICIAL API (Blocks of type "quote" are still unsupported...)
        #blocks = get_page_children(token, n['id'])

        #UNOFFICIAL API
        blocks = client.get_block(n['id']).children
        highlight_text = blocks[0].title
        note = blocks[1].title

        main_page_id = get_id_by_url(token, url, library_db_id)

        if len(n['properties']['Digital library ref']['rich_text']) == 0:
            add_main_db_link(token, n['id'], main_page_id)
        main_page = client.get_block(main_page_id)

        for idx, h in enumerate(main_page.children):
            if hasattr(h, 'title') and h.title==highlight_text:
                if(idx<len(main_page.children)-1 and main_page.children[idx+1].type == "text"):
                    print("Remove ", main_page.children[idx + 1].title)
                    main_page.children[idx + 1].remove(permanently=True)
                h.remove(permanently=True)
                main_page.children.add_new(QuoteBlock, title=highlight_text)
                main_page.children.add_new(CalloutBlock, title=note)


        #add_block(n['id'])
        #except:
        #    error(token, "Adding notes from {} to main DB ({})".format(notes_db_id, library_db_id), "Title: {}, Highlight: {}, URL: {}".format(title, highlight, url))


    return