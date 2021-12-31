#!/usr/bin/env python3
import sys
from colorama import Fore, Style, init
from auth_utils import authenticate_gsc
init(autoreset=True)

def query(property:str, num_urls:int):
    """Wrapper function to query the Search Console API and return a dataframe.

    Args:
        property (str): The GSC property to query.
        num_urls (int): The number of URLs to return in the dataframe.

    Returns:
        <class 'pandas.core.frame.DataFrame'>: Dataframe containing the last month's worth of Search Console data.
    """
    # checking that the specified property exists in Search Console
    account = authenticate_gsc()
    all_properties = [prop.url for prop in account.webproperties]
    if property not in all_properties:
        sys.exit(
            (f'\n{Fore.RED + Style.BRIGHT}ERROR:{Style.RESET_ALL} "{property}" property does not exist in your Search Console account. Please check the --property argument specified when running the script.\n')
        )
    # fetching the dataframe
    webprop = account[property]
    df = webprop.query\
                        .range(start='today', months=-1)\
                        .dimension('page')\
                        .limit(num_urls)\
                        .get()\
                        .to_dataframe()
    return df