#!/usr/bin/env python3
import sys
from glob import glob
from pathlib import Path

import searchconsole
import yagmail
from colorama import Fore, Style, init
from searchconsole import auth
from searchconsole.account import WebProperty

init(autoreset=True)

def authenticate_gsc():
    """Authenticates you to query the Search Console API.

    Returns:
        <class 'searchconsole.account.Account'>: An insantiated Account object from which to query the API.
    
    Errors:
        The function will raise a system error if no client_secret.json file has been provided, or if it is named incorrectly.
    """
    client_secrets_check = glob(f'{str(Path())}/*client*secret*')
    if not client_secrets_check:
        print(f'\n{Fore.RED + Style.BRIGHT}ERROR:{Style.RESET_ALL} Authentication to the GSC API failed for {Style.BRIGHT}two{Style.RESET_ALL} possible reasons:\n')
        print(f'{Fore.CYAN + Style.BRIGHT}1){Style.RESET_ALL} The client_secret file is not present in this directory. If so, {Style.BRIGHT}refer to README.md{Style.RESET_ALL} for instructions on how to get your GSC API credentials.')
        print(f'{Fore.CYAN + Style.BRIGHT}2){Style.RESET_ALL} The file is present, but is not called "client_secret[xyz].json". If so, please {Style.BRIGHT}rename the file{Style.RESET_ALL} to "client_secret.json".\n')
        sys.exit()
    else:
        client_secrets_file = client_secrets_check[0]
        credentials_check = glob(f'{str(Path())}/*creds*')
        if not credentials_check:
            credentials_file = 'creds.json'
            searchconsole.authenticate(client_config=client_secrets_file,
                                       serialize=credentials_file)
        else:
            credentials_file = credentials_check[0]
    return searchconsole.authenticate(client_config=client_secrets_file,
                                        credentials=credentials_file)
        
def authenticate_yagmail():
    """Authenticates you to send emails via the Gmail API.

    Returns:
        <class 'yagmail.sender.SMTP'>: An instantiated SMTP object that you can use to send emails.
    """
    yagmail_path = Path.home().joinpath('.yagmail')
    if not yagmail_path.exists():
        username = input('Enter Gmail username >>> ').strip()
        password = input('Enter Gmail password >>> ')
        print('Registering for yagmail...')
        yagmail.register(username=username,
                         password=password)
        with open(yagmail_path, 'w') as f:
            f.write(username) 
        print('Done.')
    return yagmail.SMTP()
