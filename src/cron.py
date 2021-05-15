import requests
import json

def get_db_content(token, id):
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '""+token+""'',
        'Notion-Version': '2021-05-13'
    }

    data = ''#filters

    response = requests.post('https://api.notion.com/v1/databases/'+id+'/query', headers=headers, data=data)

    return response

def cron(token):

    db = json.dump(get_db_content(token, '4b7625673a034a789bf055aabd180a0c'))
    #print(db)
    return db