#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime
from sys import maxsize

import aiohttp
import pandas as pd
from aiolimiter import AsyncLimiter
from tqdm.asyncio import tqdm

async def fetch(url:str, session:aiohttp.client.ClientSession):
    """Coroutine function to get the request headers (but not content) of the given URL.

    Args:
        url (str): The URL to fetch.
        session (aiohttp.client.ClientSession): A ClientSession object to make the request.

    Returns:
        tuple: A tuple containing information about the request, namely:
                - requested URL
                - status code
                - error message (if applicable, else None)
                - redirect type (if applicable, else 0)
                - redirect URL (if applicable, else None)
                - resolved URL
    """
    try:
        async with session.get(url) as resp:
            status_code = int(resp.status)
            resolved_url = resp.url
            error_message = None
            if resp.history:
                redirect_type = int(resp.history[-1].status)
                redirect_url = resp.history[-1].url
            else:
                redirect_type = 0
                redirect_url = None
    except Exception as e:
        if type(e).__name__ in dir(aiohttp.client_exceptions):
            error_message = type(e).__name__
            status_code = 0
            redirect_type = 0
            redirect_url = resolved_url = None
        else:
            # logging the error
            today = datetime.today().strftime('%Y-%m-%d')
            logging.basicConfig(filename=f'logs/critical-error-log{today}.log',
                    filemode='w',
                    level=logging.ERROR,
                    format='%(asctime)s -- %(message)s',
                    datefmt='%d-%b-%Y %H:%M:%S'
                    )
            logging.error(msg=e,
                          exc_info=True)
    return (url, status_code, error_message, redirect_type, redirect_url, resolved_url)

async def get_tasks(urls:list, session:aiohttp.client.ClientSession, rate_limit:int):
    """Async function that utilises fetch() to check a list of URLs asynchronously.

    Args:
        urls (list): The list of URLs to check.
        session (aiohttp.client.ClientSession): A ClientSession object.
        rate_limit (int): A rate limit to limit how quickly the function checks URLs.

    Returns:
        list: A list of tuples containing the data on the URLs provided.
    """
    limiter = AsyncLimiter(max_rate=rate_limit,
                           time_period=1)
    tasks = []
    for url in urls:
        async with limiter:
            task = asyncio.create_task(fetch(url, session))
            tasks.append(task)
    results = await tqdm.gather(*tasks)
    return results

async def fetch_all(urls:list, rate_limit:int):
    """A main()-like function to pass into asyncio.run().

    Args:
        urls (list): The list of URLs to check.
        rate_limit (int): A rate limit to limit how quickly the function checks URLs.
        
    Returns:
        list: A list of tuples containing the data on the URLs provided.
    """
    async with aiohttp.ClientSession() as session:
        data = await get_tasks(urls, session, rate_limit)
        return data

def return_results_as_dataframe(urls:list, rate_limit:int):
    """Helper function to asynchronously check a list of URLs and return a DataFrame containing the results.

    Args:
        urls (list): The list of URLs to check.
        rate_limit (int): A rate limit to limit how quickly the function checks URLs.

    Returns:
        pandas.DataFrame: A DataFrame with the URLs as its index and the following columns:
                - requested URL (index)
                - status code
                - error message (if applicable, else None)
                - redirect type (if applicable, else 0)
                - redirect URL (if applicable, else None)
                - resolved URL
    """
    data = asyncio.run(fetch_all(urls, rate_limit))
    df = pd.DataFrame(data=data,
                      columns=[
                          'url',
                          'status_code',
                          'error_message',
                          'redirect_type',
                          'redirect_url',
                          'resolved_url'
                          ]
                      )
    df = df.set_index('url')
    return df