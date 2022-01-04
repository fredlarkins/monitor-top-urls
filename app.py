#!/usr/bin/env python3
import argparse
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import searchconsole
from searchconsole import auth

from auth_utils import authenticate_gsc, authenticate_yagmail
from check_urls import return_results_as_dataframe
from query_search_console import query

parser = argparse.ArgumentParser()
parser.add_argument('--property',
                    help='The property in Search Console you wish to query.',
                    required=True)
parser.add_argument('--num-urls',
                    help='The number of URLs you want to pull from the Search Console API and check for errors.',
                    default=100,
                    type=int
                    )
parser.add_argument('--rate-limit',
                    help='A rate limit if you want to control how quickly the script makes requests.',
                    default=30,
                    type=int
                    )
parser.add_argument('--recipients',
                    help='The email address of recipient of the automated emails.',
                    nargs='+',
                    required=True,
                    type=str)

args = parser.parse_args()
RECIPIENTS = args.recipients
PROPERTY = args.property
NUM_URLS = args.num_urls
RATE_LIMIT = args.rate_limit
search_console_url = 'https://search.google.com/u/1/search-console?' + urlencode({'resource_id':PROPERTY})
date_today = datetime.today().strftime('%Y-%m-%d')

yag = authenticate_yagmail()
print('Authenticating to Gmail...')

# getting our data from GSC API
print('Fetching data from GSC API...')
gsc_data = query(PROPERTY, NUM_URLS)
print('Done.')

# checking our URLs for 4xx, 5xx errors
print('Checking URLs for errors & redirects...')
try:
    check_results = return_results_as_dataframe(urls=gsc_data.page.to_list(),
                                                rate_limit=RATE_LIMIT)
# adding in an  exception block to 
except Exception as e:
    yag.send(
        subject='⚠️ Script crashed - check logs',
        to = RECIPIENTS,
        contents = f'''
        The following error occurred:
        
        {str(e)}
        
        Check logs for more info.
        '''
    )
    sys.exit()
print('Done.')

# joining the check results back on to the original dataframe
gsc_data = gsc_data.join(check_results, on='page')

# sorting errors and redirects into DataFrames
errors = gsc_data[gsc_data.status_code != 200]
redirects = gsc_data[gsc_data.redirect_type > 300]

# writing the errors to CSVs
print('Saving results of check to CSV...')
if not Path('errors').exists():
    Path('errors').mkdir()
    errors.to_csv(path_or_buf='errors/latest-errors.csv',
                                                index=False)
    redirects.to_csv(path_or_buf='errors/latest-redirects.csv',
                                                index=False)

else:
    errors.to_csv(path_or_buf='errors/latest-errors.csv',
                                                index=False)
    redirects.to_csv(path_or_buf='errors/latest-redirects.csv',
                                                index=False)
print('Done.')

# conditional statements below decide which template of email will be sent

if errors.empty:
    with open('html-templates/no-new-errors.html') as f:
        html_template = f.read()
        contents = html_template.replace(r'{{PROPERTY}}', PROPERTY)\
                                .replace(r'{{SEARCH_CONSOLE_LINK}}', search_console_url)\
                                .replace(r'{{NUM_URLS}}', str(gsc_data.shape[0]))\
                                .replace(r'{{DATE_TODAY}}', date_today)
        attachments = None
        if redirects.empty:
            subject = f'🟢 No errors found for {PROPERTY}'
        else:
            subject = f'🟡 Redirects found for {PROPERTY}'
            try:
                percentage_of_clicks_affected_by_redirects =  redirects.clicks.sum() * 100 / gsc_data.clicks.sum()
                percentage_of_clicks_affected_by_redirects = round(percentage_of_clicks_affected_by_redirects, 2)
            except ZeroDivisionError:
                percentage_of_clicks_affected_by_redirects = 0
            contents = contents.replace(r'<!--{{START_REDIRECTS_BLOCK}}','')\
                                .replace(r'{{END_REDIRECTS_BLOCK}}-->', '')\
                                .replace(r'{{NUM_REDIRECTS_FOUND}}', str(redirects.shape[0]))\
                                .replace(r'{{CLICK_PERCENTAGE}}', str(percentage_of_clicks_affected_by_redirects))
            attachments = ['errors/latest-redirects.csv']

else:
    with open('html-templates/errors.html') as f:
        html_template = f.read()
        attachments = ['errors/latest-errors.csv']
        contents = html_template.replace(r'{{PROPERTY}}', PROPERTY)\
                                .replace(r'{{SEARCH_CONSOLE_LINK}}', search_console_url)\
                                .replace(r'{{NUM_URLS}}', str(gsc_data.shape[0]))\
                                .replace(r'{{DATE_TODAY}}', date_today)\
                                .replace(r'{{NUM_ERRORS}}', str(errors.shape[0]))
        try:
            percentage_of_clicks_affected_by_errors = errors.clicks.sum() * 100 / gsc_data.clicks.sum()
            percentage_of_clicks_affected_by_errors = round(percentage_of_clicks_affected_by_errors, 2)
        except ZeroDivisionError:
            percentage_of_clicks_affected_by_errors = 0
        contents = contents.replace(r'{{ERROR_CLICK_PERCENTAGE}}', str(percentage_of_clicks_affected_by_errors))
        if redirects.empty:
            subject = f'🔴 Errors outstanding for {PROPERTY}'
        else:
            subject = f'🔴🟡 Errors & redirects outstanding for {PROPERTY}'
            try:
                percentage_of_clicks_affected_by_redirects = redirects.clicks.sum() * 100 / gsc_data.clicks.sum()
                percentage_of_clicks_affected_by_redirects = round(percentage_of_clicks_affected_by_redirects, 2)
            except ZeroDivisionError:
                percentage_of_clicks_affected_by_redirects = 0
            contents = contents.replace(r'<!--{{START_REDIRECTS_BLOCK}}','')\
                                .replace(r'{{END_REDIRECTS_BLOCK}}-->', '')\
                                .replace(r'{{NUM_REDIRECTS_FOUND}}', str(redirects.shape[0]))\
                                .replace(r'{{CLICK_PERCENTAGE}}', str(percentage_of_clicks_affected_by_redirects))
            attachments.append('errors/latest-errors.csv')            
print(f'Sending email(s) to {",".join(RECIPIENTS)}...')

yag.send(
    subject=subject,
    to=RECIPIENTS,
    attachments=attachments,
    contents=contents,
)
print('Done.')