# -*- coding: utf-8 -*-
"""
Created on Tue Mar 26 11:59:58 2019

@author: jdevreeze
"""
from datetime import datetime
from distutils.version import StrictVersion

import bs4 as bs

import inspect
import json
import re
import requests

class Etherpad:
    """
    This class extracts Etherpad data (Etherpad Lite 1.6.6)
    """  
    
    _ignore = True
    _print_errors = True
    
    _base = None
    _apikey = None
    
    _version = '1.2.12'
    
    _log = []
    
    def __init__(self, url, apikey, version=None, ignore=True):
        """
        Initialize the Etherpad class.   
        
        Args:
            url: The base url for the API.
            apikey: The secret key to access the API.
            version: Change the version of Etherpad (Note some methods might not work).
            ignore: Set to False to raise exceptions, which is helpfull for debugging (default True).
        
        Returns:
            False in case of an error.
        Raises:
            ValueError: A valid url must be specified.
            ValueError: A valid API key must be specified.
        """
            
        if type(url) is not str:
            self.__error(self.__line_no(), 'A valid url must be specified.', None)
        else:
            self._base = url
        
        if type(apikey) is not str:
            self.__error(self.__line_no(), 'A valid API key must be specified.', None)
        else:
            self._apikey = apikey 
            
        if type(version) is str:
            self._version = version 

        if ignore is False:
            self._ignore = False      
    
    def unique_authors(self, pad):
        """
        Extract all unique authors from a saved etherpad pad.
        
        Args:
            pad: The pad name.

        Returns:
            A list with all authors.
        
        Raises:
            ValueError: Etherpad API version 1 or later is required.
            ValueError: An error message from the etherpad API.
        """
        
        if StrictVersion(self._version) < StrictVersion('1.0.0'):
            self.__error(self.__line_no(), 'Etherpad API version 1.2.7 or later is required, you have: ' + self._version + '.', None)
            return False
        
        params = {
            'padID' : pad
        }
        
        # Extract the data for this method
        data = self._request('listAuthorsOfPad', params)
        
        if data['code'] is not 0:
            self.__error(self.__line_no(), 'PadId "' + pad + '" does not exist.', None)
            return []
        
        return data['data']['authorIDs']
    
    def author_name(self, authorId):
        """
        Extract the raw text of a pad.
        
        Args:
            pad: The pad name.

        Returns:
            A string with the raw text.
        
        Raises:
            ValueError: Etherpad API version 1 or later is required.
            ValueError: An error message from the etherpad API.
        """
        
        if StrictVersion(self._version) < StrictVersion('1.1.0'):
            self.__error(self.__line_no(), 'Etherpad API version 1.2.7 or later is required, you have: ' + self._version + '.', None)
            return False
        
        params = {
            'authorID' : authorId
        }
        
        # Extract the data for this method
        data = self._request('getAuthorName', params)
        
        if data['code'] is not 0:
            self.__error(self.__line_no(), 'AuthorId "' + authorId + '" does not exist.', None)
            return False
        
        return data['data']

    def get_text(self, pad):
        """
        Extract the raw text of a pad.
        
        Args:
            pad: The pad name.

        Returns:
            A string with the raw text.
        
        Raises:
            ValueError: Etherpad API version 1 or later is required.
            ValueError: An error message from the etherpad API.
        """
        
        if StrictVersion(self._version) < StrictVersion('1.0.0'):
            self.__error(self.__line_no(), 'Etherpad API version 1.2.7 or later is required, you have: ' + self._version + '.', None)
            return False
        
        params = {
            'padID' : pad
        }
        
        # Extract the data for this method
        data = self._request('getText', params)
        
        if data['code'] is not 0:
            self.__error(self.__line_no(), 'PadId "' + pad + '" does not exist.', None)
            return False
        
        return data['data']['text']

    def get_html(self, pad, authors):
        """
        Extract the html of a path and change all author class names.
        
        Args:
            pad: The pad name.
            authors: The author names for which the contributions need to be extracted.

        Returns:
            A list with all text added by each author and a list of all text deleted by each author.
        """
        
        soup = str(self.__unique_contributions(pad))

        for i, author in enumerate(authors, 1):
            
            soup = soup.replace(
                'authora_{}'.format(author[2:]), 'author{}'.format(i)
            )

        return soup

    def get_edits(self, pad, author):
        """
        Extract all edits made by an author from a saved etherpad pad.
        
        Args:
            pad: The pad name.
            author: The author name for which the contributions need to be extracted.

        Returns:
            A list with all texts added by an author.
        """
        
        pieces = []

        soup = self.__unique_contributions(pad)
        edits = soup.find_all('span', class_='author{}'.format(author.replace('.','_'))) 
        
        for edit in edits:
            pieces.append(str(edit.string))

        return pieces

    def all_pads_with_authors(self):
        """
        Get all pads and their corresponding authors.

        Returns:
            A dict with all pads and their corresponding authors. 
        """
        
        meta_pads = []
        pads = self._request('listAllPads', {})['data']['padIDs']

        for pad in pads:

            # Only include allowed pads
            if len(pad) == 13:

                meta_authors = {}
                authors = self.unique_authors(pad)
                timestamp = self._request('getLastEdited', {'padID' : pad})['data']['lastEdited'] 

                # Only include pads that have 2 or more authors
                if len(authors) > 1:
                
                    for author in authors:
                        meta_authors[author] = self.author_name(author)

                    meta_pads.append({
                        'padId' : pad,
                        'timestamp' : timestamp,
                        'authors' : meta_authors
                    })

        return meta_pads

    def __unique_contributions(self, pad):
        """
        Extract all unique_contributions from a saved etherpad pad.
        
        Args:
            pad: The pad name.

        Returns:
            A BeautifulSoup object.
        
        Raises:
            ValueError: Etherpad API version 1.2.7 or later is required.
            ValueError: An error message from the etherpad API.
        """
        
        if StrictVersion(self._version) < StrictVersion('1.2.7'):
            self.__error(self.__line_no(), 'Etherpad API version 1.2.7 or later is required, you have: ' + self._version + '.', None)
            return False
        
        params = {
            'padID' : pad,
            'startRev' : 0 
        }
        
        # Extract the data for this method
        data = self._request('createDiffHTML', params)
        
        if data['code'] is not 0:
            self.__error(self.__line_no(), 'PadId "' + pad + '" does not exist.', None)
            return False
        
        content = data['data']['html']

        # Remove escape character from the document
        content = re.sub('\"', '"', content)
        content = re.sub('\n', '', content)
        content = re.sub('\t', '', content)
        content = re.sub('\r', '', content)
        
        soup = bs.BeautifulSoup(content, 'html.parser')

        # Remove all styles from the content    
        elements = soup.findAll('style')
        for element in elements:
            element.replace_with('')
        
        return soup

    def __position(self, haystack, needle):
        """
        Internal method to find the position of a needle in a haystack string.
        
        Args:
            haystack: The string to search in.
            needle: The string to search for in the haystack.
        
        Returns:
            An integer with the position.
        """
        
        if type(haystack) is not str:
            self.__error(self.__line_no(), 'A valid haystack must be specified.', None)
            return False
        
        if type(needle) is not str:
            self.__error(self.__line_no(), 'A valid needle must be specified.', None)
            return False
        
        position = haystack.find(needle)
        
        # Occurrence at the beginning of the haystack
        if position == 0:
            return 1
        
        # Occurrence at the end of the haystack
        if len(haystack) == position + len(needle):
            return -1

        return 0
            
    def _request(self, method, params):
        """
        Internal method which extracts information from the Etherpad API.    
        
        Args:
            method: A string with an API supported method name.
            params: A dict with the Etherpad API paramaters for the specified method.
        
        Returns:
            A json object.
        
        Raises:
            ValueError: An unexpected error occurred while connecting to Wikipedia.
        """
        
        #prefix = '' if self._base is '127.0.0.1' and self._base is not 'localhost' else 'pad.'
        
        url = 'http://{}{}/api/{}/{}'.format('', self._base, self._version, method)        
        params.update({'apikey' : self._apikey})
        
        resp = requests.get(url, params)
        
        if resp.status_code != requests.codes.ok:
            self.__error(self.__line_no(), 'An unexpected error occurred while connecting to Etherpad API (Status code: "' + resp.status_code + '").', None)
            return False
        
        return resp.json()
    
    def __line_no(self):
        """
        Internal method to get the current line number.
        
        Returns:
            An integer with the current line number.
        """        
        return inspect.currentframe().f_back.f_lineno
        
    def __error(self, line, error, etype):
        """
        Internal method to handle errors.    
        
        Args:
            line: An integer with the current line number
            error: A string with the error message.
            etype: A string with the error type
        """

        if self._print_errors is True:
            print('Line:', line, '-', error)
            
        self._log.append((datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S%Z'), line, error, etype))
        
        if self._ignore is False:
            raise ValueError(error)
