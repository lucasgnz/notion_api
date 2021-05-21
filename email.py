import notion_api.config
import notion_api.utils

def email(token, title, note):
    metadata = note.split("\n")

    print(metadata)
    return