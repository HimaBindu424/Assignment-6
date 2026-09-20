#Name:  M.HimaBindu
#Emp Num:  1204977

import os
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAILBOX_OWNER_EMAIL = os.getenv("MAILBOX_OWNER_EMAIL")

if GEMINI_API_KEY:
    print("GEMINI_API_KEY is set.")