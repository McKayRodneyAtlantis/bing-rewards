#!/usr/bin/env python3

import os
import getpass
import base64
import time


CONFIG_FILE_PATH      = "BingRewards/src/config.py"

CONFIG_FILE_TEMPLATE = """credentials = dict(
    email = '{0}',
    password = '{1}',
)
"""


# get hashed credentials 
try:
    email = base64.b64encode(raw_input("   *Email: ").encode()).decode()
except:
    email = base64.b64encode(input("   *Email: ").encode()).decode()
print("   Hashed: {}\n".format(email))
password = base64.b64encode(getpass.getpass("*Password: ").encode()).decode()
print("   Hashed: {}\n".format(password))

new_config = CONFIG_FILE_TEMPLATE.format(email, password)

# check if config file exists
if not os.path.isfile(CONFIG_FILE_PATH):
    # create new config file
    with open(CONFIG_FILE_PATH, "w") as config_file:
        config_file.write(new_config)
        print("{} created successfully".format(CONFIG_FILE_PATH))
else:
    with open(CONFIG_FILE_PATH, "r") as config_file:
        cur_config = config_file.read()
    if new_config != cur_config:
        # update config file
        with open(CONFIG_FILE_PATH, "w") as config_file:
            config_file.writelines(new_config)
        print("{} updated successfully".format(CONFIG_FILE_PATH))
    else:
        print("{} already contains latest credentials".format(CONFIG_FILE_PATH))
time.sleep(2)

