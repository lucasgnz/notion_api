import config
import utils

def email_to_notion(token, title, note):
    metadata = note.split("\n")

    print(metadata)
    return