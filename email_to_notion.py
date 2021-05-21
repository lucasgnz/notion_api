#from .config import *
#from .utils import *

def transfer_email_to_notion(token, title, note):
    metadata = note.split("\n")

    print(metadata)
    return