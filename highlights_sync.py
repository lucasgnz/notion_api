from notion.client import NotionClient

from .utils import *

from .config import *

def update_main_page(token, client, main_page_id, title, highlights, metadata):
    print("Adding {} highlights to {}".format(len(highlights), title))

    update_metadata(token, client, main_page_id, metadata)

    main_page = client.get_block(main_page_id)
    for e in main_page.children:
        if e.type == "quote" or e.type == "callout":
            e.remove(permanently=True)

    notes_db = get_db_content(token, client, notes_db_id, notes_last_run_page_id,
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


def get_metadata(token, client, url, metadata_, statuses_, types_, areas_, projects_, tags_, areas=[], projects=[], tags=[], status = None, type = None):
    metadata_lower = [m.lower() for m in metadata_]
    new_tags = metadata_.copy()
    for a in areas_:
        if a[1].lower() in metadata_lower:
            if a[0] not in areas:
                areas.append(a[0])
            new_tags[metadata_lower.index(a[1].lower())] = ''
    for a in projects_:
        if a[1].lower() in metadata_lower:
            if a[0] not in projects:
                projects.append(a[0])
            new_tags[metadata_lower.index(a[1].lower())] = ''
        for sn in a[2]:
            if sn.lower() in metadata_lower:
                if a[0] not in projects:
                    projects.append(a[0])
                new_tags[metadata_lower.index(sn.lower())] = ''
    for a in tags_:
        if a[1].lower() in metadata_lower:
            if a[0] not in tags:
                tags.append(a[0])
            new_tags[metadata_lower.index(a[1].lower())] = ''



    for s in statuses_:
        if s.lower() in metadata_lower:
            status = s
            new_tags[metadata_lower.index(s.lower())] = ''

    for t in types_:
        if t.lower() in metadata_lower:
            type = t
            new_tags[metadata_lower.index(t.lower())] = ''

    new_tags_areas = ['"Areas": {' \
                      '"relation": [' \
                      + ','.join(['{ "id": "' + id + '" }' for id in areas]) + '' \
                                                                               ']' \
                                                                               '}']

    for tag in [t for t in new_tags if t != '']:
        id_tag = create_new_page(token, client, tag, tags_db_id, new_tags_areas)# # # # new_tags_areas
        tags.append(id_tag)

    #####
    metadata = [
        '"Areas_": {' \
        '"relation": [' \
        + ','.join(['{ "id": "' + id + '" }' for id in areas]) + '' \
                                                                 ']' \
                                                                 '}',
        '"Projects": {' \
        '"relation": [' \
        + ','.join(['{ "id": "' + id + '" }' for id in projects]) + '' \
                                                                    ']' \
                                                                    '}',
        '"Tags": {' \
        '"relation": [' \
        + ','.join(['{ "id": "' + id + '" }' for id in tags]) + '' \
                                                                ']' \
                                                                '}'
    ]
    if status != None:
        metadata += [
            '"Status": {' \
            '"select": {' \
            '"name": "' + status + '"' \
                                   '}' \
                                   '}']
    if type != None:
        metadata += [
            '"Type": {' \
            '"select": {' \
            '"name": "' + type + '"' \
                                 '}' \
                                 '}']

    metadata += ['"Link": { ' \
                 '       "url": ' + ('null' if url == '' else '"' + url + '"') + '' \
                                                                                 '    }']

    return metadata

def sync(token, token_v2):
    client = NotionClient(token_v2)

    #### COMMAND ####
    highlights_db = get_db_content(token, client, highlights_db_id, highlights_last_run_page_id, [])

    updated_main_db_pages = []

    main_db_pages_to_update = []

    notes_db = get_db_content(token, client, notes_db_id, notes_last_run_page_id, [])
    for n in notes_db:
        title = n['properties']['Name']['title'][0]['text']['content']
        url = n['properties']['Link']['url']
        url = clean_url(url)

        main_page_id = get_id_by_url(token, url, library_db_id)

        if main_page_id == -1:
            main_page_id = create_new_page(token, client, title, library_db_id, [

                '"Link": { ' \
    '       "url": '+('null' if url=='' else '"'+url+'"')+'' \
    '    }',

                '"Status": {"select": {"name": "'+new_entry_status+'"}}'])

        main_db_pages_to_update.append(main_page_id)

        if len(n['properties']['Digital library ref']['rich_text']) == 0:
            add_main_db_link(token, n['id'], main_page_id)


    areas_, projects_, tags_ = get_areas_projects_tags(token, client)
    statuses_, types_ = get_statuses_types(token, client, library_db_id)

    # Get Reading List types

    # Add highlights to main DB
    print("Adding highlights to main DB...")
    for h in highlights_db:
        title = h['properties']['Title']['title'][0]['text']['content']
        print(title)
        url = h['properties']['Link']['url']
        url = clean_url(url)
        metadata_ = [e['name'] for e in h['properties']['Tags']['multi_select']]

        try:
            # OFFICIAL API (Blocks of type "quote" are still unsupported...)
            # blocks = get_page_children(token, n['id'])
            ######

            # UNOFFICIAL API
            main_page_id = get_id_by_url(token, url, library_db_id)
            if main_page_id == -1:
                #metadata = get_metadata(token, client, url, metadata_, statuses_, types_, areas_, projects_, tags_)
                main_page_id = create_new_page(token, client, title, library_db_id, [])

            main_page = get_page(token, main_page_id)

            areas = [r['id'] for r in main_page['properties']['Areas_']['relation']]
            projects = [r['id'] for r in main_page['properties']['Projects']['relation']]
            tags = [r['id'] for r in main_page['properties']['Tags']['relation']]

            metadata = get_metadata(token, client, url, metadata_, statuses_, types_, areas_, projects_, tags_, areas, projects, tags, status="In progress")


            #add_main_db_link(token, h['id'], main_page_id)
            update_main_page(token, client, main_page_id, title, [e.title for e in client.get_block(h['id']).children if e.type == "quote"], metadata)
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