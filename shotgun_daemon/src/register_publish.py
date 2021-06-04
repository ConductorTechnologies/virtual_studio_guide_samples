import json
import os
import pprint

import shotgun_api3

SERVER = os.environ['SHOTGUN_SERVER']
SCRIPT_NAME = os.environ['SHOTGUN_SCRIPT_NAME']
SCRIPT_KEY = os.environ['SHOTGUN_SCRIPT_KEY']
    
print "Registering publish of file to Shotgun"

sg = shotgun_api3.Shotgun(SERVER, SCRIPT_NAME, SCRIPT_KEY)

with open("/tmp/published_file.json") as fh:
    data = json.load(fh)
    
print "Using data:"
pprint.pprint(data, indent=4)

entity = sg.create("PublishedFile", data=data)

