import config
import utils

def email(token, title, note):
    metadata = note.split("\n")

    print(metadata)
    return